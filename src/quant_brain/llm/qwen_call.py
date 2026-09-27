"""Bounded local-Qwen validation ladder: 14B, one repair, 27B, fail."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from quant_brain.db.init_db import DEFAULT_DB_PATH
from quant_brain.llm import ollama_client
from quant_brain.llm.validators import ValidationResult, validate_research_output
from quant_brain.research.schema import RawResearchPayload

DEFAULT_MODEL = "qwen3:14b"
ESCALATION_MODEL = "qwen3.8:27b"

# Context budget, calibrated on this machine (RTX 5070 12 GB, Ollama 0.34.3,
# 2026-09-26). At 16k qwen3:14b runs 84% on GPU at ~18 tok/s; at 40k it drops
# to ~2 tok/s, and qwen3.8:27b is ~6 tok/s at 16k. One constant for both
# models, so Ollama never reloads a model between calls to change its context.
EXTRACTION_NUM_CTX = 16384
# One source's JSON payload is a few hundred tokens; this leaves headroom, and a
# response that still hits it is refused as cut (done_reason=length).
EXTRACTION_NUM_PREDICT = 1536
# "Fits comfortably": prompt plus the output reserve within 80% of the window.
PROMPT_TOKEN_BUDGET = int(EXTRACTION_NUM_CTX * 0.8) - EXTRACTION_NUM_PREDICT
# 27B at 16k with a full output reserve measured close to 300s.
EXTRACTION_TIMEOUT = 600
# Fast pre-flight screen only. Measured prose and HTML snapshots ran 3.0-3.9
# bytes per token (PDF mojibake 1.8), so dividing by 4 refuses a prompt only
# when it is too large even under a generous ratio. The exact guards are the
# server's refusal and the response's own prompt_eval_count.
ESTIMATE_BYTES_PER_TOKEN = 4.0


def estimate_prompt_tokens(prompt: str) -> int:
    """Optimistic token estimate: an over-budget estimate means over budget."""
    return -(-len(prompt.encode("utf-8")) // int(ESTIMATE_BYTES_PER_TOKEN))


def prompt_budget_violation(prompt: str) -> str | None:
    """Why this prompt cannot be sent within the extraction budget, if it cannot."""
    estimated = estimate_prompt_tokens(prompt)
    if estimated > PROMPT_TOKEN_BUDGET:
        return (
            f"context: prompt needs at least ~{estimated} tokens, above the "
            f"{PROMPT_TOKEN_BUDGET}-token budget for num_ctx {EXTRACTION_NUM_CTX}"
        )
    return None


@dataclass(frozen=True)
class QwenAttempt:
    model: str
    duration_seconds: float
    prompt_hash: str
    response_hash: str
    validator_ok: bool
    validator_reasons: tuple[str, ...]


@dataclass(frozen=True)
class QwenResult:
    output: dict[str, Any]
    model_used: str
    repaired: bool
    escalated: bool
    validator_reasons: tuple[str, ...]
    durations: tuple[float, ...]
    attempts: tuple[QwenAttempt, ...]


class QwenValidationError(RuntimeError):
    """All three bounded attempts failed deterministic validation."""

    def __init__(self, attempts: list[QwenAttempt]) -> None:
        self.attempts = tuple(attempts)
        reasons = attempts[-1].validator_reasons if attempts else ("no response",)
        super().__init__("local Qwen failed closed: " + "; ".join(reasons))


class ContextBudgetError(QwenValidationError):
    """A prompt did not fit the context budget, so the ladder stopped at once.

    A repair or escalation prompt is always longer than the one that did not
    fit, so continuing could only waste calls or read a cut prompt. Subclassing
    keeps every existing fail-closed path that catches QwenValidationError.
    """

    def __init__(self, attempts: list[QwenAttempt], reason: str | None = None) -> None:
        super().__init__(attempts)
        if reason is not None and not attempts:
            self.args = ("local Qwen failed closed: " + reason,)


class RunBudgetError(QwenValidationError):
    """The Scout's whole-run wall-clock deadline was exhausted."""


def _record_attempt(
    attempt: QwenAttempt,
    *,
    db_path: str | Path | None,
    run_id: str | None,
    task_id: str | None,
    context: dict[str, Any] | None = None,
) -> None:
    if not run_id:
        return
    from quant_brain.ops.events import record_event

    record_event(
        db_path or DEFAULT_DB_PATH,
        run_id=run_id,
        task_id=task_id,
        agent_role="research_scout",
        stage="qwen_validation",
        status="completed" if attempt.validator_ok else "failed",
        event_type="qwen_attempt",
        message=f"{attempt.model} validation {'passed' if attempt.validator_ok else 'failed'}",
        payload={
            "model": attempt.model,
            "duration_seconds": attempt.duration_seconds,
            "prompt_hash": attempt.prompt_hash,
            "response_hash": attempt.response_hash,
            "validator_ok": attempt.validator_ok,
            "validator_reasons": list(attempt.validator_reasons),
            **(context or {}),
        },
    )


def _attempt(
    prompt: str,
    model: str,
    evidence: list[dict[str, Any]],
    expected_research_id: str,
    client: Any,
    attempts: list[QwenAttempt],
    *,
    db_path: str | Path | None,
    run_id: str | None,
    task_id: str | None,
    deadline: float | None,
) -> tuple[dict[str, Any] | None, ValidationResult]:
    started = time.perf_counter()
    response = None
    run_failure = None
    context_failure = prompt_budget_violation(prompt)
    if deadline is not None and time.monotonic() >= deadline:
        parsed = None
        run_failure = "budget: Scout run exceeded its whole-run wall-clock deadline"
        verdict = ValidationResult(False, (run_failure,))
    elif context_failure is not None:
        # Refused before the model is called: nothing was sent, nothing was cut.
        parsed = None
        verdict = ValidationResult(False, (context_failure,))
    else:
        try:
            timeout = EXTRACTION_TIMEOUT
            if deadline is not None:
                timeout = min(EXTRACTION_TIMEOUT, max(0.001, deadline - time.monotonic()))
            response = client.generate(
                prompt,
                model,
                num_ctx=EXTRACTION_NUM_CTX,
                num_predict=EXTRACTION_NUM_PREDICT,
                prompt_token_budget=PROMPT_TOKEN_BUDGET,
                timeout=timeout,
                temperature=0.0,
                format=RawResearchPayload.model_json_schema(),
            )
            if deadline is not None and time.monotonic() >= deadline:
                parsed = None
                run_failure = "budget: Scout run exceeded its whole-run wall-clock deadline"
                verdict = ValidationResult(False, (run_failure,))
            else:
                parsed = json.loads(response.text)
                verdict = validate_research_output(
                    parsed, evidence, expected_research_id=expected_research_id
                )
        except ollama_client.ContextOverflowError as exc:
            parsed = None
            context_failure = str(exc)
            verdict = ValidationResult(False, (context_failure,))
        except Exception as exc:
            parsed = None
            if deadline is not None and time.monotonic() >= deadline:
                run_failure = "budget: Scout run exceeded its whole-run wall-clock deadline"
                reason = run_failure
            elif isinstance(exc, (json.JSONDecodeError, TypeError, ValueError)) and response is not None:
                reason = f"schema: malformed JSON: {exc}"
            else:
                reason = f"client_error: {type(exc).__name__}: {exc}"
            verdict = ValidationResult(False, (reason,))
    text = getattr(response, "text", None)
    item = QwenAttempt(
        model=model,
        duration_seconds=float(
            getattr(response, "duration_seconds", time.perf_counter() - started)
        ),
        prompt_hash=str(
            getattr(response, "prompt_hash", hashlib.sha256(prompt.encode("utf-8")).hexdigest())
        ),
        response_hash=str(
            getattr(
                response,
                "response_hash",
                hashlib.sha256(text.encode("utf-8")).hexdigest() if isinstance(text, str) else "",
            )
        ),
        validator_ok=verdict.ok,
        validator_reasons=verdict.reasons,
    )
    attempts.append(item)
    _record_attempt(
        item,
        db_path=db_path,
        run_id=run_id,
        task_id=task_id,
        context={
            "source_ids": [str(entry.get("source_id")) for entry in evidence],
            "num_ctx": EXTRACTION_NUM_CTX,
            "estimated_prompt_tokens": estimate_prompt_tokens(prompt),
            "prompt_eval_count": getattr(response, "prompt_eval_count", None),
        },
    )
    if run_failure is not None:
        raise RunBudgetError(attempts)
    if context_failure is not None:
        raise ContextBudgetError(attempts)
    return parsed, verdict


def _repair_prompt(base_prompt: str, prior: dict[str, Any] | None, reasons: tuple[str, ...]) -> str:
    return (
        f"{base_prompt}\n\nYour previous response failed deterministic validation.\n"
        f"Previous response:\n{json.dumps(prior, indent=2)}\n\n"
        f"Validator failures:\n{json.dumps(list(reasons), indent=2)}\n"
        "Return corrected JSON only. Fix the listed fields without inventing evidence."
    )


def qwen_call(
    prompt: str,
    evidence: list[dict[str, Any]],
    *,
    expected_research_id: str,
    client: Any = ollama_client,
    db_path: str | Path | None = None,
    run_id: str | None = None,
    task_id: str | None = None,
    deadline: float | None = None,
) -> QwenResult:
    """Run at most three local attempts, bounded by an optional whole-run deadline."""
    attempts: list[QwenAttempt] = []
    prior, verdict = _attempt(
        prompt, DEFAULT_MODEL, evidence, expected_research_id, client, attempts,
        db_path=db_path, run_id=run_id, task_id=task_id, deadline=deadline,
    )
    if verdict.ok and prior is not None:
        return _result(prior, attempts, repaired=False, escalated=False)

    repair = _repair_prompt(prompt, prior, verdict.reasons)
    prior, verdict = _attempt(
        repair, DEFAULT_MODEL, evidence, expected_research_id, client, attempts,
        db_path=db_path, run_id=run_id, task_id=task_id, deadline=deadline,
    )
    if verdict.ok and prior is not None:
        return _result(prior, attempts, repaired=True, escalated=False)

    escalation = _repair_prompt(prompt, prior, verdict.reasons)
    prior, verdict = _attempt(
        escalation, ESCALATION_MODEL, evidence, expected_research_id, client, attempts,
        db_path=db_path, run_id=run_id, task_id=task_id, deadline=deadline,
    )
    if verdict.ok and prior is not None:
        return _result(prior, attempts, repaired=True, escalated=True)
    raise QwenValidationError(attempts)


def _result(
    output: dict[str, Any], attempts: list[QwenAttempt], *, repaired: bool, escalated: bool
) -> QwenResult:
    return QwenResult(
        output=output,
        model_used=attempts[-1].model,
        repaired=repaired,
        escalated=escalated,
        validator_reasons=attempts[-1].validator_reasons,
        durations=tuple(item.duration_seconds for item in attempts),
        attempts=tuple(attempts),
    )

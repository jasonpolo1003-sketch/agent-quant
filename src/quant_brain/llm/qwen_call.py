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


def _record_attempt(
    attempt: QwenAttempt,
    *,
    db_path: str | Path | None,
    run_id: str | None,
    task_id: str | None,
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
) -> tuple[dict[str, Any] | None, ValidationResult]:
    started = time.perf_counter()
    response = None
    try:
        response = client.generate(
            prompt,
            model,
            temperature=0.0,
            format=RawResearchPayload.model_json_schema(),
        )
        parsed = json.loads(response.text)
        verdict = validate_research_output(
            parsed, evidence, expected_research_id=expected_research_id
        )
    except Exception as exc:
        parsed = None
        if isinstance(exc, (json.JSONDecodeError, TypeError, ValueError)) and response is not None:
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
    _record_attempt(item, db_path=db_path, run_id=run_id, task_id=task_id)
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
) -> QwenResult:
    """Run exactly three maximum local attempts; there is no retry loop/cloud fallback."""
    attempts: list[QwenAttempt] = []
    prior, verdict = _attempt(
        prompt, DEFAULT_MODEL, evidence, expected_research_id, client, attempts,
        db_path=db_path, run_id=run_id, task_id=task_id,
    )
    if verdict.ok and prior is not None:
        return _result(prior, attempts, repaired=False, escalated=False)

    repair = _repair_prompt(prompt, prior, verdict.reasons)
    prior, verdict = _attempt(
        repair, DEFAULT_MODEL, evidence, expected_research_id, client, attempts,
        db_path=db_path, run_id=run_id, task_id=task_id,
    )
    if verdict.ok and prior is not None:
        return _result(prior, attempts, repaired=True, escalated=False)

    escalation = _repair_prompt(prompt, prior, verdict.reasons)
    prior, verdict = _attempt(
        escalation, ESCALATION_MODEL, evidence, expected_research_id, client, attempts,
        db_path=db_path, run_id=run_id, task_id=task_id,
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

from __future__ import annotations

import argparse
import hashlib
import json
import shlex
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from quant_brain.config import PROJECT_ROOT
from quant_brain.db.init_db import DEFAULT_DB_PATH, connect, init_database
from quant_brain.research.intake import update_research_status
from quant_brain.research.schema import validate_raw_research_payload

# Phase 6 requires a raw note to cite at least this many upstream sources.
# Single definition on purpose: scripts/gate_readiness.py imports it, so the
# read-only probe and the pipeline cannot drift apart. They were two separate
# literals, and only the probe actually checked anything.
MIN_UPSTREAM_SOURCES = 3
# Phase 6's whole-run budget. The same monotonic deadline is passed to every
# per-source ladder so five sources cannot each consume a fresh timeout budget.
SCOUT_WALL_CLOCK_SECONDS = 15 * 60


class InsufficientUpstreamSources(ValueError):
    """Discovery found fewer distinct upstream works than Phase 6 requires.

    Carries the per-candidate detail so the Failed_Runs receipt can record what
    *was* found. A question that genuinely has thin literature behind it is a
    real research finding; it must be preserved as evidence rather than
    discarded, and it must never become a raw note or a curator recommendation.
    """

    def __init__(self, message: str, *, detail: dict[str, Any]) -> None:
        super().__init__(message)
        self.detail = detail


def candidate_evidence(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The per-candidate provenance block shared by every failure receipt.

    One definition so the sparse-source path and the generic failure path cannot
    describe the same candidates differently. Reads the keys discovery sets when
    it snapshots a page; a backend that writes no snapshots (the seeded stub)
    simply yields ``None`` for the snapshot fields.
    """
    return [
        {
            "url": source.get("url_or_citation"),
            "title": source.get("title"),
            "tier": source.get("source_quality"),
            "snapshot_path": source.get("snapshot_path"),
            "snapshot_sha256": source.get("snapshot_sha256"),
        }
        for source in sources
    ]


def _discovery_lane_markdown(lane: dict[str, Any]) -> str:
    """Human-readable record of the pre-registered list that drove this run."""
    lines = [
        "## Discovery Lane",
        "",
        f"- Lane: `{lane.get('lane')}` (pre-registered candidate list; no search query)",
        f"- List: `{lane.get('candidate_list_path')}`",
        f"- List sha256: `{lane.get('candidate_list_sha256')}`",
        f"- Candidates listed: {lane.get('candidate_count')}",
        "",
        "Listing a URL is discovery provenance only. Tiers come from the classifier, "
        "and support comes only from the snapshots and validators above.",
    ]
    return "\n".join(lines) + "\n"


def distinct_upstream_keys(sources: list[dict[str, Any]]) -> list[str]:
    """Identity of each cited work, for counting against the minimum.

    Counted over normalized URLs rather than list length: arXiv serves the same
    paper as ``.../abs/1234.5678v1`` and ``.../abs/1234.5678``, and
    ``normalize_candidate_url`` treats those as different strings, so
    ``len(sources)`` would let one work satisfy the bar twice. arXiv identities
    are canonicalized here rather than trusting the lane that supplied them --
    a source can reach this point from any lane, or from a hand-written note.
    The same holds for a DOI and its publisher landing page, which
    ``upstream_work_key`` maps to one work for the hosts it recognizes.
    Sources without a URL fall back to their citation text so an offline
    reference still counts once, and only once.
    """
    from quant_brain.discovery.work_identity import upstream_work_key

    keys: list[str] = []
    for source in sources:
        raw = str(source.get("url_or_citation") or "").strip()
        if not raw:
            continue
        if "://" in raw:
            key = upstream_work_key(raw)
        else:
            key = raw.casefold()
        if key and key not in keys:
            keys.append(key)
    return keys


# Minimal starter catalog: enough to execute the first loop without building a web crawler yet.
# This is intentionally small. A real quant workflow values provenance and review over volume.
STARTER_SOURCES: list[dict[str, Any]] = [
    {
        "title": "Relative Strength Index (RSI) — Investopedia overview",
        "source_type": "web",
        "url_or_citation": "https://www.investopedia.com/terms/r/rsi.asp",
        "method_families": ["mean_reversion"],
        "main_claim": "RSI is a momentum oscillator commonly used to identify overbought or oversold conditions.",
        "evidence": "Use as a plain-English source for RSI definition; verify exact formula and claims before final citation.",
        "possible_strategy_rule": "For an exploratory ETF mean-reversion test: define oversold using RSI below a threshold, then enter on the next bar rather than the same close.",
        "risks": [
            "RSI oversold can stay oversold during strong downtrends.",
            "Indicator definitions are not a trading edge by themselves.",
        ],
        "confidence": "medium",
        "source_quality": "practitioner",
        "asset_classes": ["equity", "etf"],
        "data_required": ["daily adjusted close for SPY, QQQ, IWM"],
        "data_access": "available-now",
        "mvp_testable": True,
    },
    {
        "title": "QuantConnect glossary — Look-Ahead Bias",
        "source_type": "docs",
        "url_or_citation": "https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/glossary#Look-Ahead-Bias",
        "method_families": ["mean_reversion", "trend_following", "all"],
        "main_claim": "Backtests must avoid using information that would not have been available at the time of the simulated trade.",
        "evidence": "Use as bias-control source; exact quote should be captured during curation.",
        "possible_strategy_rule": "Close-based signals should normally enter no earlier than the next bar in the MVP backtester.",
        "risks": [
            "If this is ignored, a strategy can appear profitable only because it cheats with future data."
        ],
        "confidence": "high",
        "source_quality": "primary",
        "asset_classes": ["equity", "etf", "futures"],
        "data_required": ["timestamped bars available at decision time"],
        "data_access": "available-now",
        "mvp_testable": True,
    },
    {
        "title": "QuantConnect glossary — Survivorship Bias",
        "source_type": "docs",
        "url_or_citation": "https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/glossary#Survivorship-Bias",
        "method_families": ["mean_reversion", "trend_following", "all"],
        "main_claim": "Universe selection can be biased if the backtest only includes assets that survived until today.",
        "evidence": "Use as validation-control source; exact quote should be captured during curation.",
        "possible_strategy_rule": "The first MVP should use fixed broad ETFs and explicitly label that this avoids stock-selection survivorship questions but does not prove broad market edge.",
        "risks": ["Stock-picking strategies need survivorship-bias-aware datasets later."],
        "confidence": "high",
        "source_quality": "primary",
        "asset_classes": ["equity", "etf"],
        "data_required": ["survivorship-aware or fixed-universe daily prices"],
        "data_access": "available-now",
        "mvp_testable": True,
    },
    {
        "title": "backtesting.py documentation",
        "source_type": "docs",
        "url_or_citation": "https://kernc.github.io/backtesting.py/",
        "method_families": ["mean_reversion", "trend_following", "all"],
        "main_claim": "backtesting.py is a small Python framework for testing trading strategies with features such as commissions, statistics, and plotting.",
        "evidence": "Use as tooling source for the first readable event-style MVP backtests.",
        "possible_strategy_rule": "Implement first strategy classes in backtesting.py after research and strategy-card stages are complete.",
        "risks": [
            "Framework convenience does not prevent bad signal timing, bad data, or overfitting."
        ],
        "confidence": "medium",
        "source_quality": "primary",
        "asset_classes": ["equity", "etf"],
        "data_required": ["daily OHLCV plus commission assumptions"],
        "data_access": "available-now",
        "mvp_testable": True,
    },
    {
        "title": "vectorbt documentation",
        "source_type": "docs",
        "url_or_citation": "https://vectorbt.dev/",
        "method_families": ["mean_reversion", "trend_following", "all"],
        "main_claim": "vectorbt is useful for fast vectorized research and parameter sweeps over pandas/NumPy data.",
        "evidence": "Use as tooling source for fast exploration, not as proof of edge.",
        "possible_strategy_rule": "Use vectorbt later to compare parameter regions, then validate promising settings in a more explicit backtest.",
        "risks": [
            "Large parameter sweeps can create data-mining bias.",
            "Vectorized tests can hide execution timing mistakes if signals are not shifted correctly.",
        ],
        "confidence": "medium",
        "source_quality": "primary",
        "asset_classes": ["equity", "etf"],
        "data_required": ["pandas/NumPy price series for parameter sweeps"],
        "data_access": "available-now",
        "mvp_testable": True,
    },
    {
        "title": "Ernest P. Chan — Algorithmic Trading book",
        "source_type": "book",
        "url_or_citation": "Chan, Ernest P. Algorithmic Trading: Winning Strategies and Their Rationale. Wiley, 2013.",
        "method_families": ["mean_reversion", "trend_following", "all"],
        "main_claim": "A practitioner book commonly used for learning systematic strategy research, including mean-reversion and momentum concepts.",
        "evidence": "Book citation only; use user-owned copy or legal preview/notes for exact quotes.",
        "possible_strategy_rule": "Use as background reading, but do not promote any specific rule unless exact evidence is captured from an accessible copy.",
        "risks": [
            "Do not treat book reputation as evidence for a specific ETF strategy without a sourced passage and backtest."
        ],
        "confidence": "medium",
        "source_quality": "practitioner",
        "asset_classes": ["equity", "etf", "futures"],
        "data_required": ["user-owned copy or legal preview for exact quotes"],
        "data_access": "available-later",
        "mvp_testable": False,
    },
]


def select_candidate_sources(
    method_family: str | None, question: str, limit: int = 8
) -> list[dict[str, Any]]:
    """Select a small set of relevant starter sources for a research task."""
    family = method_family or "unclassified"
    question_lower = question.lower()
    selected = []
    for source in STARTER_SOURCES:
        families = source.get("method_families", [])
        title_claim = f"{source['title']} {source['main_claim']}".lower()
        if (
            family in families
            or "all" in families
            or any(term in title_claim for term in question_lower.split())
        ):
            selected.append({k: v for k, v in source.items() if k != "method_families"})
    return selected[:limit]


def format_findings_markdown(
    task: dict[str, Any],
    sources: list[dict[str, Any]],
    rejected: list[dict[str, Any]] | None = None,
    discovery_lane: dict[str, Any] | None = None,
    extraction_windows: list[dict[str, Any]] | None = None,
    validated_payload: dict[str, Any] | None = None,
) -> str:
    """Format selected sources into a raw research note section plus JSON block.

    ``validated_payload`` is the whole payload that passed validation; when
    given, the JSON block is exactly that payload (re-checked against the
    schema), never the template questions and recommendation below, which
    only the offline seeded catalog uses.

    ``rejected`` is rendered as prose *outside* the validated JSON block. The
    raw-research payload forbids extra fields, and honest rejection reporting is
    not worth widening that contract for; the machine-readable copy is the
    ``discovery_candidates_rejected`` event.
    """
    lines = [
        "## Scout Findings",
        "",
        "This first Research Scout executor is intentionally conservative: it gathers a small, reviewable source set instead of flooding the brain with hundreds of links.",
        "",
    ]
    for idx, source in enumerate(sources, start=1):
        lines.extend(
            [
                f"### Source {idx}: {source['title']}",
                "",
                f"- Source URL / citation: {source['url_or_citation']}",
                f"- Source type: {source['source_type']}",
                f"- Main claim: {source['main_claim']}",
                f"- Evidence: {source['evidence']}",
                f"- Possible strategy rule: {source['possible_strategy_rule']}",
                "- Risks / caveats:",
            ]
        )
        for risk in source.get("risks", []):
            lines.append(f"  - {risk}")
        lines.extend(
            [
                f"- Confidence: {source['confidence']}",
                f"- MVP testable with daily SPY/QQQ/IWM data: {str(source['mvp_testable']).lower()}",
                "",
            ]
        )

    if rejected:
        lines.extend(
            [
                "## Rejected Candidates",
                "",
                "Considered during bounded acquisition and deliberately not used as "
                "evidence. Honest rejection is a valid outcome.",
                "",
                "| URL | Tier | Reason |",
                "| --- | --- | --- |",
            ]
        )
        for record in rejected:
            url = str(record.get("url", "")).replace("|", "\\|")
            tier = str(record.get("tier", "")).replace("|", "\\|")
            reason = str(record.get("reason", "")).replace("|", "\\|")
            lines.append(f"| {url} | {tier} | {reason} |")
        lines.append("")

    if discovery_lane:
        # Prose outside the JSON block, for the same reason as the rejection
        # ledger: the payload contract forbids extra fields.
        lines.extend([_discovery_lane_markdown(discovery_lane), ""])

    if extraction_windows:
        # Also prose outside the JSON block; the machine-readable copy is the
        # ``extraction_window`` event trail.
        from quant_brain.research.windowing import window_manifest_markdown

        lines.extend([window_manifest_markdown(extraction_windows), ""])

    payload = (
        validate_raw_research_payload(validated_payload)
        if validated_payload is not None
        else build_raw_research_payload(task, sources)
    )
    lines.extend(
        ["## Required JSON Block", "", "```json", json.dumps(payload, indent=2), "```", ""]
    )
    return "\n".join(lines)


def build_raw_research_payload(
    task: dict[str, Any], sources: list[dict[str, Any]]
) -> dict[str, Any]:
    """Assemble and validate the JSON contract the curator later parses."""
    payload = {
        "research_id": task["research_id"],
        "status": "raw_saved",
        "sources": sources,
        "open_questions": [
            "Which exact RSI thresholds and holding period should be tested first?",
            "Which claims have exact quotes versus only high-level citation notes?",
            "Should the curator promote one source note per source or one combined source digest first?",
        ],
        "curator_recommendation": "promote_source",
    }
    return validate_raw_research_payload(payload)


def _get_research_task(db_path: str | Path, research_id: str) -> dict[str, Any]:
    init_database(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM research_questions WHERE research_id = ?", (research_id,)
        ).fetchone()
    if row is None:
        raise KeyError(f"research_id not found: {research_id}")
    return dict(row)


def _resolve_note_path(project_root: Path, raw_note_path: str | None) -> Path | None:
    if not raw_note_path:
        return None
    note_path = Path(raw_note_path)
    if note_path.exists():
        return note_path
    relative = project_root / str(raw_note_path)
    return relative if relative.exists() else None


def _discard_incomplete_raw_note(
    note_path: Path | None, original_bytes: bytes | None = None
) -> None:
    """Undo this run's effect on the raw note.

    Compensating rather than best-effort. Cleanup used to key on the note still
    *looking* like a scaffold, which silently spared a note that had already been
    rewritten to ``status: raw_saved`` — the orphan case. The run's own record of
    what it changed is authoritative instead:

    - a pre-existing note is restored byte-for-byte;
    - a note this run created is removed.
    """
    if note_path is None or not note_path.exists():
        return
    if original_bytes is not None:
        note_path.write_bytes(original_bytes)
        return
    note_path.unlink()


def _recover_raw_note(
    note_path: Path | None,
    *,
    created_scaffold: bool,
    original_note_bytes: bytes | None,
    resolve_write: Any | None,
) -> str:
    """Undo only what this run provably owns or changed; return the outcome.

    A note that existed before the run and was never modified by it is left
    alone: it may be a prepared scaffold holding pasted human work, and nothing
    authorizes this run to delete it. Every mutation goes through
    ``resolve_write`` first, so a path restriction refuses recovery (raising
    PathViolation) rather than being bypassed by it.
    """
    if note_path is None:
        return "no-note-tracked"
    if not note_path.exists():
        return "not-present"
    if not created_scaffold and original_note_bytes is None:
        return "untouched-preexisting"
    target = resolve_write(note_path) if resolve_write is not None else note_path
    _discard_incomplete_raw_note(target, None if created_scaffold else original_note_bytes)
    return "removed" if created_scaffold else "restored"


def _attempt(
    failures: list[dict[str, str]], step: str, fn: Any, *args: Any, **kwargs: Any
) -> tuple[bool, Any]:
    """Run one fail-closed step; absorb and record an ordinary failure.

    The boolean is the only success signal -- a step that succeeds by returning
    ``None`` must not read as a failure. ``Exception`` only: KeyboardInterrupt
    and SystemExit are process control and must propagate.
    """
    try:
        return True, fn(*args, **kwargs)
    except Exception as exc:
        failures.append({"step": step, "error_type": type(exc).__name__, "error": str(exc)})
        return False, None


def _write_failed_run_note(
    project_root: Path,
    *,
    run_id: str,
    research_id: str,
    stage: str,
    error: BaseException,
    resolve_write: Any | None,
    extra: dict[str, Any] | None = None,
    question: str = "queued",
    leftover_note: str | None = None,
) -> str:
    relative = f"brain/00_Inbox/Failed_Runs/{run_id}.md"
    dest = resolve_write(relative) if resolve_write else project_root / relative
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = extra or {}
    retryable = question == "queued" and leftover_note is None
    def release(clear: bool) -> str:
        return (
            "uv run python -c \"from quant_brain.research.intake import reset_research_for_retry; "
            f"reset_research_for_retry('db/brain.sqlite', '{research_id}', "
            f"clear_raw_note_path={clear})\""
        )

    if retryable:
        command = f"uv run python scripts/dispatch_task.py --type discovery --research-id {research_id}"
        lane = payload.get("discovery_lane")
        if isinstance(lane, dict) and isinstance(lane.get("candidate_list_path"), str):
            command += f" --candidate-list {shlex.quote(lane['candidate_list_path'])}"
        retry = f"""The research question was returned to `queued`. Re-run:

```bash
{command}
```"""
    elif question == "needs_review":
        retry = f"""**Manual inspection required.** Raw-note recovery failed, so the note this run
created or changed is still on disk at:

    {leftover_note}

The question is held at `needs_review`, which queue selection and Scout
dispatch refuse, and its `raw_note_path` still points at that file. Check
whether the note is a bare scaffold, a completed-looking (`raw_saved`) note, or
holds human-pasted work; remove it or restore it by hand. Then release with
exactly one of these.

If you removed the note:

```bash
{release(True)}
```

If you kept the note (the question keeps pointing at it):

```bash
{release(False)}
```"""
    else:
        leftover = f" The raw note at `{leftover_note}` was also not recovered." if leftover_note else ""
        retry = f"""**Recovery incomplete.** The research question could NOT be returned to
`queued` or held for review; see `recovery` in Detail.{leftover} Check the
question's status and its raw note by hand before retrying."""
    text = f"""---
id: {run_id}
type: failed_run
research_id: {research_id}
stage: {stage}
agent_role: research_scout
retryable: {"true" if retryable else "false"}
---

# Failed Scout Run — {run_id}

## Research ID

{research_id}

## Stage Reached

{stage}

## Error

`{type(error).__name__}`: {error}

## Detail

```json
{json.dumps(payload, indent=2, default=str)}
```

## Retry

{retry}
"""
    dest.write_text(text, encoding="utf-8")
    try:
        return dest.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return dest.as_posix()


def _record_scout_event(
    db_path: str | Path,
    *,
    run_id: str | None,
    task_id: str | None,
    event_type: str,
    status: str,
    message: str,
    payload: dict[str, Any] | None = None,
) -> None:
    if not run_id:
        return
    from quant_brain.ops.events import record_event

    record_event(
        db_path,
        run_id=run_id,
        task_id=task_id,
        agent_role="research_scout",
        stage="discovery",
        status=status,
        event_type=event_type,
        message=message,
        payload=payload or {},
    )


DIAGNOSTICS_DIR = "brain/00_Inbox/Failed_Runs/diagnostics"


def _failed_responses(
    attempts: Any, *, source_id: str, window_id: str | None
) -> list[dict[str, Any]]:
    """The failed attempts of one ladder, with their raw text, for diagnostics."""
    return [
        {
            "source_id": source_id,
            "window_id": window_id,
            "model": attempt.model,
            "prompt_hash": attempt.prompt_hash,
            "response_hash": attempt.response_hash,
            "validator_reasons": list(attempt.validator_reasons),
            "response_text": getattr(attempt, "response_text", None),
        }
        for attempt in attempts
        if not attempt.validator_ok
    ]


def _write_failed_responses(
    project_root: Path,
    *,
    run_id: str,
    research_id: str,
    responses: list[dict[str, Any]],
    resolve_write: Any | None,
) -> str:
    """Keep what the model actually said in a failed run, apart from research.

    JSON, not Markdown, so the brain indexer (``*.md``) never picks it up, and
    under ``Failed_Runs`` so nothing reads it as a raw note or a source. The run
    events keep only hashes; each ``response_hash`` here joins to them.
    """
    relative = f"{DIAGNOSTICS_DIR}/{run_id}.responses.json"
    dest = resolve_write(relative) if resolve_write else project_root / relative
    dest.parent.mkdir(parents=True, exist_ok=True)
    document = {
        "kind": "untrusted_model_responses",
        "trust": (
            "Diagnostic only: raw model output from failed validation attempts. "
            "It is not evidence, was rejected by the validators, and must never be "
            "promoted, indexed or cited."
        ),
        "run_id": run_id,
        "research_id": research_id,
        "responses": responses,
    }
    dest.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return relative


def _fail_closed_discovery(
    *,
    project_root: Path,
    db_path: str | Path,
    research_id: str | None,
    run_id: str | None,
    task_id: str | None,
    note_path: Path | None,
    created_scaffold: bool,
    stage: str,
    error: BaseException,
    resolve_write: Any | None,
    original_note_bytes: bytes | None = None,
    run_provenance: dict[str, Any] | None = None,
    failed_responses: list[dict[str, Any]] | None = None,
) -> str | None:
    """Recover retryable state, then write a Failed_Runs receipt saying what happened.

    Never raises ``Exception``: every step is attempted independently and a
    failure in one -- a receipt path violation, a locked database, a disk error
    -- is recorded as secondary and never skips the others or replaces
    ``error``, which the caller re-raises. Recovery is *attempted*, not
    guaranteed; what could not be done is reported on the receipt (if it can be
    written) and always as a note on ``error`` itself, a channel that depends
    on neither the database nor the filesystem.
    """
    from uuid import uuid4

    from quant_brain.research import intake
    from quant_brain.research.intake import reset_research_for_retry

    failures: list[dict[str, str]] = []
    _attempt(
        failures,
        "discovery_failed_event",
        _record_scout_event,
        db_path,
        run_id=run_id,
        task_id=task_id,
        event_type="discovery_failed",
        status="failed",
        message=str(error),
        payload={"stage": stage, "error": type(error).__name__},
    )

    # Recovery runs before the receipt so the receipt can state the outcome
    # rather than assume it.
    scaffold_ok, scaffold = _attempt(
        failures,
        "raw_note_recovery",
        _recover_raw_note,
        note_path,
        created_scaffold=created_scaffold,
        original_note_bytes=original_note_bytes,
        resolve_write=resolve_write,
    )
    if not scaffold_ok:
        scaffold = "failed"
        _attempt(
            failures,
            "cleanup_failed_event",
            _record_scout_event,
            db_path,
            run_id=run_id,
            task_id=task_id,
            event_type="discovery_cleanup_failed",
            status="failed",
            message=f"Could not recover raw note {note_path}",
            payload={"stage": stage},
        )

    question = "untracked"
    if research_id and scaffold == "failed":
        # A note this run created or changed is still on disk. ``queued`` would
        # make the question auto-selectable, and the next prepare would
        # overwrite that file at its deterministic path -- so hold it instead.
        # ``needs_review`` is selected by nothing and refused by explicit
        # dispatch; update_research_status keeps the pointer at the leftover.
        held, _ = _attempt(
            failures,
            "hold_for_review",
            intake.update_research_status,
            db_path,
            research_id,
            "needs_review",
        )
        question = "needs_review" if held else "update-failed"
    elif research_id:
        # The pointer is cleared only when no note remains at it. A pre-existing
        # note (untouched or restored) keeps its pointer, so a retry reuses it
        # instead of overwriting it.
        reset, _ = _attempt(
            failures,
            "reset_for_retry",
            reset_research_for_retry,
            db_path,
            research_id,
            clear_raw_note_path=scaffold in {"removed", "not-present", "no-note-tracked"},
        )
        question = "queued" if reset else "update-failed"

    failed_run_id = run_id or f"FAIL-{uuid4().hex[:10]}"
    diagnostics_path = None
    if failed_responses:
        # Before the receipt, so a failure here is listed among its secondary
        # failures, and so the receipt can point at the file.
        _, diagnostics_path = _attempt(
            failures,
            "diagnostic_responses",
            _write_failed_responses,
            project_root,
            run_id=failed_run_id,
            research_id=research_id or "unknown",
            responses=failed_responses,
            resolve_write=resolve_write,
        )
    recovery = {
        "raw_note": scaffold,
        "question": question,
        "complete": scaffold != "failed" and question == "queued",
        "secondary_failures": list(failures),
    }
    receipt_ok, failed_path = _attempt(
        failures,
        "receipt",
        _write_failed_run_note,
        project_root,
        run_id=failed_run_id,
        research_id=research_id or "unknown",
        stage=stage,
        error=error,
        resolve_write=resolve_write,
        question=question,
        leftover_note=str(note_path) if scaffold == "failed" else None,
        # Candidate evidence is attached to the *run*, not to one exception
        # class. It used to arrive only via ``error.detail``, which only
        # InsufficientUpstreamSources defines -- so a QwenValidationError
        # (or any post-fetch failure) wrote a receipt naming no source and
        # no snapshot, leaving files on disk that the receipt never
        # referenced. ``run_provenance`` sits *beneath* ``error.detail`` so
        # an exception that does carry its own richer detail still wins.
        extra={
            "task_id": task_id,
            **({"diagnostic_responses_path": diagnostics_path} if diagnostics_path else {}),
            "created_scaffold": created_scaffold,
            **(run_provenance or {}),
            **getattr(error, "detail", {}),
            "recovery": recovery,
        },
    )
    if receipt_ok:
        _attempt(
            failures,
            "failed_run_written_event",
            _record_scout_event,
            db_path,
            run_id=failed_run_id if run_id else None,
            task_id=task_id,
            event_type="failed_run_written",
            status="failed",
            message=f"Wrote Failed_Runs receipt {failed_path}",
            payload={"path": failed_path, "stage": stage},
        )

    for failure in failures:
        error.add_note(
            f"fail-closed {failure['step']} failed "
            f"({failure['error_type']}: {failure['error']}); "
            f"raw_note={scaffold}, question={question}, "
            f"receipt={'written' if receipt_ok else 'not written'}"
        )
    return failed_path if receipt_ok else None


def _source_extraction_prompt(task: dict[str, Any], item: dict[str, Any]) -> str:
    """The extraction prompt for exactly one evidence item.

    The snapshot goes in as raw text between delimiters rather than inside a
    JSON string: ``json.dumps`` escapes every non-ASCII character, which roughly
    doubled the token count of real snapshots, and the model must quote the
    text exactly as the validator will see it.
    """
    source_id = item["source_id"]
    metadata = {key: item[key] for key in ("source_id", "title", "url_or_citation", "source_quality")}
    return (
        "Extract a raw research payload using only the supplied snapshot. "
        f"Return exactly one source, with source_id {source_id}. "
        "Preserve its source_id, title, URL, and source_quality exactly. "
        "Evidence values must be exact snapshot quotations. Do not invent rules, "
        "thresholds, holding periods, or costs.\n\n"
        f"Research ID: {task['research_id']}\nQuestion: {task['question']}\n"
        f"Source metadata:\n{json.dumps(metadata, indent=2, ensure_ascii=False)}\n"
        f"Snapshot text for {source_id}:\n"
        f"<<<BEGIN SNAPSHOT {source_id}>>>\n{item['snapshot_text']}\n<<<END SNAPSHOT {source_id}>>>"
    )


def _merge_extractions(research_id: str, outputs: list[dict[str, Any]]) -> dict[str, Any]:
    """Combine per-source payloads deterministically, in source order.

    The recommendation is kept only when every call agreed; otherwise it falls
    back to ``needs_more_work``, which asserts nothing a per-source validation
    did not already check. The curator does not read this field.
    """
    open_questions: list[str] = []
    for output in outputs:
        for question in output.get("open_questions") or []:
            if question not in open_questions:
                open_questions.append(question)
    recommendations = {output.get("curator_recommendation") for output in outputs}
    return {
        "research_id": research_id,
        "status": "raw_saved",
        "sources": [source for output in outputs for source in output.get("sources") or []],
        "open_questions": open_questions,
        "curator_recommendation": (
            recommendations.pop() if len(recommendations) == 1 else "needs_more_work"
        ),
    }


def _attempt_records(attempts: Any) -> list[dict[str, Any]]:
    return [
        {
            "model": attempt.model,
            "duration_seconds": attempt.duration_seconds,
            "prompt_hash": attempt.prompt_hash,
            "response_hash": attempt.response_hash,
            "validator_ok": attempt.validator_ok,
            "validator_reasons": list(attempt.validator_reasons),
        }
        for attempt in attempts
    ]


def _extract_windows(
    task: dict[str, Any],
    item: dict[str, Any],
    windowed: list[tuple[Any, str]],
    manifest: dict[str, Any],
    *,
    db_path: str | Path,
    run_id: str | None,
    task_id: str | None,
    deadline: float,
    failed_responses: list[dict[str, Any]],
) -> tuple[list[Any], dict[str, Any]]:
    """Run the ladder on every window of one source, in order, then merge them.

    ``manifest`` is updated in place as each window finishes, so a failure
    receipt records every window reached, the one that failed, and those never
    run. The first failed window stops the source, and with it the run. Every
    failed attempt's raw response goes into ``failed_responses``.
    """
    # Function-local for the same reason as in execute_discovery_task: tests
    # rebind ``qwen_call`` on its module.
    from quant_brain.llm.qwen_call import QwenAttempt, QwenValidationError, qwen_call
    from quant_brain.research.windowing import (
        WindowMergeError,
        WindowOutcome,
        merge_window_outcomes,
        validate_window_outcome,
    )

    schema = WindowOutcome.model_json_schema()
    results: list[Any] = []
    outcomes: list[dict[str, Any]] = []
    for (window, prompt), entry in zip(windowed, manifest["windows"], strict=True):

        def validator(parsed: Any, window: Any = window) -> Any:
            return validate_window_outcome(
                parsed, item, window, expected_research_id=task["research_id"]
            )

        try:
            result = qwen_call(
                prompt,
                [item],
                expected_research_id=task["research_id"],
                db_path=db_path,
                run_id=run_id,
                task_id=task_id,
                deadline=deadline,
                validator=validator,
                output_schema=schema,
                attempt_context={
                    "window_id": window.window_id,
                    "window_index": window.index,
                    "window_count": window.count,
                },
            )
        except QwenValidationError as exc:
            failed_responses.extend(
                _failed_responses(exc.attempts, source_id=item["source_id"], window_id=window.window_id)
            )
            entry.update(outcome="failed", validator_ok=False, attempts=_attempt_records(exc.attempts))
            _record_window_event(db_path, run_id, task_id, manifest, entry)
            raise
        failed_responses.extend(
            _failed_responses(
                getattr(result, "attempts", ()), source_id=item["source_id"], window_id=window.window_id
            )
        )
        entry.update(
            outcome=str(result.output["outcome"]).strip(),
            validator_ok=True,
            attempts=_attempt_records(getattr(result, "attempts", ())),
        )
        _record_window_event(db_path, run_id, task_id, manifest, entry)
        results.append(result)
        outcomes.append(result.output)

    try:
        merged = merge_window_outcomes(
            task["research_id"], item, [window for window, _ in windowed], outcomes
        )
    except WindowMergeError as exc:
        raise QwenValidationError(
            [
                QwenAttempt(
                    model="window-merge",
                    duration_seconds=0.0,
                    prompt_hash="",
                    response_hash=hashlib.sha256(
                        json.dumps(outcomes, sort_keys=True).encode("utf-8")
                    ).hexdigest(),
                    validator_ok=False,
                    validator_reasons=(str(exc),),
                )
            ]
        ) from exc
    return results, merged


def _record_window_event(
    db_path: str | Path,
    run_id: str | None,
    task_id: str | None,
    manifest: dict[str, Any],
    entry: dict[str, Any],
) -> None:
    _record_scout_event(
        db_path,
        run_id=run_id,
        task_id=task_id,
        event_type="extraction_window",
        status="completed" if entry["validator_ok"] else "failed",
        message=(
            f"Window {entry['window_id']} ({entry['index']} of {manifest['window_count']}): "
            f"{entry['outcome']}"
        ),
        payload={
            "source_id": manifest["source_id"],
            "snapshot_path": manifest["snapshot_path"],
            "snapshot_sha256": manifest["snapshot_sha256"],
            "snapshot_text_sha256": manifest["snapshot_text_sha256"],
            "window_count": manifest["window_count"],
            **entry,
        },
    )


def execute_discovery_task(
    project_root: str | Path = PROJECT_ROOT,
    db_path: str | Path = DEFAULT_DB_PATH,
    research_id: str | None = None,
    *,
    backend: Any | None = None,
    resolve_write: Any | None = None,
    prepare_if_missing: bool = True,
    max_sources: int = 5,
    run_id: str | None = None,
    task_id: str | None = None,
) -> dict[str, Any]:
    """Run one discovery backend and write a schema-valid raw research note.

    Does not run the curator. Callers (the scout handler) return a recommendation
    so the harness can decide whether curation runs next. Live failures restore
    the research question to ``queued``, write ``Failed_Runs``, and drop any
    incomplete raw-note scaffold.
    """
    from quant_brain.discovery.live_discovery import SeededDiscoveryBackend
    from quant_brain.research.scout_runner import build_scout_prompt, create_raw_research_note

    run_deadline = time.monotonic() + SCOUT_WALL_CLOCK_SECONDS
    root = Path(project_root)
    searcher = backend or SeededDiscoveryBackend()
    # A pre-registered list is an input to the run and is already known before
    # task preparation. Capture it now so even a prepare-stage failure can give
    # an exact, same-lane retry command.
    discovery_lane = getattr(searcher, "discovery_provenance", None)
    task: dict[str, Any] | None = None
    note_path: Path | None = None
    created_scaffold = False
    original_note_bytes: bytes | None = None
    stage = "load_task"
    # Captured once and never re-read from ``sources``:
    # a successful model call rebinds ``sources`` to model output, so reading it
    # at failure time would describe a later write_note failure with
    # model-shaped values instead of what discovery actually fetched. Before
    # discovery it contains only the lane input, never fabricated candidate
    # evidence.
    # Raw text of every failed model attempt, kept only if the run fails closed.
    failed_responses: list[dict[str, Any]] = []
    discovered_provenance: dict[str, Any] = (
        {"discovery_lane": discovery_lane} if discovery_lane else {}
    )
    try:
        if research_id is None:
            with connect(db_path) as conn:
                row = conn.execute(
                    """
                    SELECT * FROM research_questions
                    WHERE status IN ('researching', 'queued')
                    ORDER BY CASE status WHEN 'researching' THEN 0 ELSE 1 END,
                             priority ASC, updated_at ASC
                    LIMIT 1
                    """
                ).fetchone()
            if row is None:
                raise ValueError(
                    "no researching task found; run research_scout_runner.py prepare first"
                )
            task = dict(row)
        else:
            requested = _get_research_task(db_path, research_id)
            # Refused before ``task`` is bound, so the fail-closed path does not
            # run: it would otherwise "recover" this question back to queued and
            # undo the hold a person has not yet reviewed.
            if requested.get("status") == "needs_review":
                raise ValueError(
                    f"{research_id} is held for manual review after a failed raw-note "
                    "recovery; inspect its raw note and release it before dispatching"
                )
            task = requested

        note_path = _resolve_note_path(root, task.get("raw_note_path"))
        if note_path is None:
            if not prepare_if_missing:
                if not task.get("raw_note_path"):
                    raise ValueError(
                        "research task has no raw note path; prepare the task before executing"
                    )
                raise ValueError(f"raw note does not exist: {task.get('raw_note_path')}")
            stage = "prepare_note"
            prompt = build_scout_prompt(task)
            created = create_raw_research_note(root, db_path, task, prompt)
            note_path = Path(created)
            created_scaffold = True
            task = _get_research_task(db_path, task["research_id"])

        stage = "discover"
        # The identity of a pre-registered candidate list is an *input* to the
        # run, known before anything is fetched, so it is captured here rather
        # than after discovery: a failure inside ``discover`` must still name
        # the list it was driven by. It is not candidate evidence, and a search
        # run records nothing here.
        started_payload: dict[str, Any] = {
            "backend": getattr(searcher, "name", type(searcher).__name__)
        }
        if discovery_lane:
            started_payload["discovery_lane"] = discovery_lane
        _record_scout_event(
            db_path,
            run_id=run_id,
            task_id=task_id,
            event_type="discovery_started",
            status="running",
            message=f"Scout discovery started for {task['research_id']}",
            payload=started_payload,
        )
        discovered = searcher.discover(
            task["question"],
            task.get("method_family"),
            limit=max_sources,
            project_root=root,
            resolve_write=resolve_write,
            deadline=run_deadline,
        )
        sources = list(discovered.sources)
        rejected_records = [dict(record) for record in getattr(discovered, "rejected", ())]
        discovered_provenance = {
            **discovered_provenance,
            "research_id": task["research_id"],
            "run_id": run_id,
            "task_id": task_id,
            "accepted_candidates": candidate_evidence(sources),
            "snapshot_paths": list(getattr(discovered, "snapshots", ())),
            "distinct_upstream_count": len(distinct_upstream_keys(sources)),
            "required_upstream_count": MIN_UPSTREAM_SOURCES,
            "rejected_candidates": rejected_records,
            "search_query_expression": getattr(searcher, "last_query_expression", None),
        }
        if not sources:
            raise ValueError("no candidate sources found for this research task")

        # Fail closed BEFORE any raw note is written. A sparse result is a real
        # finding about the literature, not a partial success to be salvaged:
        # it is preserved in a Failed_Runs receipt and never becomes a
        # raw_saved note or a curator recommendation.
        distinct = distinct_upstream_keys(sources)
        if len(distinct) < MIN_UPSTREAM_SOURCES:
            raise InsufficientUpstreamSources(
                f"{len(distinct)} distinct upstream source(s) found, "
                f"Phase 6 requires {MIN_UPSTREAM_SOURCES}",
                detail={
                    "research_id": task["research_id"],
                    "distinct_upstream_count": len(distinct),
                    "required_upstream_count": MIN_UPSTREAM_SOURCES,
                    "accepted_candidates": candidate_evidence(sources),
                    "distinct_upstream_keys": distinct,
                    "rejected_candidates": rejected_records,
                    "search_query_expression": getattr(searcher, "last_query_expression", None),
                    **({"discovery_lane": discovery_lane} if discovery_lane else {}),
                    "follow_up": (
                        "Not a refutation: the question was asked and the reachable "
                        "literature was thin. Widen the lane set (a discovery lane "
                        "that answers documentation or practitioner questions), or "
                        "retain sources manually through the external intake and "
                        "verify their original upstream works. Do not lower "
                        f"MIN_UPSTREAM_SOURCES ({MIN_UPSTREAM_SOURCES}) to pass."
                    ),
                },
            )

        if rejected_records:
            # Immutable, machine-queryable record of what was deliberately not
            # used. The note carries the human-readable copy.
            _record_scout_event(
                db_path,
                run_id=run_id,
                task_id=task_id,
                event_type="discovery_candidates_rejected",
                status="running",
                message=(
                    f"{len(rejected_records)} candidate(s) rejected before extraction "
                    f"for {task['research_id']}"
                ),
                payload={
                    "accepted_count": len(sources),
                    "rejected_count": len(rejected_records),
                    "rejected": rejected_records,
                },
            )

        # Structural invariant: the live backend always extracts through the
        # validated local-Qwen ladder. There is deliberately no override
        # parameter, so no caller and no task payload can disable validation.
        should_run_qwen = searcher.name == "live"
        model_result = None
        if should_run_qwen:
            stage = "qwen_extract"
            # Deliberately function-local: the module attribute is re-read on
            # every call, which is the seam tests rebind. Hoisting this to
            # module scope would silently break that injection point.
            from quant_brain.llm.qwen_call import (
                ESCALATION_MODEL,
                ContextBudgetError,
                QwenAttempt,
                QwenValidationError,
                prompt_budget_violation,
                qwen_call,
            )
            from quant_brain.llm.validators import validate_research_output
            from quant_brain.research.windowing import (
                MAX_WINDOWS_PER_SOURCE,
                plan_windows,
                window_manifest,
                window_prompt,
            )

            evidence_bundle = []
            snapshot_files = []
            for index, (source, snapshot) in enumerate(
                zip(sources, discovered.snapshots, strict=True), start=1
            ):
                snapshot_path = Path(snapshot)
                if not snapshot_path.is_absolute():
                    snapshot_path = root / snapshot_path
                snapshot_files.append((str(snapshot), snapshot_path))
                evidence_bundle.append(
                    {
                        "source_id": f"S{index}",
                        "title": source["title"],
                        "url_or_citation": source["url_or_citation"],
                        "source_quality": source["source_quality"],
                        "snapshot_text": snapshot_path.read_text(encoding="utf-8"),
                    }
                )
            # One source per extraction call (Phase 6 design). A single prompt
            # holding every snapshot ran to ~55k tokens and Ollama silently kept
            # only its tail, so each call now carries exactly one snapshot and
            # must fit the context budget on its own. A source that cannot is
            # read in deterministic windows instead (PROP-006); a source that
            # fits takes exactly the single-prompt path it always did.
            plans: list[tuple[dict[str, Any], str | None, list[tuple[Any, str]] | None]] = []
            for item in evidence_bundle:
                prompt = _source_extraction_prompt(task, item)
                violation = prompt_budget_violation(prompt)
                if violation is None:
                    plans.append((item, prompt, None))
                    continue
                label = f"source {item['source_id']}: {item['url_or_citation']}"
                windows = plan_windows(item["snapshot_text"], item["source_id"])
                if len(windows) > MAX_WINDOWS_PER_SOURCE:
                    raise ContextBudgetError(
                        [],
                        f"{violation}; reading it needs {len(windows)} windows, above the "
                        f"{MAX_WINDOWS_PER_SOURCE}-window cap ({label})",
                    )
                windowed = [(window, window_prompt(task, item, window)) for window in windows]
                plans.append((item, None, windowed))
            # Every prompt, including every window's, is screened before the
            # first model call, so a source that cannot fit fails the run at
            # once instead of after four others.
            for item, prompt, windowed in plans:
                screened = [(item["source_id"], prompt)] if prompt is not None else [
                    (window.window_id, text) for window, text in windowed or []
                ]
                for name, text in screened:
                    violation = prompt_budget_violation(text)
                    if violation is not None:
                        where = "" if name == item["source_id"] else f"window {name} of "
                        raise ContextBudgetError(
                            [],
                            f"{violation} ({where}source {item['source_id']}: "
                            f"{item['url_or_citation']})",
                        )

            # All or nothing, as before: any source -- or any window of a
            # source -- that fails its ladder fails the run. Dropping it could
            # only make the run look better.
            window_manifests: list[dict[str, Any]] = []
            discovered_provenance["extraction_windows"] = window_manifests
            results = []
            outputs = []
            for (item, prompt, windowed), (snapshot_ref, snapshot_path) in zip(
                plans, snapshot_files, strict=True
            ):
                if windowed is None:
                    try:
                        result = qwen_call(
                            prompt,
                            [item],
                            expected_research_id=task["research_id"],
                            db_path=db_path,
                            run_id=run_id,
                            task_id=task_id,
                            deadline=run_deadline,
                        )
                    except QwenValidationError as exc:
                        failed_responses.extend(
                            _failed_responses(exc.attempts, source_id=item["source_id"], window_id=None)
                        )
                        raise
                    failed_responses.extend(
                        _failed_responses(
                            getattr(result, "attempts", ()), source_id=item["source_id"], window_id=None
                        )
                    )
                    results.append(result)
                    outputs.append(result.output)
                    continue
                manifest = window_manifest(
                    item,
                    [window for window, _ in windowed],
                    snapshot_path=snapshot_ref,
                    snapshot_sha256=hashlib.sha256(snapshot_path.read_bytes()).hexdigest(),
                )
                window_manifests.append(manifest)
                window_results, window_outputs = _extract_windows(
                    task,
                    item,
                    windowed,
                    manifest,
                    db_path=db_path,
                    run_id=run_id,
                    task_id=task_id,
                    deadline=run_deadline,
                    failed_responses=failed_responses,
                )
                results.extend(window_results)
                outputs.append(window_outputs)
            merged = _merge_extractions(task["research_id"], outputs)
            # The merged payload must pass the same whole-bundle validation the
            # single-prompt design applied, so splitting can never weaken it.
            verdict = validate_research_output(
                merged, evidence_bundle, expected_research_id=task["research_id"]
            )
            if not verdict.ok:
                raise QwenValidationError(
                    [
                        QwenAttempt(
                            model="merge",
                            duration_seconds=0.0,
                            prompt_hash="",
                            response_hash=hashlib.sha256(
                                json.dumps(merged, sort_keys=True).encode("utf-8")
                            ).hexdigest(),
                            validator_ok=False,
                            validator_reasons=tuple(
                                f"merge: {reason}" for reason in verdict.reasons
                            ),
                        )
                    ]
                )
            models_used = [r.model_used for r in results]
            model_result = SimpleNamespace(
                # What was validated, as the validator normalized it. The raw
                # model output may legally omit fields the schema defaults
                # (E5, RUN-871299ea31: ``possible_strategy_rule``), and the note
                # must record exactly the payload that passed, not a variant.
                output=verdict.normalized,
                model_used=(
                    ESCALATION_MODEL if ESCALATION_MODEL in models_used else models_used[0]
                ),
                repaired=any(r.repaired for r in results),
                escalated=any(r.escalated for r in results),
            )
            sources = list(model_result.output["sources"])

        stage = "write_note"
        findings = format_findings_markdown(
            task,
            sources,
            rejected_records,
            discovery_lane=discovery_lane,
            extraction_windows=discovered_provenance.get("extraction_windows") or None,
            validated_payload=model_result.output if model_result else None,
        )
        # Remember the exact pre-write bytes so a later failure can put the file
        # back rather than leaving a half-finalized note behind.
        original_note_bytes = note_path.read_bytes()
        text = note_path.read_text(encoding="utf-8")
        if "Scout findings go here." in text:
            text = text.replace("Scout findings go here.", findings)
        else:
            text = text.rstrip() + "\n\n" + findings
        text = text.replace("status: researching", "status: raw_saved", 1)
        if resolve_write is not None:
            note_path = resolve_write(note_path)
        note_path.write_text(text, encoding="utf-8")

        update_research_status(
            db_path, task["research_id"], "raw_saved", raw_note_path=str(note_path)
        )
        _record_scout_event(
            db_path,
            run_id=run_id,
            task_id=task_id,
            event_type="discovery_completed",
            status="completed",
            message=f"Scout discovery completed for {task['research_id']}",
            payload={
                "sources_count": len(sources),
                "backend": discovered.backend,
                **({"discovery_lane": discovery_lane} if discovery_lane else {}),
            },
        )
        return {
            "research_id": task["research_id"],
            "status": "raw_saved",
            "raw_note_path": str(note_path),
            "sources_count": len(sources),
            "snapshots": list(discovered.snapshots),
            "backend": discovered.backend,
            "rejected": rejected_records,
            "rejected_count": len(rejected_records),
            "recommendation": "curation",
            "model_used": model_result.model_used if model_result else None,
            "repaired": model_result.repaired if model_result else False,
            "escalated": model_result.escalated if model_result else False,
            "discovery_lane": discovery_lane,
        }
    except Exception as exc:
        if task is not None:
            # Records discovery_failed itself and cannot raise ``Exception``, so
            # the bare ``raise`` below always re-raises ``exc`` -- same object,
            # original traceback -- whatever recovery managed to do.
            _fail_closed_discovery(
                project_root=root,
                db_path=db_path,
                research_id=str(task["research_id"]),
                run_id=run_id,
                task_id=task_id,
                note_path=note_path,
                created_scaffold=created_scaffold,
                stage=stage,
                error=exc,
                resolve_write=resolve_write,
                original_note_bytes=original_note_bytes,
                failed_responses=failed_responses,
                run_provenance={
                    **discovered_provenance,
                    "stage": stage,
                    "error_type": type(exc).__name__,
                },
            )
        raise


def execute_research_task(
    project_root: str | Path = PROJECT_ROOT,
    db_path: str | Path = DEFAULT_DB_PATH,
    research_id: str | None = None,
) -> dict[str, Any]:
    """Fill a prepared raw research note with the seeded starter catalog."""
    from quant_brain.discovery.live_discovery import SeededDiscoveryBackend

    return execute_discovery_task(
        project_root,
        db_path,
        research_id,
        backend=SeededDiscoveryBackend(),
        prepare_if_missing=False,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Execute the next prepared Research Scout task.")
    parser.add_argument("execute", nargs="?", default="execute")
    parser.add_argument("--project-root", default=str(PROJECT_ROOT))
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--research-id", default=None)
    args = parser.parse_args()

    if args.execute != "execute":
        raise SystemExit("Only supported command is: execute")
    result = execute_research_task(args.project_root, args.db, args.research_id)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

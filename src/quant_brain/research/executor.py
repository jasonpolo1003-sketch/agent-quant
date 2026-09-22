from __future__ import annotations

import argparse
import json
from pathlib import Path
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


def distinct_upstream_keys(sources: list[dict[str, Any]]) -> list[str]:
    """Identity of each cited work, for counting against the minimum.

    Counted over normalized URLs rather than list length: arXiv serves the same
    paper as ``.../abs/1234.5678v1`` and ``.../abs/1234.5678``, and
    ``normalize_candidate_url`` treats those as different strings, so
    ``len(sources)`` would let one work satisfy the bar twice. arXiv identities
    are canonicalized here rather than trusting the lane that supplied them --
    a source can reach this point from any lane, or from a hand-written note.
    Sources without a URL fall back to their citation text so an offline
    reference still counts once, and only once.
    """
    from quant_brain.discovery.arxiv_search import canonical_abs_url
    from quant_brain.discovery.source_quality import normalize_candidate_url

    keys: list[str] = []
    for source in sources:
        raw = str(source.get("url_or_citation") or "").strip()
        if not raw:
            continue
        if "://" in raw:
            key = canonical_abs_url(raw) or normalize_candidate_url(raw)
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
) -> str:
    """Format selected sources into a raw research note section plus JSON block.

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

    payload = build_raw_research_payload(task, sources)
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


def _write_failed_run_note(
    project_root: Path,
    *,
    run_id: str,
    research_id: str,
    stage: str,
    error: BaseException,
    resolve_write: Any | None,
    extra: dict[str, Any] | None = None,
) -> str:
    relative = f"brain/00_Inbox/Failed_Runs/{run_id}.md"
    dest = resolve_write(relative) if resolve_write else project_root / relative
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = extra or {}
    text = f"""---
id: {run_id}
type: failed_run
research_id: {research_id}
stage: {stage}
agent_role: research_scout
retryable: true
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

The research question was returned to `queued`. Re-run:

```bash
uv run python scripts/dispatch_task.py --type discovery --research-id {research_id}
```
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
) -> str | None:
    """Restore retryable state, drop incomplete notes, write a Failed_Runs receipt."""
    from uuid import uuid4

    from quant_brain.research.intake import reset_research_for_retry

    failed_run_id = run_id or f"FAIL-{uuid4().hex[:10]}"
    failed_path = None
    try:
        failed_path = _write_failed_run_note(
            project_root,
            run_id=failed_run_id,
            research_id=research_id or "unknown",
            stage=stage,
            error=error,
            resolve_write=resolve_write,
            # Candidate evidence is attached to the *run*, not to one exception
            # class. It used to arrive only via ``error.detail``, which only
            # InsufficientUpstreamSources defines -- so a QwenValidationError
            # (or any post-fetch failure) wrote a receipt naming no source and
            # no snapshot, leaving files on disk that the receipt never
            # referenced. ``run_provenance`` sits *beneath* ``error.detail`` so
            # an exception that does carry its own richer detail still wins.
            extra={
                "task_id": task_id,
                "created_scaffold": created_scaffold,
                **(run_provenance or {}),
                **getattr(error, "detail", {}),
            },
        )
        _record_scout_event(
            db_path,
            run_id=failed_run_id if run_id else None,
            task_id=task_id,
            event_type="failed_run_written",
            status="failed",
            message=f"Wrote Failed_Runs receipt {failed_path}",
            payload={"path": failed_path, "stage": stage},
        )
    except OSError:
        failed_path = None
    if created_scaffold or (note_path is not None and note_path.exists()):
        try:
            _discard_incomplete_raw_note(
                note_path, None if created_scaffold else original_note_bytes
            )
        except OSError:
            _record_scout_event(
                db_path,
                run_id=run_id,
                task_id=task_id,
                event_type="discovery_cleanup_failed",
                status="failed",
                message=f"Could not discard incomplete raw note {note_path}",
                payload={"stage": stage},
            )
    if research_id:
        reset_research_for_retry(db_path, research_id)
    return failed_path


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

    root = Path(project_root)
    searcher = backend or SeededDiscoveryBackend()
    task: dict[str, Any] | None = None
    note_path: Path | None = None
    created_scaffold = False
    original_note_bytes: bytes | None = None
    stage = "load_task"
    # Captured once, at the discover stage, and never re-read from ``sources``:
    # a successful model call rebinds ``sources`` to model output, so reading it
    # at failure time would describe a later write_note failure with
    # model-shaped values instead of what discovery actually fetched. Stays
    # empty when the run fails before discovery, so an early failure reports no
    # candidate evidence rather than inventing an empty finding.
    discovered_provenance: dict[str, Any] = {}
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
            task = _get_research_task(db_path, research_id)

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
        _record_scout_event(
            db_path,
            run_id=run_id,
            task_id=task_id,
            event_type="discovery_started",
            status="running",
            message=f"Scout discovery started for {task['research_id']}",
            payload={"backend": getattr(searcher, "name", type(searcher).__name__)},
        )
        discovered = searcher.discover(
            task["question"],
            task.get("method_family"),
            limit=max_sources,
            project_root=root,
            resolve_write=resolve_write,
        )
        sources = list(discovered.sources)
        rejected_records = [dict(record) for record in getattr(discovered, "rejected", ())]
        discovered_provenance = {
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
            from quant_brain.llm.qwen_call import qwen_call

            evidence_bundle = []
            for index, (source, snapshot) in enumerate(
                zip(sources, discovered.snapshots, strict=True), start=1
            ):
                snapshot_path = Path(snapshot)
                if not snapshot_path.is_absolute():
                    snapshot_path = root / snapshot_path
                evidence_bundle.append(
                    {
                        "source_id": f"S{index}",
                        "title": source["title"],
                        "url_or_citation": source["url_or_citation"],
                        "source_quality": source["source_quality"],
                        "snapshot_text": snapshot_path.read_text(encoding="utf-8"),
                    }
                )
            extraction_prompt = (
                "Extract a raw research payload using only the supplied snapshots. "
                "Preserve each source_id, title, URL, and source_quality exactly. "
                "Evidence values must be exact snapshot quotations. Do not invent rules, "
                "thresholds, holding periods, or costs.\n\n"
                f"Research ID: {task['research_id']}\nQuestion: {task['question']}\n"
                f"Evidence bundle:\n{json.dumps(evidence_bundle, indent=2)}"
            )
            model_result = qwen_call(
                extraction_prompt,
                evidence_bundle,
                expected_research_id=task["research_id"],
                db_path=db_path,
                run_id=run_id,
                task_id=task_id,
            )
            sources = list(model_result.output["sources"])

        stage = "write_note"
        findings = format_findings_markdown(task, sources, rejected_records)
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
            payload={"sources_count": len(sources), "backend": discovered.backend},
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
        }
    except Exception as exc:
        if task is not None:
            _record_scout_event(
                db_path,
                run_id=run_id,
                task_id=task_id,
                event_type="discovery_failed",
                status="failed",
                message=str(exc),
                payload={"stage": stage, "error": type(exc).__name__},
            )
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

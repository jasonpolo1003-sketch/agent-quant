from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from quant_brain.config import PROJECT_ROOT
from quant_brain.db.init_db import DEFAULT_DB_PATH, connect, init_database
from quant_brain.research.intake import update_research_status
from quant_brain.research.schema import validate_raw_research_payload

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
        "risks": ["If this is ignored, a strategy can appear profitable only because it cheats with future data."],
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
        "risks": ["Framework convenience does not prevent bad signal timing, bad data, or overfitting."],
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
        "risks": ["Do not treat book reputation as evidence for a specific ETF strategy without a sourced passage and backtest."],
        "confidence": "medium",
        "source_quality": "practitioner",
        "asset_classes": ["equity", "etf", "futures"],
        "data_required": ["user-owned copy or legal preview for exact quotes"],
        "data_access": "available-later",
        "mvp_testable": False,
    },
]


def select_candidate_sources(method_family: str | None, question: str, limit: int = 8) -> list[dict[str, Any]]:
    """Select a small set of relevant starter sources for a research task."""
    family = method_family or "unclassified"
    question_lower = question.lower()
    selected = []
    for source in STARTER_SOURCES:
        families = source.get("method_families", [])
        title_claim = f"{source['title']} {source['main_claim']}".lower()
        if family in families or "all" in families or any(term in title_claim for term in question_lower.split()):
            selected.append({k: v for k, v in source.items() if k != "method_families"})
    return selected[:limit]


def format_findings_markdown(task: dict[str, Any], sources: list[dict[str, Any]]) -> str:
    """Format selected sources into a raw research note section plus JSON block."""
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

    payload = build_raw_research_payload(task, sources)
    lines.extend(["## Required JSON Block", "", "```json", json.dumps(payload, indent=2), "```", ""])
    return "\n".join(lines)


def build_raw_research_payload(task: dict[str, Any], sources: list[dict[str, Any]]) -> dict[str, Any]:
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


def execute_discovery_task(
    project_root: str | Path = PROJECT_ROOT,
    db_path: str | Path = DEFAULT_DB_PATH,
    research_id: str | None = None,
    *,
    backend: Any | None = None,
    resolve_write: Any | None = None,
    prepare_if_missing: bool = True,
    max_sources: int = 5,
) -> dict[str, Any]:
    """Run one discovery backend and write a schema-valid raw research note.

    Does not run the curator. Callers (the scout handler) return a recommendation
    so the harness can decide whether curation runs next.
    """
    from quant_brain.discovery.live_discovery import SeededDiscoveryBackend
    from quant_brain.research.scout_runner import build_scout_prompt, create_raw_research_note

    root = Path(project_root)
    searcher = backend or SeededDiscoveryBackend()
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
            raise ValueError("no researching task found; run research_scout_runner.py prepare first")
        task = dict(row)
    else:
        task = _get_research_task(db_path, research_id)

    note_path = _resolve_note_path(root, task.get("raw_note_path"))
    if note_path is None:
        if not prepare_if_missing:
            if not task.get("raw_note_path"):
                raise ValueError("research task has no raw note path; prepare the task before executing")
            raise ValueError(f"raw note does not exist: {task.get('raw_note_path')}")
        prompt = build_scout_prompt(task)
        created = create_raw_research_note(root, db_path, task, prompt)
        note_path = Path(created)
        task = _get_research_task(db_path, task["research_id"])

    discovered = searcher.discover(
        task["question"],
        task.get("method_family"),
        limit=max_sources,
        project_root=root,
        resolve_write=resolve_write,
    )
    sources = list(discovered.sources)
    if not sources:
        raise ValueError("no candidate sources found for this research task")

    findings = format_findings_markdown(task, sources)
    text = note_path.read_text(encoding="utf-8")
    if "Scout findings go here." in text:
        text = text.replace("Scout findings go here.", findings)
    else:
        text = text.rstrip() + "\n\n" + findings
    text = text.replace("status: researching", "status: raw_saved", 1)
    if resolve_write is not None:
        note_path = resolve_write(note_path)
    note_path.write_text(text, encoding="utf-8")

    update_research_status(db_path, task["research_id"], "raw_saved", raw_note_path=str(note_path))
    return {
        "research_id": task["research_id"],
        "status": "raw_saved",
        "raw_note_path": str(note_path),
        "sources_count": len(sources),
        "snapshots": list(discovered.snapshots),
        "backend": discovered.backend,
        "recommendation": "curation",
    }


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

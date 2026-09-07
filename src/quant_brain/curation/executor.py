from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from quant_brain.config import PROJECT_ROOT
from quant_brain.curation.promotion import CuratedSource, promote_source_note
from quant_brain.db.init_db import DEFAULT_DB_PATH, connect, init_database
from quant_brain.research.intake import update_research_status
from quant_brain.research.schema import validate_raw_research_payload

JSON_BLOCK_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)
PROMOTABLE_SOURCE_QUALITIES = {"primary", "practitioner"}


@dataclass
class CuratorResult:
    research_id: str
    status: str
    curator_note_path: str
    promoted_sources_count: int
    skipped_sources_count: int
    promoted_paths: list[str]


def extract_scout_json(raw_note_path: str | Path) -> dict[str, Any]:
    """Extract the final fenced JSON payload from a raw research note."""
    text = Path(raw_note_path).read_text(encoding="utf-8")
    matches = JSON_BLOCK_RE.findall(text)
    if not matches:
        raise ValueError(f"raw research note has no fenced JSON block: {raw_note_path}")
    try:
        return json.loads(matches[-1])
    except json.JSONDecodeError as exc:
        raise ValueError(f"raw research note contains invalid JSON: {exc}") from exc


def source_payload_to_curated_source(
    research_id: str,
    payload: dict[str, Any],
    method_family: str | None = None,
) -> CuratedSource:
    """Convert a scout source payload into the CuratedSource contract."""
    evidence = payload.get("evidence")
    evidence_list = [evidence] if isinstance(evidence, str) and evidence.strip() else list(evidence or [])
    rule = payload.get("possible_strategy_rule") or ""
    return CuratedSource(
        research_id=research_id,
        title=payload.get("title", "Untitled Source"),
        source_type=payload.get("source_type", "other"),
        url=payload.get("url_or_citation"),
        summary=payload.get("main_claim", "No summary recorded."),
        useful_claims=[payload.get("main_claim", "")],
        strategy_rules=[rule] if rule else [],
        risks=list(payload.get("risks") or []),
        confidence=payload.get("confidence", "low"),
        method_family=method_family,
        evidence=evidence_list,
        trust_level=payload.get("source_quality", "unknown"),
    )


def _get_task(db_path: str | Path, research_id: str) -> dict[str, Any]:
    init_database(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM research_questions WHERE research_id = ?", (research_id,)
        ).fetchone()
    if row is None:
        raise KeyError(f"research_id not found: {research_id}")
    return dict(row)


def _next_raw_saved_task(db_path: str | Path) -> dict[str, Any] | None:
    init_database(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT * FROM research_questions
            WHERE status = 'raw_saved'
            ORDER BY priority ASC, updated_at ASC
            LIMIT 1
            """
        ).fetchone()
    return dict(row) if row else None


def _write_curator_note(
    project_root: str | Path,
    research_id: str,
    promoted_paths: list[str],
    skipped_sources: list[dict[str, Any]],
    open_questions: list[str],
) -> str:
    root = Path(project_root)
    out_dir = root / "brain" / "00_Inbox" / "Curator_Reviews"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{research_id}-curated.md"
    promoted_lines = "\n".join(f"- {p}" for p in promoted_paths) or "- None"
    skipped_lines = (
        "\n".join(
            f"- {s.get('title', 'Untitled')} — skipped because not MVP-testable or not ready"
            for s in skipped_sources
        )
        or "- None"
    )
    question_lines = "\n".join(f"- {q}" for q in open_questions) or "- None"
    text = f"""---
id: CUR-{uuid4().hex[:8]}
type: curator_review
research_id: {research_id}
verdict: curated
reviewer: knowledge_curator_executor
---

# Curator Review — {research_id}

## Verdict

curated

## Promoted Source Notes

{promoted_lines}

## Skipped Sources

{skipped_lines}

## Open Questions For Next Research Pass

{question_lines}

## Why This Is Conservative

Only MVP-testable sources were promoted into the durable source-note layer. Background-only sources remain in the raw research note until a human or future source-ingestion step adds exact supporting passages.
"""
    path.write_text(text, encoding="utf-8")
    return str(path)


def _record_finding(
    db_path: str | Path,
    research_id: str,
    source_id: str | None,
    claim: str,
    evidence: str,
    confidence: str,
) -> None:
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO research_findings (
                finding_id, research_id, source_id, claim, evidence, confidence, status
            ) VALUES (?, ?, ?, ?, ?, ?, 'curated')
            """,
            (f"FIND-{uuid4().hex[:10]}", research_id, source_id, claim, evidence, confidence),
        )
        conn.commit()


def execute_curator_task(
    project_root: str | Path = PROJECT_ROOT,
    db_path: str | Path = DEFAULT_DB_PATH,
    research_id: str | None = None,
) -> CuratorResult:
    """Curate one raw research note into promoted source notes and DB findings."""
    task = _get_task(db_path, research_id) if research_id else _next_raw_saved_task(db_path)
    if task is None:
        raise ValueError("no raw_saved research task found")
    if task.get("status") not in {"raw_saved", "curated"}:
        raise ValueError(f"research task is not ready for curation: {task.get('status')}")
    raw_note_path = task.get("raw_note_path")
    if not raw_note_path:
        raise ValueError("research task has no raw note path")

    payload = validate_raw_research_payload(extract_scout_json(raw_note_path))
    if payload.get("research_id") != task["research_id"]:
        raise ValueError("raw note JSON research_id does not match database task")

    # Make repeated curator runs idempotent for this research task.
    with connect(db_path) as conn:
        conn.execute("DELETE FROM research_findings WHERE research_id = ?", (task["research_id"],))
        conn.commit()

    promoted_paths: list[str] = []
    skipped_sources: list[dict[str, Any]] = []
    for source_payload in payload.get("sources", []):
        source_quality = source_payload.get("source_quality", "discovery-only")
        if (
            not source_payload.get("mvp_testable", False)
            or source_quality not in PROMOTABLE_SOURCE_QUALITIES
        ):
            skipped_sources.append(source_payload)
            continue
        source = source_payload_to_curated_source(
            task["research_id"], source_payload, task.get("method_family")
        )
        path = promote_source_note(project_root, db_path, source)
        promoted_paths.append(path)
        # Derive source ID from path prefix via DB lookup; keep it simple and auditable.
        with connect(db_path) as conn:
            row = conn.execute("SELECT source_id FROM sources WHERE url = ?", (source.url,)).fetchone()
        source_id = row["source_id"] if row else None
        _record_finding(
            db_path,
            task["research_id"],
            source_id,
            source.useful_claims[0] if source.useful_claims else source.summary,
            source.evidence[0] if source.evidence else "",
            source.confidence,
        )

    curator_note_path = _write_curator_note(
        project_root,
        task["research_id"],
        promoted_paths,
        skipped_sources,
        list(payload.get("open_questions") or []),
    )
    final_status = "curated" if promoted_paths else "rejected"
    update_research_status(
        db_path,
        task["research_id"],
        final_status,
        curator_note_path=curator_note_path,
        source_note_path=promoted_paths[0] if promoted_paths else None,
    )
    return CuratorResult(
        research_id=task["research_id"],
        status=final_status,
        curator_note_path=curator_note_path,
        promoted_sources_count=len(promoted_paths),
        skipped_sources_count=len(skipped_sources),
        promoted_paths=promoted_paths,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Execute Knowledge Curator on one raw research task.")
    parser.add_argument("execute", nargs="?", default="execute")
    parser.add_argument("--project-root", default=str(PROJECT_ROOT))
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--research-id", default=None)
    args = parser.parse_args()
    if args.execute != "execute":
        raise SystemExit("Only supported command is: execute")
    result = execute_curator_task(args.project_root, args.db, args.research_id)
    print(json.dumps(result.__dict__, indent=2))


if __name__ == "__main__":
    main()

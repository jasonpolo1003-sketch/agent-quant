from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from quant_brain.db.init_db import DEFAULT_DB_PATH, connect, init_database
from quant_brain.research.intake import update_research_status

SAFE_FILENAME_RE = re.compile(r"[^a-zA-Z0-9_-]+")


@dataclass
class PromotionDecision:
    research_id: str
    verdict: str
    reason: str
    source_quality: str = "unknown"
    next_location: str | None = None
    reviewer: str = "knowledge_curator"


@dataclass
class CuratedSource:
    research_id: str
    title: str
    source_type: str
    url: str | None
    summary: str
    useful_claims: list[str] = field(default_factory=list)
    strategy_rules: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    confidence: str = "low"
    method_family: str | None = None
    evidence: list[str] = field(default_factory=list)
    trust_level: str = "unknown"


def slugify(text: str) -> str:
    cleaned = SAFE_FILENAME_RE.sub("-", text.strip().lower()).strip("-")
    return cleaned[:80] or "untitled"


def source_type_folder(source_type: str) -> str:
    """Map source types to clean source-note folders."""
    return {
        "web": "web",
        "docs": "docs",
        "blog": "blogs",
        "book": "books",
        "paper": "papers",
        "repo": "repos",
        "other": "other",
    }.get(source_type, source_type)


def stable_source_id(source: CuratedSource) -> str:
    basis = source.url or f"{source.title}|{source.summary}"
    return "SRC-" + hashlib.sha256(basis.encode("utf-8")).hexdigest()[:10]


def create_curator_review(project_root: str | Path, decision: PromotionDecision) -> str:
    root = Path(project_root)
    out_dir = root / "brain" / "00_Inbox" / "Curator_Reviews"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{decision.research_id}-{slugify(decision.verdict)}.md"
    text = f"""---
id: CUR-{uuid4().hex[:8]}
type: curator_review
research_id: {decision.research_id}
verdict: {decision.verdict}
source_quality: {decision.source_quality}
reviewer: {decision.reviewer}
next_location: {decision.next_location or ''}
---

# Curator Review — {decision.research_id}

## Verdict

{decision.verdict}

## Reason

{decision.reason}

## Source Quality

{decision.source_quality}

## Next Location

{decision.next_location or 'None'}
"""
    path.write_text(text, encoding="utf-8")
    return str(path)


def _markdown_list(items: list[str]) -> str:
    if not items:
        return "- None recorded"
    return "\n".join(f"- {item}" for item in items)


def validate_curated_source(source: CuratedSource) -> None:
    if not source.title.strip():
        raise ValueError("curated source needs a title")
    if not source.summary.strip():
        raise ValueError("curated source needs a summary")
    joined_claims = "\n".join(source.useful_claims).lower()

    hype_phrases = [
        "always beats the market",
        "guaranteed profit",
        "risk free",
        "can't lose",
        "never loses",
    ]
    if source.confidence == "high" and any(phrase in joined_claims for phrase in hype_phrases):
        raise ValueError("high-confidence profit claims need direct evidence and reviewer skepticism")

    has_evidence = bool(source.evidence) or bool(source.url)
    explicitly_unverified = "unverified" in joined_claims or source.confidence == "low"
    if source.useful_claims and not has_evidence and not explicitly_unverified:
        raise ValueError("useful claims need evidence, a source URL, or an unverified/low-confidence label")


def promote_source_note(project_root: str | Path, db_path: str | Path, source: CuratedSource) -> str:
    """Promote a curated finding into a durable source note and database source row."""
    validate_curated_source(source)
    root = Path(project_root)
    source_dir = root / "brain" / "01_Sources" / source_type_folder(source.source_type)
    source_dir.mkdir(parents=True, exist_ok=True)
    source_id = stable_source_id(source)
    note_path = source_dir / f"{source_id}-{slugify(source.title)}.md"
    rel_note_path = note_path.relative_to(root).as_posix()

    text = f"""---
id: {source_id}
type: source_note
source_kind: {source.source_type}
status: curated
research_id: {source.research_id}
title: {source.title}
url: {source.url or ''}
trust_level: {source.trust_level}
confidence: {source.confidence}
method_family: {source.method_family or ''}
---

# Source — {source.title}

## Citation

{source.url or 'No URL recorded'}

## Summary

{source.summary}

## Useful Claims

{_markdown_list(source.useful_claims)}

## Evidence

{_markdown_list(source.evidence)}

## Possible Strategy Rules

{_markdown_list(source.strategy_rules)}

## Risks / Caveats

{_markdown_list(source.risks)}

## Curator Notes

Promoted from research task `{source.research_id}`. This source is allowed into the durable brain, but strategy cards still require precise testable rules and a later review.
"""
    note_path.write_text(text, encoding="utf-8")

    init_database(db_path)
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO notes (note_id, path, title, type, status)
            VALUES (?, ?, ?, 'source_note', 'curated')
            ON CONFLICT(note_id) DO UPDATE SET
                path = excluded.path,
                title = excluded.title,
                status = excluded.status,
                updated_at = CURRENT_TIMESTAMP
            """,
            (source_id, rel_note_path, source.title),
        )
        conn.execute(
            """
            INSERT INTO sources (source_id, title, url, source_type, trust_level, note_id)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_id) DO UPDATE SET
                title = excluded.title,
                url = excluded.url,
                source_type = excluded.source_type,
                trust_level = excluded.trust_level,
                note_id = excluded.note_id
            """,
            (source_id, source.title, source.url, source.source_type, source.trust_level, source_id),
        )
        conn.commit()

    update_research_status(db_path, source.research_id, "curated", source_note_path=str(note_path))
    return str(note_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Curator promotion tools.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    review = sub.add_parser("review-stub")
    review.add_argument("research_id")
    review.add_argument("--verdict", default="needs_more_work")
    review.add_argument("--reason", default="Curator review needed before promotion.")
    review.add_argument("--quality", default="unknown")
    review.add_argument("--project-root", default=".")

    promote = sub.add_parser("promote-source-json")
    promote.add_argument("json_path")
    promote.add_argument("--db", default=str(DEFAULT_DB_PATH))
    promote.add_argument("--project-root", default=".")

    args = parser.parse_args()
    if args.cmd == "review-stub":
        path = create_curator_review(
            args.project_root,
            PromotionDecision(
                research_id=args.research_id,
                verdict=args.verdict,
                reason=args.reason,
                source_quality=args.quality,
            ),
        )
        print(path)
    elif args.cmd == "promote-source-json":
        data = json.loads(Path(args.json_path).read_text(encoding="utf-8"))
        path = promote_source_note(args.project_root, args.db, CuratedSource(**data))
        print(path)


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import json
from pathlib import Path
from uuid import uuid4

from quant_brain.config import PROJECT_ROOT
from quant_brain.db.init_db import DEFAULT_DB_PATH, connect, init_database

# ``needs_review``: a failed Scout run left a raw note it could not recover. No
# selector picks it up and Scout dispatch refuses it until a person releases it.
VALID_STATUSES = {
    "queued",
    "researching",
    "raw_saved",
    "curating",
    "curated",
    "rejected",
    "needs_review",
}


def new_research_id() -> str:
    return f"RQ-{uuid4().hex[:8]}"


def add_research_question(
    db_path: str | Path,
    question: str,
    method_family: str | None = None,
    priority: int = 3,
    assigned_agent: str = "research_scout",
) -> dict[str, object]:
    if not question.strip():
        raise ValueError("research question cannot be empty")
    if priority < 1 or priority > 5:
        raise ValueError("priority must be between 1 and 5")

    init_database(db_path)
    research_id = new_research_id()
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO research_questions (
                research_id, question, method_family, priority, status, assigned_agent
            ) VALUES (?, ?, ?, ?, 'queued', ?)
            """,
            (research_id, question.strip(), method_family, priority, assigned_agent),
        )
        conn.commit()
    return {
        "research_id": research_id,
        "question": question.strip(),
        "method_family": method_family,
        "priority": priority,
        "status": "queued",
        "assigned_agent": assigned_agent,
    }


def list_research_questions(
    db_path: str | Path = DEFAULT_DB_PATH,
    status: str | None = None,
) -> list[dict[str, object]]:
    init_database(db_path)
    sql = "SELECT * FROM research_questions"
    params: tuple[object, ...] = ()
    if status:
        sql += " WHERE status = ?"
        params = (status,)
    sql += " ORDER BY CASE status WHEN 'queued' THEN 0 ELSE 1 END, priority ASC, created_at ASC"
    with connect(db_path) as conn:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]


def update_research_status(
    db_path: str | Path,
    research_id: str,
    status: str,
    raw_note_path: str | None = None,
    source_note_path: str | None = None,
    curator_note_path: str | None = None,
) -> None:
    if status not in VALID_STATUSES:
        raise ValueError(f"invalid research status: {status}")

    completed_expr = ", completed_at = CURRENT_TIMESTAMP" if status in {"curated", "rejected"} else ""
    with connect(db_path) as conn:
        cur = conn.execute(
            f"""
            UPDATE research_questions
            SET status = ?,
                raw_note_path = COALESCE(?, raw_note_path),
                source_note_path = COALESCE(?, source_note_path),
                curator_note_path = COALESCE(?, curator_note_path),
                updated_at = CURRENT_TIMESTAMP
                {completed_expr}
            WHERE research_id = ?
            """,
            (status, raw_note_path, source_note_path, curator_note_path, research_id),
        )
        if cur.rowcount != 1:
            raise KeyError(f"research_id not found: {research_id}")
        conn.commit()


def reset_research_for_retry(
    db_path: str | Path, research_id: str, *, clear_raw_note_path: bool = True
) -> None:
    """Return a research question to queued, clearing the raw-note path by default.

    ``clear_raw_note_path=False`` keeps the pointer for a note the failed run did
    not own (a pre-existing note, left or restored), so a retry reuses that note
    instead of recreating -- and overwriting -- it at the same path.
    """
    with connect(db_path) as conn:
        cur = conn.execute(
            """
            UPDATE research_questions
            SET status = 'queued',
                raw_note_path = CASE WHEN ? THEN NULL ELSE raw_note_path END,
                updated_at = CURRENT_TIMESTAMP
            WHERE research_id = ?
            """,
            (clear_raw_note_path, research_id),
        )
        if cur.rowcount != 1:
            raise KeyError(f"research_id not found: {research_id}")
        conn.commit()


def create_research_brief(project_root: str | Path, task: dict[str, object]) -> str:
    root = Path(project_root)
    inbox = root / "brain" / "00_Inbox" / "Research_Briefs"
    inbox.mkdir(parents=True, exist_ok=True)
    research_id = str(task["research_id"])
    path = inbox / f"{research_id}.md"
    method_family = task.get("method_family") or "unclassified"
    text = f"""---
id: {research_id}
type: research_brief
status: queued
method_family: {method_family}
priority: {task.get('priority', 3)}
assigned_agent: {task.get('assigned_agent', 'research_scout')}
---

# Research Brief — {research_id}

## Research Question

{task['question']}

## Agent Task

Find useful sources that help answer this question. Extract concrete claims, strategy rules, risks, and limitations. Save messy notes here first; do not create strategy cards unless the method is clearly testable.

## Allowed Write Locations

- Raw notes: `brain/00_Inbox/`
- Research briefs: `brain/00_Inbox/Research_Briefs/`
- Source notes after curation: `brain/01_Sources/`
- Method doors after curation: `brain/02_Strategy_Doors/`

## Required Output Format

For each useful source:

```text
Source URL / citation:
Source type: paper | book | blog | repo | docs | other
Main claim:
Evidence quote or exact passage:
Possible strategy rule:
Risks / caveats:
Confidence: low | medium | high
```

## Rules

- Do not download copyrighted books illegally.
- Use high-quality sources: books, papers, official docs, public repos, reputable blogs, previews, or user-provided files.
- Cite every source.
- Label uncertain claims as `unverified`.
- Prefer fewer high-quality sources over many weak sources.
- Do not paper trade or live trade anything.
"""
    path.write_text(text, encoding="utf-8")
    return str(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage quant research intake queue.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    add = sub.add_parser("add")
    add.add_argument("question")
    add.add_argument("--family", default=None)
    add.add_argument("--priority", type=int, default=3)
    add.add_argument("--db", default=str(DEFAULT_DB_PATH))
    add.add_argument("--brief", action="store_true")

    list_cmd = sub.add_parser("list")
    list_cmd.add_argument("--status", default=None)
    list_cmd.add_argument("--db", default=str(DEFAULT_DB_PATH))

    args = parser.parse_args()
    if args.cmd == "add":
        task = add_research_question(args.db, args.question, args.family, args.priority)
        if args.brief:
            task["brief_path"] = create_research_brief(PROJECT_ROOT, task)
        print(json.dumps(task, indent=2))
    elif args.cmd == "list":
        print(json.dumps(list_research_questions(args.db, args.status), indent=2))


if __name__ == "__main__":
    main()

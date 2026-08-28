from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from quant_brain.config import PROJECT_ROOT
from quant_brain.db.init_db import DEFAULT_DB_PATH, connect, init_database
from quant_brain.research.intake import update_research_status


def claim_next_research_task(db_path: str | Path = DEFAULT_DB_PATH) -> dict[str, Any] | None:
    """Claim the highest-priority queued research question for the scout."""
    init_database(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT * FROM research_questions
            WHERE status = 'queued'
            ORDER BY priority ASC, created_at ASC
            LIMIT 1
            """
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """
            UPDATE research_questions
            SET status = 'researching', updated_at = CURRENT_TIMESTAMP
            WHERE research_id = ?
            """,
            (row["research_id"],),
        )
        conn.commit()
        claimed = dict(row)
        claimed["status"] = "researching"
        return claimed


def build_scout_prompt(task: dict[str, Any]) -> str:
    """Build a bounded, agent-readable prompt for one research task."""
    method_family = task.get("method_family") or "unclassified"
    return f"""# Research Scout Task

You are the Research Scout for Quant Agent Brain.

## Research ID

{task['research_id']}

## Research Question

{task['question']}

## Method Family

{method_family}

## Mission

Find useful sources that answer the research question. Prioritize books, papers, reputable blogs, public repos, official documentation, credible practitioner writeups, and user-provided files.

## Research Universe

Quant Agent Brain is not restricted to one asset class, market, or strategy family. Research may cover equities, ETFs, futures, rates, foreign exchange, commodities, options, crypto, market microstructure, alternative data, portfolio construction, or other traceable quantitative ideas.

Broad discovery does not mean automatic promotion. Discovery is not proof.

## Discovery Tools

Use Agent Reach (`https://github.com/Panniantong/Agent-Reach`) as the live-source router when available. It may discover web pages, GitHub material, YouTube transcripts, RSS, and social discussions. Treat blogs, videos, and social posts as leads unless their claims are independently supported.

## Source Quality

- Prefer primary sources, papers, official documentation, datasets, and named practitioner research.
- Preserve useful practitioner blogs and interviews when the author, method, and limitations are identifiable.
- Label social/video-only claims as discovery evidence until corroborated.
- Reject untraceable performance screenshots, guaranteed-return claims, copied summaries without provenance, and rules that hide data, costs, or timing.

## Hard Boundaries

- Do not create strategy cards.
- Do not run backtests.
- Do not paper trade or live trade.
- Do not claim a strategy works just because a source says so.
- Do not illegally download copyrighted books.
- Save messy findings under `brain/00_Inbox` only.

## What To Extract

For each source, separate:

1. Source URL / citation.
2. Main claim.
3. Evidence quote or exact passage when available.
4. Possible testable strategy rule.
5. Required data.
6. Risks and caveats.
7. Confidence: low / medium / high.
8. Relevant asset class, market, and implementation horizon.
9. Data required and whether it is accessible now, later, or not realistically available.
10. Source quality: primary | practitioner | discovery-only.

## Required JSON Block

At the end of the raw note, include a fenced JSON block exactly like this shape:

```json
{{
  "research_id": "{task['research_id']}",
  "status": "raw_saved",
  "sources": [
    {{
      "title": "",
      "source_type": "book|paper|blog|repo|docs|other",
      "url_or_citation": "",
      "main_claim": "",
      "evidence": "",
      "possible_strategy_rule": "",
      "risks": [],
      "confidence": "low|medium|high",
      "source_quality": "primary|practitioner|discovery-only|reject",
      "asset_classes": [],
      "data_required": [],
      "data_access": "available-now|available-later|not-realistic",
      "mvp_testable": true
    }}
  ],
  "open_questions": [],
  "curator_recommendation": "promote_source|update_door|create_strategy_card|needs_more_work|rejected"
}}
```

## Output Location

Write raw findings to `brain/00_Inbox/Raw_Research/{task['research_id']}.md`.
"""


def create_raw_research_note(
    project_root: str | Path,
    db_path: str | Path,
    task: dict[str, Any],
    prompt: str,
) -> str:
    """Create the raw note scaffold the scout should fill in."""
    root = Path(project_root)
    out_dir = root / "brain" / "00_Inbox" / "Raw_Research"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{task['research_id']}.md"
    text = f"""---
id: {task['research_id']}
type: raw_research
status: researching
method_family: {task.get('method_family') or 'unclassified'}
assigned_agent: research_scout
---

# Raw Research Note — {task['research_id']}

## Research Question

{task['question']}

## Scout Prompt

{prompt}

## Paste / Agent Findings

Scout findings go here.

## Required JSON Block

The scout must finish with the JSON block requested in the prompt.
"""
    path.write_text(text, encoding="utf-8")
    update_research_status(db_path, task["research_id"], "researching", raw_note_path=str(path))
    return str(path)


def prepare_next_research_run(
    project_root: str | Path = PROJECT_ROOT,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> dict[str, Any] | None:
    """Claim the next research task and prepare its raw note/prompt packet."""
    task = claim_next_research_task(db_path)
    if task is None:
        return None
    prompt = build_scout_prompt(task)
    raw_note_path = create_raw_research_note(project_root, db_path, task, prompt)
    return {
        "research_id": task["research_id"],
        "question": task["question"],
        "method_family": task.get("method_family"),
        "prompt": prompt,
        "raw_note_path": raw_note_path,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare Research Scout work packets.")
    parser.add_argument("prepare", nargs="?", default="prepare")
    parser.add_argument("--project-root", default=str(PROJECT_ROOT))
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    args = parser.parse_args()

    if args.prepare != "prepare":
        raise SystemExit("Only supported command is: prepare")

    prepared = prepare_next_research_run(args.project_root, args.db)
    print(json.dumps(prepared, indent=2))


if __name__ == "__main__":
    main()

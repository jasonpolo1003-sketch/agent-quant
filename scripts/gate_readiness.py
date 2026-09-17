"""Can the currently available lanes answer *this* research question?

A different question from `scripts/agent_reach_check.py`. That one asks whether
any lane is working; this one asks whether the working lanes can actually reach
the Phase 6 minimum source count for a specific research ID. A lane can be
perfectly healthy and still be unable to answer a given question -- GitHub
returns code repositories, which will not answer a question about documented
transaction-cost assumptions.

This is a read-only probe. It runs the same search the Scout would run and
counts candidate URLs. It fetches nothing, snapshots nothing, calls no model,
and writes no research artifact, so running it is not a research run.

    uv run python scripts/gate_readiness.py --research-id RQ-6d9c12f4
    uv run python scripts/gate_readiness.py --research-id RQ-6d9c12f4 --min-sources 3

Exit codes:
    0  the available lanes can reach the minimum
    2  Agent Reach itself is unusable
    3  the research ID is unknown
    4  the lanes answered, but cannot reach the minimum
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from quant_brain.db.init_db import DEFAULT_DB_PATH, connect
from quant_brain.discovery.agent_reach import (
    AgentReachAdapter,
    AgentReachError,
    plan_queries,
)
from quant_brain.discovery.source_quality import normalize_candidate_url

# brain/_system/plan/phase_06_research_scout_agent.md: a raw research note must
# cite at least three upstream sources.
PHASE_6_MIN_SOURCES = 3


def load_question(db_path: str | Path, research_id: str) -> dict[str, Any] | None:
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT research_id, question, method_family, status "
            "FROM research_questions WHERE research_id = ?",
            (research_id,),
        ).fetchone()
    return dict(row) if row is not None else None


def probe(
    adapter: AgentReachAdapter,
    question: str,
    method_family: str | None,
    *,
    min_sources: int,
) -> dict[str, Any]:
    """Run the Scout's own search and count distinct candidate URLs."""
    queries = plan_queries(question, method_family)
    try:
        hits = adapter.search_for_question(question, method_family, limit=min_sources)
    except AgentReachError as exc:
        return {
            "queries": queries,
            "unique_urls": 0,
            "urls": [],
            "error": str(exc),
        }
    unique = {normalize_candidate_url(str(hit.get("url") or "")) for hit in hits}
    unique.discard("")
    return {
        "queries": queries,
        "unique_urls": len(unique),
        "urls": sorted(unique),
        "error": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--research-id", required=True)
    parser.add_argument("--db", default=DEFAULT_DB_PATH)
    parser.add_argument(
        "--min-sources",
        type=int,
        default=PHASE_6_MIN_SOURCES,
        help=f"Phase 6 minimum (default {PHASE_6_MIN_SOURCES})",
    )
    args = parser.parse_args()

    task = load_question(args.db, args.research_id)
    if task is None:
        print(f"unknown research id: {args.research_id}", file=sys.stderr)
        return 3

    print(f"research_id:   {task['research_id']}  (status {task['status']})")
    print(f"question:      {' '.join(task['question'].split())[:150]}...")
    print(f"min sources:   {args.min_sources}")

    try:
        adapter = AgentReachAdapter()
        result = probe(
            adapter,
            task["question"],
            task.get("method_family"),
            min_sources=args.min_sources,
        )
    except AgentReachError as exc:
        print(f"agent-reach unusable: {exc}", file=sys.stderr)
        return 2

    print(f"queries tried: {len(result['queries'])}")
    for query in result["queries"]:
        print(f"  - {' '.join(query.split())[:110]}")
    print(f"unique urls:   {result['unique_urls']}")
    for url in result["urls"]:
        print(f"  - {url}")

    if result["error"]:
        print(f"search reported: {result['error']}")

    if result["unique_urls"] < args.min_sources:
        print(
            f"\nNOT READY: {result['unique_urls']} candidate url(s) reachable, "
            f"Phase 6 requires {args.min_sources}.",
            file=sys.stderr,
        )
        return 4

    print("\nREADY: the available lanes can reach the minimum source count.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

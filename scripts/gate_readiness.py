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

With ``--candidate-list`` it instead checks a pre-registered candidate list
(PROP-004) offline: the list loads, is registered for this question, and names
at least the minimum number of distinct upstream *works*. That is a
pre-registration check only -- it says nothing about relevance, access or
support, which the run itself and human review decide.

    uv run python scripts/gate_readiness.py --research-id RQ-6d9c12f4 \
        --candidate-list brain/00_Inbox/Scout_Candidates/RQ-6d9c12f4.md

Exit codes:
    0  the available lanes (or the list) can reach the minimum
    2  Agent Reach itself is unusable
    3  the research ID is unknown
    4  the lanes answered (or the list loaded), but cannot reach the minimum
    5  the candidate list is invalid or registered for another question
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from quant_brain.config import PROJECT_ROOT
from quant_brain.db.init_db import DEFAULT_DB_PATH, connect
from quant_brain.discovery.agent_reach import (
    AgentReachAdapter,
    AgentReachError,
    plan_queries,
)
from quant_brain.discovery.candidate_list import CandidateListError, load_candidate_list
from quant_brain.discovery.work_identity import upstream_work_key

# brain/_system/plan/phase_06_research_scout_agent.md: a raw research note must
# cite at least three upstream sources. Imported rather than redeclared so this
# probe and the executor that enforces it cannot drift apart -- they were two
# independent literals, and only this one was ever checked.
from quant_brain.research.executor import MIN_UPSTREAM_SOURCES

PHASE_6_MIN_SOURCES = MIN_UPSTREAM_SOURCES


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
    unique = {upstream_work_key(str(hit.get("url") or "")) for hit in hits if hit.get("url")}
    return {
        "queries": queries,
        "unique_urls": len(unique),
        "urls": sorted(unique),
        "error": None,
    }


def check_candidate_list(
    project_root: str | Path,
    list_path: str,
    research_id: str,
) -> dict[str, Any]:
    """Offline pre-registration check. Fetches nothing and calls no model."""
    candidate_list = load_candidate_list(project_root, list_path)
    if candidate_list.research_id != research_id:
        raise CandidateListError(
            f"candidate list is registered for {candidate_list.research_id}, not {research_id}"
        )
    works = sorted({upstream_work_key(url) for url in candidate_list.urls})
    return {
        "path": candidate_list.path,
        "sha256": candidate_list.sha256,
        "listed": len(candidate_list.urls),
        "distinct_works": len(works),
        "works": works,
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
    parser.add_argument("--candidate-list", default=None)
    parser.add_argument("--project-root", default=str(PROJECT_ROOT))
    args = parser.parse_args()

    task = load_question(args.db, args.research_id)
    if task is None:
        print(f"unknown research id: {args.research_id}", file=sys.stderr)
        return 3

    print(f"research_id:   {task['research_id']}  (status {task['status']})")
    print(f"question:      {' '.join(task['question'].split())[:150]}...")
    print(f"min sources:   {args.min_sources}")

    if args.candidate_list:
        try:
            checked = check_candidate_list(
                args.project_root, args.candidate_list, task["research_id"]
            )
        except CandidateListError as exc:
            print(f"invalid candidate list: {exc}", file=sys.stderr)
            return 5
        print(f"candidate list: {checked['path']}")
        print(f"list sha256:    {checked['sha256']}")
        print(f"listed urls:    {checked['listed']}")
        print(f"distinct works: {checked['distinct_works']}")
        for work in checked["works"]:
            print(f"  - {work}")
        if checked["distinct_works"] < args.min_sources:
            print(
                f"\nNOT READY: the list names {checked['distinct_works']} distinct work(s), "
                f"Phase 6 requires {args.min_sources}.",
                file=sys.stderr,
            )
            return 4
        print(
            "\nREGISTERED: the list names enough distinct works. This is not a "
            "relevance, access or support check; the run and human review decide those."
        )
        return 0

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

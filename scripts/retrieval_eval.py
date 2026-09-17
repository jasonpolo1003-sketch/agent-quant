"""Measure retrieval quality against hand-labeled queries.

The fixture queries are deliberately NON-LEXICAL: they avoid sharing rare tokens
with their target note. That is the whole point -- a lexical backend can match on
shared words, so a query that shares vocabulary with its target proves nothing
about semantic retrieval.

KNOWN ISSUE -- `--compare` does not currently work. It evaluates the semantic
backend against the `local-hash-embedding-v1` lexical baseline, but the hash
vectors are no longer in db/brain.sqlite: the Phase 3 re-embed left only
`nomic-embed-text@768`, despite the Phase 3 design note saying to keep the hash
vectors precisely so this script could compare against them. `--compare` now
raises a dimension-mismatch ValueError from search_similar_chunks; before that
error existed it silently reported the baseline as recall 0.00, which is worse.
Restoring it means re-embedding all chunks under HASH_MODEL, which writes to the
database -- deliberately not done here. The single-model run (the one that gates
Phase 3) is unaffected.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quant_brain.config import BRAIN_DIR, PROJECT_ROOT
from quant_brain.db.init_db import DEFAULT_DB_PATH
from quant_brain.indexing.embeddings import DEFAULT_MODEL, HASH_MODEL, search_similar_chunks

# (query, substring that must appear in the winning note path)
FIXTURES: tuple[tuple[str, str], ...] = (
    (
        "can a backtest accidentally use tomorrow's information",
        "look-ahead-bias",
    ),
    (
        "why do only the companies that stayed in business show up in my sample",
        "survivorship-bias",
    ),
    (
        "how is the momentum oscillator actually computed from average gains and losses",
        "relative-strength-index",
    ),
    (
        "python library for quickly sweeping many parameter combinations over price series",
        "vectorbt",
    ),
    (
        "framework for simulating trades with commissions and plotting statistics",
        "backtesting-py",
    ),
    (
        "which asset classes and strategy families is this project willing to study",
        "quant-research-universe",
    ),
    (
        "when should a trade be closed after entering on an oversold signal",
        "DOOR-etf-mean-reversion",
    ),
)

# NOTE: brain/_system/ is excluded from the index by default (markdown_indexer
# exclude_dirs={"_system"}), so pre_backtest_validation_checklist.md and the
# source-quality policy are NOT retrievable. That is why no fixture targets
# them. See PLAN.md for the open decision on indexing _system.


def evaluate(
    db_path: str | Path,
    model: str,
    limit: int = 5,
    fixtures: tuple[tuple[str, str], ...] = FIXTURES,
    dimensions: int | None = None,
) -> dict[str, Any]:
    """Run every fixture query and report Recall@1, Recall@5, and MRR."""
    rows = []
    hits_at_1 = 0
    hits_at_k = 0
    reciprocal_ranks = 0.0

    for query, expected in fixtures:
        results = search_similar_chunks(
            db_path, query, limit=limit, model=model, dimensions=dimensions
        )
        paths = [str(item["note_path"]) for item in results]
        rank = next((i + 1 for i, path in enumerate(paths) if expected in path), None)

        if rank == 1:
            hits_at_1 += 1
        if rank is not None:
            hits_at_k += 1
            reciprocal_ranks += 1.0 / rank

        rows.append(
            {
                "query": query,
                "expected_contains": expected,
                "rank": rank,
                "top_path": paths[0] if paths else None,
                "top_score": round(results[0]["score"], 4) if results else None,
            }
        )

    total = len(fixtures)
    return {
        "model": model,
        "limit": limit,
        "fixture_count": total,
        "recall_at_1": round(hits_at_1 / total, 4),
        f"recall_at_{limit}": round(hits_at_k / total, 4),
        "mrr": round(reciprocal_ranks / total, 4),
        "results": rows,
    }


def _print_report(report: dict[str, Any]) -> None:
    limit = report["limit"]
    print(f"\n=== {report['model']} ===")
    print(
        f"Recall@1: {report['recall_at_1']:.2f}   "
        f"Recall@{limit}: {report[f'recall_at_{limit}']:.2f}   "
        f"MRR: {report['mrr']:.3f}"
    )
    for row in report["results"]:
        mark = "HIT " if row["rank"] else "MISS"
        rank = f"@{row['rank']}" if row["rank"] else "  -"
        print(f"  {mark} {rank}  {row['query'][:58]}")
        if not row["rank"]:
            print(f"          got: {row['top_path']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Evaluate the semantic backend against the lexical hash baseline.",
    )
    parser.add_argument("--save", action="store_true", help="Write the report under brain/00_Inbox.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    models = [args.model, HASH_MODEL] if args.compare else [args.model]
    reports = [evaluate(args.db, model, args.limit) for model in models]

    if args.json:
        print(json.dumps(reports, indent=2))
    else:
        for report in reports:
            _print_report(report)
        if args.compare and len(reports) == 2:
            key = f"recall_at_{args.limit}"
            delta = reports[0][key] - reports[1][key]
            print(f"\nSemantic minus lexical on {key}: {delta:+.2f}")

    if args.save:
        stamp = datetime.now(UTC).strftime("%Y-%m-%d")
        out_dir = Path(BRAIN_DIR) / "00_Inbox" / "Model_Evaluations"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"retrieval-eval-{stamp}.json"
        out_path.write_text(json.dumps(reports, indent=2), encoding="utf-8")
        print(f"\nSaved: {out_path.relative_to(PROJECT_ROOT).as_posix()}")


if __name__ == "__main__":
    main()

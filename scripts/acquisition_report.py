"""Gate C acceptance demonstration: bounded credible source acquisition, offline.

Runs the real acquisition pipeline over a recorded fixture bundle and reports
what it accepted, what it rejected, and why. No network, no database, no model.

The point is to make the Gate C exit condition inspectable rather than inferred:
a deliberately adversarial search result set must yield at least one credible
primary or practitioner candidate, and must reject thin, promotional and
duplicate material before anything reaches Qwen.

Usage:
    uv run python scripts/acquisition_report.py
    uv run python scripts/acquisition_report.py --limit 3
    uv run python scripts/acquisition_report.py --json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from quant_brain.discovery.acquisition import (
    assess_fetched_content,
    dedupe_candidates,
    rank_candidates,
)
from quant_brain.discovery.live_discovery import save_source_snapshot

DEFAULT_QUESTION = "source supported exit rules for RSI mean reversion on ETFs"
DEFAULT_FIXTURES = Path(__file__).resolve().parents[1] / "tests" / "fixtures"


def build_report(fixtures: Path, question: str, limit: int) -> dict:
    """Run the pipeline end to end against recorded fixtures."""
    hits = json.loads(
        (fixtures / "acquisition_search_mixed.json").read_text(encoding="utf-8")
    )["results"]
    bodies = json.loads(
        (fixtures / "acquisition_fetch_bodies.json").read_text(encoding="utf-8")
    )

    deduped = dedupe_candidates(hits)
    accepted, rejected = rank_candidates(deduped, question, limit=limit)

    records: list[dict] = []
    rejected_records = [dict(c.as_record(), stage="ranking") for c in rejected]

    # Snapshot into a scratch directory: this is a demonstration, not a run, and
    # it must not write into the project's real inbox.
    with tempfile.TemporaryDirectory(prefix="gate-c-acquisition-") as tmp:
        root = Path(tmp)
        for candidate in accepted:
            body = bodies.get(candidate.url, "")
            verdict = assess_fetched_content(candidate.url, body, title=candidate.title)
            if verdict is not None:
                rejected_records.append(
                    dict(
                        candidate.as_record(),
                        stage="content-assessment",
                        tier=verdict.tier,
                        reason=verdict.reason,
                        signals=list(verdict.signals),
                    )
                )
                continue

            captured_at = datetime.now(UTC)
            snapshot = save_source_snapshot(
                root,
                url=candidate.url,
                content=body,
                title=candidate.title,
                channel="web",
                backend="fixture",
                captured_at=captured_at,
            )
            records.append(
                dict(
                    candidate.as_record(),
                    accepted=True,
                    snapshot=snapshot,
                    snapshot_exists=(root / snapshot).exists(),
                    content_hash=hashlib.sha256(body.encode("utf-8")).hexdigest(),
                    captured_at=captured_at.isoformat(),
                )
            )

        promotable = [r for r in records if r["tier"] in {"primary", "practitioner"}]
        return {
            "question": question,
            "source_cap": limit,
            "search_hits": len(hits),
            "unique_candidates": len(deduped),
            "accepted": records,
            "rejected": rejected_records,
            "gate_c_checks": {
                "at_least_one_credible_candidate": bool(promotable),
                "within_source_cap": len(records) <= limit,
                "every_accepted_source_has_a_snapshot": all(
                    r["snapshot_exists"] for r in records
                ),
                # Rejection must happen before extraction wherever it happens.
                # A narrowed cap can legitimately filter everything at ranking,
                # so requiring a content-assessment rejection specifically would
                # fail a healthy pipeline at --limit 1.
                "thin_or_promotional_rejected_before_extraction": any(
                    r["tier"] == "reject" for r in rejected_records
                ),
                "duplicates_collapsed": len(deduped) < len(hits),
                "promotable_tiers_found": sorted({r["tier"] for r in promotable}),
            },
        }


def _print_human(report: dict) -> None:
    checks = report["gate_c_checks"]
    print(f"Question: {report['question']}")
    print(
        f"{report['search_hits']} search hits -> {report['unique_candidates']} unique "
        f"-> {len(report['accepted'])} accepted (cap {report['source_cap']})\n"
    )

    print("ACCEPTED (snapshotted, would proceed to Qwen)")
    for record in report["accepted"]:
        print(f"  [{record['tier']:<12}] score {record['score']:5.2f}  {record['url']}")
        print(f"      {record['reason']}")
        print(f"      snapshot: {record['snapshot']}")
        print(f"      sha256:   {record['content_hash'][:16]}...  captured {record['captured_at']}")

    print("\nREJECTED (never reaches the model)")
    for record in report["rejected"]:
        print(f"  [{record['tier']:<12}] {record['url']}  ({record['stage']})")
        print(f"      {record['reason']}")

    print("\nGATE C CHECKS")
    for name, value in checks.items():
        if isinstance(value, bool):
            print(f"  {'PASS' if value else 'FAIL'}  {name}")
        else:
            print(f"        {name}: {value}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURES)
    parser.add_argument("--question", default=DEFAULT_QUESTION)
    parser.add_argument("--limit", type=int, default=5, help="source cap (max 5)")
    parser.add_argument("--json", action="store_true", help="emit the raw report")
    args = parser.parse_args()

    if args.limit > 5:
        parser.error("the source cap is 5; callers may narrow it, never widen it")

    report = build_report(args.fixtures, args.question, args.limit)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        _print_human(report)

    failed = [k for k, v in report["gate_c_checks"].items() if isinstance(v, bool) and not v]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

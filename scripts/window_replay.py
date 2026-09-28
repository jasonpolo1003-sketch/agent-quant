"""Replay the windows of a preserved failed run through live local Qwen.

Fresh model inference, not saved-response validation: it rebuilds each window
of the run's windowed source from the committed snapshot (checking the run's
recorded offsets and hashes first), then runs the real ladder under the
*current* window contract and validators. It dispatches nothing and writes
nothing -- no database rows, no events, no notes, no diagnostics files -- so it
is not a production run and cannot produce research. Not run by pytest.

    uv run python scripts/window_replay.py RUN-d67b1d121b
    uv run python scripts/window_replay.py RUN-d67b1d121b --windows S4-W02,S4-W03

Exit 0 only if every replayed window validated. Ollama is not byte-stable even
at temperature 0, so one replay is a sample, not a guarantee.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys

from quant_brain.config import PROJECT_ROOT
from quant_brain.db.init_db import DEFAULT_DB_PATH
from quant_brain.llm.qwen_call import QwenValidationError, qwen_call
from quant_brain.research.receipts import resolve_recorded_snapshot
from quant_brain.research.windowing import (
    WindowOutcome,
    plan_windows,
    validate_window_outcome,
    window_prompt,
)


def _receipt(run_id: str) -> dict:
    body = (PROJECT_ROOT / "brain" / "00_Inbox" / "Failed_Runs" / f"{run_id}.md").read_text(
        encoding="utf-8"
    )
    return json.loads(body.split("```json")[1].split("```")[0])


def _question(research_id: str) -> str:
    with sqlite3.connect(f"file:{DEFAULT_DB_PATH}?mode=ro", uri=True) as conn:
        row = conn.execute(
            "SELECT question FROM research_questions WHERE research_id = ?", (research_id,)
        ).fetchone()
    if row is None:
        raise SystemExit(f"unknown research question {research_id}")
    return str(row[0])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run_id")
    parser.add_argument("--windows", help="comma-separated window IDs (default: all)")
    args = parser.parse_args()

    receipt = _receipt(args.run_id)
    research_id = receipt["research_id"]
    task = {"research_id": research_id, "question": _question(research_id)}
    wanted = set(args.windows.split(",")) if args.windows else None
    ok = True
    for manifest in receipt.get("extraction_windows") or []:
        # Follows the reconciliation ledger if the run's snapshot bytes moved.
        snapshot = resolve_recorded_snapshot(PROJECT_ROOT, args.run_id, manifest["snapshot_path"])
        if hashlib.sha256(snapshot.read_bytes()).hexdigest() != manifest["snapshot_sha256"]:
            raise SystemExit(f"{snapshot} no longer matches the run's recorded sha256")
        candidate = next(
            c for c in receipt["accepted_candidates"] if c["url"] == manifest["url_or_citation"]
        )
        item = {
            "source_id": manifest["source_id"],
            "title": candidate["title"],
            "url_or_citation": candidate["url"],
            "source_quality": candidate["tier"],
            "snapshot_text": snapshot.read_text(encoding="utf-8"),
        }
        windows = plan_windows(item["snapshot_text"], item["source_id"])
        recorded = [(w["window_id"], w["start"], w["end"], w["text_sha256"]) for w in manifest["windows"]]
        if [(w.window_id, w.start, w.end, w.text_sha256) for w in windows] != recorded:
            raise SystemExit("planned windows differ from the run's recorded windows")
        print(f"{item['source_id']} {item['url_or_citation']}: {len(windows)} windows, "
              f"run outcomes {[w['outcome'] for w in manifest['windows']]}")
        for window in windows:
            if wanted and window.window_id not in wanted:
                continue
            try:
                result = qwen_call(
                    window_prompt(task, item, window),
                    [item],
                    expected_research_id=research_id,
                    validator=lambda parsed, w=window: validate_window_outcome(
                        parsed, item, w, expected_research_id=research_id
                    ),
                    output_schema=WindowOutcome.model_json_schema(),
                )
            except QwenValidationError as exc:
                ok = False
                print(f"[{window.window_id}] FAILED after {len(exc.attempts)} attempts")
                for attempt in exc.attempts:
                    print(f"    {attempt.model} {attempt.duration_seconds:.1f}s "
                          f"{list(attempt.validator_reasons)[:3]}")
                continue
            source = result.output.get("source") or {}
            print(f"[{window.window_id}] {result.output['outcome']} via {result.model_used}, "
                  f"durations {[round(a.duration_seconds, 1) for a in result.attempts]}")
            for attempt in result.attempts[:-1]:
                print(f"    failed first: {attempt.model} {list(attempt.validator_reasons)[:3]}")
            if source:
                print(f"    evidence {source.get('evidence')!a}")
                print(f"    confidence {source.get('confidence')}, "
                      f"mvp_testable {source.get('mvp_testable')}")
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

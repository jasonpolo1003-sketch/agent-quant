"""Run a frozen strategy card's backtest in two gated phases.

    uv run python scripts/run_backtest.py SC-0002 --phase in-sample
    uv run python scripts/run_backtest.py SC-0002 --approve-in-sample --by Jason
    uv run python scripts/run_backtest.py SC-0002 --phase held-out      # once, ever

The held-out phase refuses to run without a recorded in-sample approval and a
matching second-implementation cross-check, and refuses to run a second time.
A backtest is not proof of future profit.
"""

from __future__ import annotations

import argparse
import sys

from quant_brain.backtest import run as rn
from quant_brain.config import PROJECT_ROOT
from quant_brain.db.init_db import DEFAULT_DB_PATH


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("card_id")
    parser.add_argument("--phase", choices=["in-sample", "held-out"])
    parser.add_argument("--approve-in-sample", action="store_true")
    parser.add_argument("--by")
    args = parser.parse_args()
    try:
        if args.approve_in_sample:
            if not args.by:
                parser.error("--approve-in-sample needs --by <name>")
            rn.approve_in_sample(PROJECT_ROOT, args.card_id, by=args.by)
            print(f"in-sample results of {args.card_id} approved by {args.by}")
        elif args.phase == "in-sample":
            outcome = rn.run_in_sample(PROJECT_ROOT, DEFAULT_DB_PATH, args.card_id)
            print(f"in-sample done; cross-check {'match' if outcome['reference_match'] else 'MISMATCH'}; "
                  f"report: {rn.REPORT_DIR}/{args.card_id}-in-sample.md")
        elif args.phase == "held-out":
            outcome = rn.run_held_out(PROJECT_ROOT, DEFAULT_DB_PATH, args.card_id)
            print(f"held-out verdict: {outcome['verdict']['verdict']}; "
                  f"report: {rn.REPORT_DIR}/{args.card_id}-held-out.md")
        else:
            parser.error("choose --phase or --approve-in-sample")
    except rn.RunnerError as exc:
        print(f"REFUSED: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

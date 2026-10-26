"""Run SC-FUT-0001 behind its gates (see src/quant_brain/futures/runner.py).

    uv run python scripts/run_sc_fut_0001.py status --data-dir <dir>
    uv run python scripts/run_sc_fut_0001.py authorize development_authorized --by Jason
    uv run python scripts/run_sc_fut_0001.py run --phase development \
        --data-dir C:/Users/jason/OneDrive/Desktop/Quant/data/databento/dev_2019-05-01_2024-12-31

`authorize` records Jason's explicit decision; agents run it only when Jason
has said so in the conversation. The held-out phase reads the raw download
once and is refused on any later attempt.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from quant_brain.config import PROJECT_ROOT
from quant_brain.futures import runner
from quant_brain.futures.bars import load_days


def make_loader(phase: str, data_dir: Path) -> runner.Loader:
    bars = data_dir / (runner.DEV_BARS if phase == "development" else runner.RAW_BARS)

    def load(root: str, start: date, end: date):
        return load_days(
            bars,
            PROJECT_ROOT / runner.ROLL_CSV,
            PROJECT_ROOT / runner.CALENDAR,
            root=root,
            start=start,
            end=end,
        )

    return load


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)
    status = sub.add_parser("status")
    status.add_argument("--data-dir", type=Path, required=True)
    auth = sub.add_parser("authorize")
    auth.add_argument("event")
    auth.add_argument("--by", required=True)
    go = sub.add_parser("run")
    go.add_argument("--phase", choices=["development", "held_out"], required=True)
    go.add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args()

    if args.command == "status":
        for phase in ("development", "held_out"):
            problems = runner.gate_problems(PROJECT_ROOT, phase, args.data_dir)
            print(f"{phase}: {'READY' if not problems else 'BLOCKED'}")
            for problem in problems:
                print(f"  - {problem}")
        return 0
    if args.command == "authorize":
        print(json.dumps(runner.authorize(PROJECT_ROOT, args.event, args.by)))
        return 0
    try:
        event = runner.run(
            PROJECT_ROOT, args.phase, args.data_dir, make_loader(args.phase, args.data_dir)
        )
    except runner.GateError as exc:
        print(f"REFUSED  {exc}")
        return 1
    print(json.dumps({k: event[k] for k in ("event", "primary", "outcome", "power")}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

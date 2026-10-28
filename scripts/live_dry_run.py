"""Dry run of the SC-FUT-0005 live runner on one historical practice day (FakeBroker only).

Loads MNQ practice days (volume roll) the way the workbench does, builds the sigma table from
the sessions before --date, replays the day bar by bar through Runner + FakeBroker with each
bar delivered --latency seconds after it closes, prints the JSONL journal and compares the
broker's round trips with NoiseArea().simulate for that day. No network, no credentials.

Usage: .venv/Scripts/python.exe scripts/live_dry_run.py --date 2024-03-15 [--latency 0.5]
       [--contracts 1] [--loss-stop 500] [--journal out.jsonl] [--kill-file STOP]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from quant_brain.config import PROJECT_ROOT
from quant_brain.live.broker import FakeBroker
from quant_brain.live.engine import SigmaHistory, bars_of, context_of
from quant_brain.live.runner import RiskConfig, Runner
from quant_brain.workbench.noise import NoiseArea


def _workbench():
    spec = importlib.util.spec_from_file_location("wb", PROJECT_ROOT / "scripts" / "workbench.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--date", type=date.fromisoformat, required=True)
    parser.add_argument("--latency", type=float, default=0.5, help="seconds after each bar closes")
    parser.add_argument("--contracts", type=int, default=1)
    parser.add_argument("--max-position", type=int, default=2)
    parser.add_argument("--loss-stop", type=float, default=500.0, help="daily loss stop, dollars")
    parser.add_argument("--journal", type=Path)
    parser.add_argument("--kill-file", type=Path)
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

    wb = _workbench()
    start = max(date(2019, 5, 1), args.date - timedelta(days=45))
    days = wb.dev_loader(wb.DEV_DIR)("MNQ", start, args.date, "volume_roll_date")
    if not days or days[-1].trade_date != args.date:
        raise SystemExit(f"{args.date} is not a practice session")
    history = SigmaHistory("MNQ")
    for d in days[:-1]:
        history.add_session(d.bars)
    day, sigma = days[-1], history.sigma()

    risk = RiskConfig(
        contracts=args.contracts,
        max_position=args.max_position,
        daily_loss_stop_cents=round(args.loss_stop * 100),
        kill_file=args.kill_file,
    )
    broker = FakeBroker("MNQ")
    t0 = datetime.combine(day.trade_date, datetime.min.time()) + timedelta(hours=8)
    runner = Runner(context_of(day, sigma), broker, risk, args.journal, now=t0)
    for bar in bars_of(day):
        end = datetime.combine(day.trade_date, bar.minute) + timedelta(minutes=1)
        runner.on_bar(bar, end + timedelta(seconds=args.latency))
    runner.end_session(datetime.combine(day.trade_date, datetime.min.time()) + timedelta(hours=16))
    runner.close()

    for rec in runner.records:
        if rec["kind"] == "signal" and rec["order"] is None:
            continue  # quiet checks: no order
        print(json.dumps(rec, sort_keys=True))
    batch = NoiseArea().simulate(NoiseArea().prepare_all(days)[-1])
    want = [
        (x.side, x.entry_minute, x.entry_ticks, x.exit_minute, x.exit_ticks) for x in batch.trades
    ]
    got = [
        (r.side, r.entry_at.time(), r.entry, r.exit_at.time(), r.exit) for r in broker.round_trips
    ]
    print(
        f"\n{day.trade_date}: {len(got)} broker round trips, workbench {len(want)} trades; "
        f"{'MATCH' if got == want else 'DIFFER'} (contracts=1 compares one for one)"
    )
    print(
        f"day P&L (gross, at last close): ${broker.day_pnl_cents(bars_of(day)[-1].close) / 100:.2f}"
        f"; workbench net after L3 costs: ${batch.net_cents / 100:.2f}; halted: {runner.halted}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

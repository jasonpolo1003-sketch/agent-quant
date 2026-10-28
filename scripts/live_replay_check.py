"""Replay equivalence for the SC-FUT-0005 live engine (plan workstream E2; the key proof).

Every practice day 2019-05-01..2024-12-31 for MNQ (volume roll), built exactly as the
workbench builds them (scripts/workbench.py dev_loader), goes through:
  A. the batch rule: NoiseArea().prepare_all + simulate;
  B. the live engine: SigmaHistory fed session by session (its sigma table must equal
     prepare_all's), then NoiseEngine fed one closed bar at a time;
  C. the runner + FakeBroker, orders sent 0.5 s after each check, risk switches off.
A must equal B on every day: full Trade objects (side, entry minute and price, exit minute and
price, reason, cents) and the day status. C's round trips must equal B's legs wherever the
model fills (a Void day, where a check-minute bar is missing, is reported separately).
Reads licensed data from ../data/databento, so it is a script, not a unit test.

Usage: .venv/Scripts/python.exe scripts/live_replay_check.py [--start 2019-05-01] [--end 2024-12-31]
"""

from __future__ import annotations

import argparse
import importlib.util
import logging
import sys
from datetime import date, datetime, timedelta

from quant_brain.config import PROJECT_ROOT
from quant_brain.live.broker import FakeBroker
from quant_brain.live.engine import SigmaHistory, bars_of, context_of, replay
from quant_brain.live.runner import RiskConfig, Runner
from quant_brain.workbench.noise import NoiseArea

OFF = RiskConfig(max_position=1, daily_loss_stop_cents=10**12, stale_seconds=1e9, kill_file=None)


def _workbench():
    spec = importlib.util.spec_from_file_location("wb", PROJECT_ROOT / "scripts" / "workbench.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def legs(trades):
    return [(x.side, x.entry_minute, x.entry_ticks, x.exit_minute, x.exit_ticks) for x in trades]


def broker_replay(day, sigma):
    broker = FakeBroker(day.root)
    runner = Runner(
        context_of(day, sigma),
        broker,
        OFF,
        now=datetime.combine(day.trade_date, datetime.min.time()),
    )
    for bar in bars_of(day):
        end = datetime.combine(day.trade_date, bar.minute) + timedelta(minutes=1)
        runner.on_bar(bar, end + timedelta(seconds=0.5))
    runner.end_session()
    trips = [
        (r.side, r.entry_at.time(), r.entry, r.exit_at.time(), r.exit) for r in broker.round_trips
    ]
    voids = sum(r["kind"] == "void" for r in runner.records)
    late = (
        max((r["seconds_after_check"] or 0) for r in runner.records if r["kind"] == "order")
        if broker.orders
        else 0
    )
    return runner.engine, trips, voids, late


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--start", type=date.fromisoformat, default=date(2019, 5, 1))
    parser.add_argument("--end", type=date.fromisoformat, default=date(2024, 12, 31))
    args = parser.parse_args()

    logging.getLogger("quant_brain.live.runner").setLevel(logging.ERROR)  # warning once per day
    wb = _workbench()
    days = wb.dev_loader(wb.DEV_DIR)("MNQ", args.start, args.end, "volume_roll_date")
    strat = NoiseArea()
    prepared = strat.prepare_all(days)
    history = SigmaHistory("MNQ")
    n = sigma_ok = match = traded = trades = 0
    broker_ok = broker_days = void_days = 0
    max_delay = 0.0
    bad: list[str] = []
    for raw, prep in zip(days, prepared, strict=True):
        n += 1
        sigma = history.sigma()
        sigma_ok += sigma == prep.context["sigma"]
        batch = strat.simulate(prep)
        live = replay(raw, sigma)
        want_status = "no_trade" if batch.status == "ineligible" else batch.status
        same = live.trades() == batch.trades and live.status == want_status
        match += same
        traded += bool(batch.trades)
        trades += len(batch.trades)
        if not same:
            bad.append(
                f"{raw.trade_date} engine {live.status} {legs(live.trades())} vs batch {batch.status} {legs(batch.trades)}"
            )
        eng, trips, voids, late = broker_replay(raw, sigma)
        max_delay = max(max_delay, late)
        model = [(x.side, x.entry_at, x.entry, x.exit_at, x.exit) for x in eng.legs]
        if voids:
            void_days += 1
        elif eng.status != "non_evaluable":
            broker_days += 1
            if trips == model:
                broker_ok += 1
            else:
                bad.append(f"{raw.trade_date} broker {trips} vs model {model}")
        history.add_session(raw.bars)

    print(f"days {n}  ({days[0].trade_date}..{days[-1].trade_date})")
    print(f"sigma tables equal prepare_all: {sigma_ok}/{n}")
    print(
        f"engine == NoiseArea.simulate (trades + status): {match}/{n}  [{traded} traded days, {trades} trades]"
    )
    print(
        f"runner+FakeBroker round trips == engine legs: {broker_ok}/{broker_days} evaluable days without voids"
    )
    print(f"days with a voided check (missing check-minute bar): {void_days}")
    print(f"max order delay after check in replay: {max_delay:.1f} s")
    for line in bad[:30]:
        print("MISMATCH", line)
    return 0 if match == n and sigma_ok == n and broker_ok == broker_days else 1


if __name__ == "__main__":
    sys.exit(main())

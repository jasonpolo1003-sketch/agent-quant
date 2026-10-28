"""Exam proctor runner (W8).

    # 1. prove the full-file loader rebuilds the practice run exactly (no exam days read out)
    .venv/Scripts/python.exe scripts/proctor_check.py validate
    # 2. spend one exam check (needs Jason's approval); prints only PASS or FAIL
    .venv/Scripts/python.exe scripts/proctor_check.py ask brain/_system/proctor/q1-sc-fut-0005.json \
        --approved-by "Jason 2026-10-28 ..."
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import numpy as np

from quant_brain.config import PROJECT_ROOT
from quant_brain.futures import runner
from quant_brain.futures.bars import read_calendar, read_tick_bars
from quant_brain.futures.session_audit import read_mappings
from quant_brain.workbench import engine, proctor

RC_DIR = PROJECT_ROOT.parent / "data" / "databento" / "rc_2026-10-22"
RC_BARS = "glbx-mdp3_ohlcv-1m_MES-MNQ-FUT_20190501-20261022.dbn.zst"
VOLUME_ROLLS = "brain/sources/mes_mnq/contracts/roll_volume_check.csv"
PRACTICE_RUN = "266777ef"


def full_loader(data_dir: Path = RC_DIR) -> engine.Loader:
    sums = dict(
        reversed(line.split(maxsplit=1))
        for line in (data_dir / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
        if line.strip()
    )
    bars = data_dir / RC_BARS
    expected = sums.get(RC_BARS, "").strip()
    if not expected or runner.sha256(bars) != expected:
        raise SystemExit("full minute-bar file does not match SHA256SUMS")
    mappings = read_mappings(bars)
    outrights = {iid for intervals in mappings.values() for *_, iid in intervals}
    frame = read_tick_bars(bars, outrights)
    calendar = read_calendar(PROJECT_ROOT / runner.CALENDAR)

    def load(market: str, start: date, end: date, roll_column: str):
        from quant_brain.futures.bars import build_days

        rolls = PROJECT_ROOT / (
            VOLUME_ROLLS if roll_column == "volume_roll_date" else runner.ROLL_CSV
        )
        return list(
            build_days(
                frame,
                mappings,
                rolls,
                calendar,
                root=market,
                start=start,
                end=end,
                roll_column=roll_column,
            )
        )

    return load


def validate() -> int:
    trial = next(
        e for e in engine.read_ledger(PROJECT_ROOT) if e["fingerprint"].startswith(PRACTICE_RUN)
    )
    cached = engine.DayTable.load(PROJECT_ROOT / engine.CACHE / f"{trial['fingerprint']}.npz")
    load = full_loader()
    start, end = engine.PRACTICE
    days = load(trial["market"], start, end, engine.ROLLS[trial["roll"]])
    if any(d.trade_date > end for d in days):
        raise SystemExit("loader returned exam days during validation; refusing")
    table = engine.simulate(proctor.build(trial["family"], trial["settings"]), days)
    same = (
        np.array_equal(table.dates, cached.dates)
        and np.array_equal(table.orb_gross, cached.orb_gross)
        and np.array_equal(table.orb_trades, cached.orb_trades)
        and np.array_equal(table.ctrl_gross, cached.ctrl_gross)
        and np.array_equal(table.status, cached.status)
    )
    print(
        f"practice rebuild from the full file: {len(table.dates)} days, "
        f"{'IDENTICAL' if same else 'DIFFERENT'} to workbench trial {PRACTICE_RUN}"
    )
    return 0 if same else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate")
    ask = sub.add_parser("ask")
    ask.add_argument("question", type=Path)
    ask.add_argument("--approved-by", required=True)
    args = parser.parse_args()
    if args.cmd == "validate":
        return validate()
    q = args.question if args.question.is_absolute() else PROJECT_ROOT / args.question
    passed = proctor.check(PROJECT_ROOT, q, full_loader(), approved_by=args.approved_by)
    used = len(proctor.checks_used(PROJECT_ROOT))
    print(f"{'PASS' if passed else 'FAIL'}  (exam checks used: {used} of {proctor.BUDGET})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

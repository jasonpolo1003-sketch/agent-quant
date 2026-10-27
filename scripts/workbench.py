"""Backtest workbench CLI: run a strategy on practice data under every condition.

    uv run python scripts/workbench.py run --family orb --market MNQ
    uv run python scripts/workbench.py run --family orb --settings "{\"range_bars\": 30}" --market MES --roll volume
    uv run python scripts/workbench.py list

Practice data only (2019-05-01..2024-12-31 dev partition, hash-checked). Each
distinct run counts as one trial and tightens its family's pass bar.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from quant_brain.config import PROJECT_ROOT
from quant_brain.futures import runner
from quant_brain.futures.bars import read_calendar, read_tick_bars
from quant_brain.futures.session_audit import read_mappings
from quant_brain.workbench import analysis, engine
from quant_brain.workbench.strategies import make

DEV_DIR = Path("C:/Users/jason/OneDrive/Desktop/Quant/data/databento/dev_2019-05-01_2024-12-31")
RESULTS = f"{engine.WORKBENCH}/results"
VOLUME_ROLLS = "brain/sources/mes_mnq/contracts/roll_volume_check.csv"


def dev_loader(data_dir: Path) -> engine.Loader:
    manifest = data_dir / "manifest.json"
    listed = json.loads(manifest.read_text(encoding="utf-8"))["ohlcv"]
    expected = next(r["output_sha256"] for r in listed if r["output"] == runner.DEV_BARS)
    bars = data_dir / runner.DEV_BARS
    if runner.sha256(bars) != expected:
        raise SystemExit("dev minute-bar file does not match its manifest")
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)
    go = sub.add_parser("run")
    go.add_argument("--family", default="orb")
    go.add_argument("--settings", default="{}")
    go.add_argument("--market", choices=engine.MARKETS, default="MNQ")
    go.add_argument("--roll", choices=list(engine.ROLLS), default="fixed")
    go.add_argument("--data-dir", type=Path, default=DEV_DIR)
    sub.add_parser("list")
    args = parser.parse_args()

    if args.command == "list":
        for e in engine.read_ledger(PROJECT_ROOT):
            print(
                f"{e['at'][:16]}  {e['family']} {json.dumps(e['settings'])} {e['market']} {e['roll']}  {e['fingerprint'][:10]}"
            )
        for family in sorted({e["family"] for e in engine.read_ledger(PROJECT_ROOT)}):
            bar = analysis.honesty(PROJECT_ROOT, family)
            print(f"{family}: {bar['trials']} trials -> pass bar p < {bar['alpha']:.4f}")
        return 0

    strategy = make(args.family, json.loads(args.settings))
    table, record, cached = engine.run(
        PROJECT_ROOT, strategy, args.market, args.roll, dev_loader(args.data_dir)
    )
    result = analysis.summary(PROJECT_ROOT, table, record)
    out = PROJECT_ROOT / RESULTS / f"{record['fingerprint']}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, default=float) + "\n", encoding="utf-8")
    v = result["verdict"]
    print(
        f"{'cached' if cached else 'new trial'}: {args.family} {json.dumps(strategy.settings())} {args.market} {args.roll}"
    )
    print(
        f"verdict {v['outcome']}: {v.get('per_day', 0):.2f} $/day, vs random {v.get('vs_random_per_day', 0):.2f}, "
        f"p {v.get('p_value', 1):.3f} (bar {v['alpha']:.4f}); {'; '.join(v['reasons'])}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

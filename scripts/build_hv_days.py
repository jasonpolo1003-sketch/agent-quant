"""Build the SC-FUT-0006 high-volatility day list from NQ daily bars (outcome-blind).

Reads only the 2010-2024 daily bars and the session calendar; no strategy result is
computed. Writes brain/_system/futures/sc-fut-0006-hv-days.csv and prints its sha256.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
from datetime import UTC, date, datetime
from pathlib import Path

import databento_dbn
import zstandard

from quant_brain.config import PROJECT_ROOT
from quant_brain.workbench.volfilter import front_returns, high_vol_days, vol_series

DAILY = PROJECT_ROOT.parent / "data/databento/daily_2010-06-06_2024-12-31"
FILE = "glbx-mdp3_ohlcv-1d_equity_indexes_20100606-20241231.dbn.zst"
CALENDAR = PROJECT_ROOT / "brain/_system/futures/session-calendar.v1.csv"
OUT = PROJECT_ROOT / "brain/_system/futures/sc-fut-0006-hv-days.csv"
PRACTICE = (date(2019, 5, 1), date(2024, 12, 31))


def nq_rows(path: Path) -> list[tuple[date, str, float, int]]:
    with path.open("rb") as handle:
        raw = zstandard.ZstdDecompressor().stream_reader(handle).read()
    decoder = databento_dbn.DBNDecoder()
    decoder.write(raw)
    records = decoder.decode()
    symbols = {
        int(interval["symbol"]): raw_symbol
        for raw_symbol, intervals in records[0].mappings.items()
        if raw_symbol.startswith("NQ") and "-" not in raw_symbol and len(raw_symbol) == 4
        for interval in intervals
    }
    rows = []
    for r in records[1:]:
        contract = symbols.get(getattr(r, "instrument_id", None))
        if contract is None or not hasattr(r, "volume"):
            continue
        day = datetime.fromtimestamp(r.ts_event / 1e9, tz=UTC).date()
        rows.append((day, contract, r.close / 1e9, int(r.volume)))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--daily-dir", type=Path, default=DAILY)
    args = parser.parse_args()
    with CALENDAR.open(encoding="utf-8") as handle:
        sessions = [
            d
            for d in (date.fromisoformat(r["trade_date"]) for r in csv.DictReader(handle))
            if PRACTICE[0] <= d <= PRACTICE[1]
        ]
    vols = vol_series(front_returns(nq_rows(args.daily_dir / FILE)))
    rows = high_vol_days(sessions, vols)
    with OUT.open("w", encoding="utf-8", newline="\n") as handle:
        out = csv.writer(handle, lineterminator="\n")
        out.writerow(["trade_date", "bar_date_used", "vol20", "median252", "high_vol"])
        for trade_date, used, vol, median, high in rows:
            out.writerow(
                [
                    trade_date,
                    used or "",
                    "" if vol is None else f"{vol:.8f}",
                    "" if median is None else f"{median:.8f}",
                    high,
                ]
            )
    high = sum(r[4] for r in rows)
    print(f"{len(rows)} sessions, {high} high-volatility ({high / len(rows):.1%})")
    print("sha256", hashlib.sha256(OUT.read_bytes()).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

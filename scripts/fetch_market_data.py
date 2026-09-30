"""Download daily bars and store each download as a new, verified dataset (Gate F).

The only code that uses the network. Yahoo via yfinance (auto_adjust=False,
actions=True), with a report-only Stooq cross-check. Each symbol becomes a new
immutable dataset: Parquet under data/parquet/ (gitignored), a manifest under
data/manifests/ (committed) and a price_datasets row, written in that order.

    uv run python scripts/fetch_market_data.py --symbols SPY QQQ IWM --start 2000-01-01
    uv run python scripts/fetch_market_data.py --universe starter --start 2000-01-01 --no-cross-check
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date

import pandas as pd

from quant_brain.config import PROJECT_ROOT
from quant_brain.data.market_data import MarketDataError, ingest
from quant_brain.db.init_db import DEFAULT_DB_PATH


def yahoo_bars(symbol: str, start: str, end: str) -> pd.DataFrame:
    import yfinance

    frame = yfinance.Ticker(symbol).history(
        start=start, end=end, interval="1d", auto_adjust=False, actions=True
    )
    if frame.empty:
        raise MarketDataError(f"{symbol}: Yahoo returned no rows")
    return frame


def stooq_close(symbol: str, start: str, end: str) -> pd.Series:
    from pandas_datareader import data as web

    return web.DataReader(f"{symbol}.US", "stooq", start, end)["Close"]


stooq_close.source = "stooq via pandas-datareader (Close)"  # type: ignore[attr-defined]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--symbols", nargs="+")
    group.add_argument("--universe", help="a list in data/universe/<name>.json (PROP-010)")
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", default=date.today().isoformat())
    parser.add_argument("--no-cross-check", action="store_true",
                        help="skip the report-only Stooq comparison (blocked since Gate F)")
    args = parser.parse_args()
    symbols = args.symbols or [
        entry["symbol"] for entry in json.loads(
            (PROJECT_ROOT / "data/universe" / f"{args.universe}.json").read_text(encoding="utf-8")
        )["symbols"]
    ]

    import yfinance

    failed = False
    for symbol in symbols:
        try:
            manifest = ingest(
                PROJECT_ROOT, DEFAULT_DB_PATH, symbol, yahoo_bars(symbol, args.start, args.end),
                meta={"provider": "yfinance", "provider_version": yfinance.__version__,
                      "requested_start": args.start, "requested_end": args.end},
                cross_check_fetcher=None if args.no_cross_check else stooq_close,
            )
        except Exception as exc:  # one symbol failing does not stop the others
            failed = True
            print(f"FAIL  {symbol}: {type(exc).__name__}: {exc}")
            continue
        check = manifest["cross_check"]
        agreement = (
            f"corr {check['return_correlation']:.5f}, max diff {check['max_abs_return_diff']:.5f} "
            f"over {check['overlap_days']} days" if check["status"] == "compared"
            else f"{check['status']} ({check.get('reason', '')})"
        )
        print(f"OK    {manifest['dataset_id']}: {manifest['rows']} rows "
              f"{manifest['first_date']}..{manifest['last_date']}; "
              f"{len(manifest['warnings'])} warnings; cross-check {agreement}")
        for warning in manifest["warnings"]:
            print(f"      warning: {warning}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

from __future__ import annotations

import argparse
import json

from quant_brain.data.price_data import download_and_cache_symbols


def main() -> None:
    parser = argparse.ArgumentParser(description="Download daily price data with yfinance.")
    parser.add_argument("--symbols", nargs="+", default=["SPY", "QQQ", "IWM"])
    parser.add_argument("--start", default="2010-01-01")
    parser.add_argument("--end", default=None)
    parser.add_argument("--interval", default="1d")
    args = parser.parse_args()

    results = download_and_cache_symbols(
        symbols=args.symbols,
        start=args.start,
        end=args.end,
        interval=args.interval,
    )
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()

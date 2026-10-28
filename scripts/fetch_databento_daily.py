"""Download Databento CME daily bars (ohlcv-1d) for the multi-market practice set.

Approved by Jason 2026-10-27: daily bars only, 2010-06-06..2024-12-31, quoted
$39.44 and paid from Databento free credits. Refuses any end date after
2025-01-01 (the exam period stays unbought and unread) and any existing output.

    uv run python scripts/fetch_databento_daily.py --out C:/Users/jason/OneDrive/Desktop/Quant/data/databento/daily_2010-06-06_2024-12-31
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import UTC, date, datetime
from pathlib import Path

import requests

from quant_brain.config import PROJECT_ROOT

API = "https://hist.databento.com/v0"
DATASET = "GLBX.MDP3"
START, END = "2010-06-06", "2025-01-01"  # end exclusive
LOCKED_FROM = date(2025, 1, 1)
GROUPS = {
    "equity_indexes": "ES NQ RTY YM",
    "us_treasuries": "ZT ZF ZN ZB",
    "currencies": "6E 6J 6B 6A 6C 6S",
    "metals": "GC SI HG",
    "energy": "CL NG RB HO",
    "grains_oilseeds": "ZC ZW ZS ZL ZM",
    "livestock": "LE HE",
}
APPROVED_MAX_USD = 40.00


def api_key() -> str:
    for line in (PROJECT_ROOT / ".env").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*DATABENTO_API_KEY\s*=\s*['\"]?([^'\"\s]+)", line)
        if m:
            return m.group(1)
    raise SystemExit("DATABENTO_API_KEY missing from .env")


def params(symbols: str) -> dict[str, str]:
    return {
        "dataset": DATASET,
        "symbols": ",".join(f"{s}.FUT" for s in symbols.split()),
        "stype_in": "parent",
        "schema": "ohlcv-1d",
        "start": START,
        "end": END,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if date.fromisoformat(END) > LOCKED_FROM:
        raise SystemExit("refusing: end date reaches the locked exam period")
    if args.out.exists():
        raise SystemExit(f"refusing to overwrite {args.out}")
    key = api_key()
    session = requests.Session()
    session.auth = (key, "")

    def meta(endpoint: str, symbols: str):
        r = session.get(f"{API}/metadata.{endpoint}", params=params(symbols), timeout=60)
        r.raise_for_status()
        return r.json()

    quotes = {g: float(meta("get_cost", s)) for g, s in GROUPS.items()}
    total = sum(quotes.values())
    print(f"re-quoted total ${total:.2f}")
    if total > APPROVED_MAX_USD:
        raise SystemExit(
            f"quote ${total:.2f} exceeds the approved ${APPROVED_MAX_USD:.2f}; nothing downloaded"
        )

    args.out.mkdir(parents=True)
    files = []
    for group, symbols in GROUPS.items():
        expected = int(meta("get_record_count", symbols))
        path = args.out / f"glbx-mdp3_ohlcv-1d_{group}_20100606-20241231.dbn.zst"
        with session.get(
            f"{API}/timeseries.get_range",
            params=params(symbols) | {"encoding": "dbn", "compression": "zstd"},
            stream=True,
            timeout=600,
        ) as r:
            r.raise_for_status()
            with path.open("wb") as handle:
                for chunk in r.iter_content(1 << 20):
                    handle.write(chunk)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        files.append(
            {
                "group": group,
                "symbols": symbols.split(),
                "file": path.name,
                "sha256": digest,
                "expected_records": expected,
                "quote_usd": round(quotes[group], 4),
            }
        )
        print(f"OK {group}: {path.stat().st_size:,} bytes, expected {expected:,} records")

    (args.out / "SHA256SUMS").write_text(
        "".join(f"{f['sha256']}  {f['file']}\n" for f in files), encoding="utf-8"
    )
    manifest = {
        "status": "practice_only_daily_bars",
        "approved_by": "Jason 2026-10-27 (daily bars only, free Databento credits)",
        "downloaded_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "dataset": DATASET,
        "schema": "ohlcv-1d",
        "stype_in": "parent",
        "start": START,
        "end_exclusive": END,
        "quoted_total_usd": round(total, 2),
        "files": files,
    }
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"done: {len(files)} files, quoted ${total:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

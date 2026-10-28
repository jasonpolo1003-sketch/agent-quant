"""Download Databento CME 1-minute bars + definitions for the multi-market practice set.

Approved by Jason 2026-10-28: ZN, 6E, GC, ZC outright contracts only (no spreads, no CL),
2019-05-01..2024-12-31, paid from free Databento credits only ($55 left, confirmed by
Jason). Quoted $45.83 on 2026-10-28. Refuses if the re-quote exceeds the cap, any end
date after 2025-01-01 (the exam period stays unbought and unread) or an existing output.

    uv run python scripts/fetch_databento_minute.py --out C:/Users/jason/Projects/Quant/data/databento/multi_2019-05-01_2024-12-31
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
START, END = "2019-05-01", "2025-01-01"  # end exclusive
LOCKED_FROM = date(2025, 1, 1)
SCHEMAS = ("ohlcv-1m", "definition")
# Listed contract months (CME); every outright expiring 2019-06..2025-07 (covers the
# contracts trading on any practice day, including the next one during a roll).
MONTHS = {"ZN": "HMUZ", "6E": "HMUZ", "GC": "GJMQVZ", "ZC": "HKNUZ"}
MONTH_CODES = "FGHJKMNQUVXZ"
APPROVED_MAX_USD = 47.00  # quote $45.83 + small rounding margin; credit is $55


def api_key() -> str:
    for line in (PROJECT_ROOT / ".env").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*DATABENTO_API_KEY\s*=\s*['\"]?([^'\"\s]+)", line)
        if m:
            return m.group(1)
    raise SystemExit("DATABENTO_API_KEY missing from .env")


def symbols(root: str) -> list[str]:
    out = []
    for year in range(2019, 2026):
        for code in MONTHS[root]:
            month = MONTH_CODES.index(code) + 1
            if (2019, 6) <= (year, month) <= (2025, 7):
                out.append(f"{root}{code}{year % 10}")
    return out


def params(root: str, schema: str) -> dict[str, str]:
    return {
        "dataset": DATASET,
        "symbols": ",".join(symbols(root)),
        "stype_in": "raw_symbol",
        "schema": schema,
        "start": START,
        "end": END,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--quote-only", action="store_true")
    args = parser.parse_args()
    if date.fromisoformat(END) > LOCKED_FROM:
        raise SystemExit("refusing: end date reaches the locked exam period")
    if args.out.exists() and not args.quote_only:
        raise SystemExit(f"refusing to overwrite {args.out}")
    session = requests.Session()
    session.auth = (api_key(), "")

    def meta(endpoint: str, root: str, schema: str):
        r = session.get(f"{API}/metadata.{endpoint}", params=params(root, schema), timeout=60)
        r.raise_for_status()
        return r.json()

    quotes = {(r, s): float(meta("get_cost", r, s)) for r in MONTHS for s in SCHEMAS}
    total = sum(quotes.values())
    print(f"re-quoted total ${total:.2f}")
    if total > APPROVED_MAX_USD:
        raise SystemExit(
            f"quote ${total:.2f} exceeds the approved ${APPROVED_MAX_USD:.2f}; nothing downloaded"
        )
    if args.quote_only:
        return 0

    args.out.mkdir(parents=True)
    files = []
    for (root, schema), quote in quotes.items():
        expected = int(meta("get_record_count", root, schema))
        path = args.out / f"glbx-mdp3_{schema}_{root}_20190501-20241231.dbn.zst"
        with session.get(
            f"{API}/timeseries.get_range",
            params=params(root, schema) | {"encoding": "dbn", "compression": "zstd"},
            stream=True,
            timeout=1800,
        ) as r:
            r.raise_for_status()
            with path.open("wb") as handle:
                for chunk in r.iter_content(1 << 20):
                    handle.write(chunk)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        files.append(
            {
                "root": root,
                "schema": schema,
                "symbols": symbols(root),
                "file": path.name,
                "sha256": digest,
                "expected_records": expected,
                "quote_usd": round(quote, 4),
            }
        )
        print(f"OK {root} {schema}: {path.stat().st_size:,} bytes, expected {expected:,} records")

    (args.out / "SHA256SUMS").write_text(
        "".join(f"{f['sha256']}  {f['file']}\n" for f in files), encoding="utf-8"
    )
    manifest = {
        "status": "practice_only_minute_bars",
        "approved_by": "Jason 2026-10-28 (4 markets, outrights only, free credits only)",
        "downloaded_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "dataset": DATASET,
        "stype_in": "raw_symbol",
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

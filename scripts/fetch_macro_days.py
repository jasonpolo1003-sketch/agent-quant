"""Macro release days for the practice period (new-edge plan; diagnostic slice only).

    .venv/Scripts/python.exe scripts/fetch_macro_days.py

FRED release dates (official, free key FRED_API_KEY from .env) for CPI, jobs report,
GDP, PCE and PPI, 2019-05-01..2024-12-31 (never the exam period). Writes
brain/_system/futures/macro_release_days_2019_2024.csv and its .sha256 pin.
This product uses the FRED® API but is not endorsed or certified by the Federal
Reserve Bank of St. Louis.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
import time
import urllib.parse
import urllib.request

from quant_brain.config import PROJECT_ROOT

URL = "https://api.stlouisfed.org/fred/release/dates"
RELEASES = {10: "CPI", 50: "jobs", 53: "GDP", 54: "PCE", 46: "PPI"}
START, END = "2019-05-01", "2024-12-31"
OUT = PROJECT_ROOT / "brain" / "_system" / "futures" / "macro_release_days_2019_2024.csv"


def api_key() -> str:
    key = os.environ.get("FRED_API_KEY", "")
    env = PROJECT_ROOT / ".env"
    if not key and env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("FRED_API_KEY="):
                key = line.split("=", 1)[1].strip().strip("\"'")
    if not key:
        raise SystemExit("FRED_API_KEY not set (environment or .env)")
    return key


def main() -> int:
    key = api_key()
    rows = []
    for rid, name in RELEASES.items():
        query = urllib.parse.urlencode(
            {
                "release_id": rid,
                "realtime_start": START,
                "realtime_end": END,
                "include_release_dates_with_no_data": "false",
                "sort_order": "asc",
                "limit": 10000,
                "file_type": "json",
                "api_key": key,
            }
        )
        with urllib.request.urlopen(f"{URL}?{query}", timeout=30) as r:
            data = json.load(r)
        for d in data.get("release_dates", []):
            if START <= d["date"] <= END:
                rows.append((d["date"], name, rid))
        time.sleep(0.5)  # modest request rate
    rows.sort()
    with OUT.open("w", encoding="utf-8", newline="") as h:
        w = csv.writer(h, lineterminator="\n")
        w.writerow(["release_date", "release", "fred_release_id"])
        w.writerows(rows)
    OUT.with_suffix(".sha256").write_text(
        hashlib.sha256(OUT.read_bytes()).hexdigest() + "\n", encoding="utf-8"
    )
    counts = {n: sum(1 for r in rows if r[1] == n) for n in RELEASES.values()}
    print(f"wrote {OUT.relative_to(PROJECT_ROOT).as_posix()}: {len(rows)} rows {counts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

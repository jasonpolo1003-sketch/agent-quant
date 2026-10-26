"""Outcome-blind session eligibility/coverage audit on the dev-only partition.

Writes per-session coverage (no prices) and a summary for MNQ (primary) and
MES (comparison). Development 2019-05-01..2023-12-31; diagnostics 2024.

    uv run python scripts/audit_dev_sessions.py \
        --dev-dir C:/Users/jason/OneDrive/Desktop/Quant/data/databento/dev_2019-05-01_2024-12-31
"""

from __future__ import annotations

import argparse
import csv
import importlib.metadata
import json
import sys
from dataclasses import asdict, fields
from datetime import date
from pathlib import Path

from quant_brain.config import BRAIN_DIR
from quant_brain.futures.dev_partition import sha256_file
from quant_brain.futures.session_audit import (
    SessionRow,
    audit_sessions,
    read_bar_keys,
    read_mappings,
    summarize,
)

BARS = "glbx-mdp3_ohlcv-1m_MES-MNQ-FUT_20190501-dev.dbn.zst"
ROLL_CSV = BRAIN_DIR / "sources" / "mes_mnq" / "contracts" / "roll_calendar_2019_2026.csv"
OUT = BRAIN_DIR / "_system" / "futures"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--dev-dir", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads((args.dev_dir / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("status") != "development_only_partition":
        print("FAIL  not a development-only partition")
        return 1
    bars_path = args.dev_dir / BARS
    expected = next(r["output_sha256"] for r in manifest["ohlcv"] if r["output"] == BARS)
    if sha256_file(bars_path) != expected:
        print("FAIL  dev partition hash mismatch")
        return 1

    bars = read_bar_keys(bars_path)
    mappings = read_mappings(bars_path)
    rows: list[SessionRow] = []
    for root in ("MNQ", "MES"):
        rows += audit_sessions(
            bars,
            mappings,
            ROLL_CSV,
            root=root,
            start=date(2019, 5, 1),
            end=date(2024, 12, 31),
            dev_end=date(2023, 12, 31),
        )

    with (OUT / "session-audit-dev.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[f.name for f in fields(SessionRow)])
        writer.writeheader()
        writer.writerows(asdict(r) for r in rows)
    summary = {
        "status": "outcome_blind_coverage_audit; not frozen eligibility",
        "inputs": {
            "bars": BARS,
            "bars_sha256": expected,
            "roll_calendar": ROLL_CSV.relative_to(BRAIN_DIR.parent).as_posix(),
            "roll_calendar_sha256": sha256_file(ROLL_CSV),
        },
        "calendar_source": {
            "package": "pandas_market_calendars",
            "version": importlib.metadata.version("pandas_market_calendars"),
            "calendars": ["NYSE (cash-open sessions)", "CME_Equity (Globex close)"],
            "note": "secondary, versioned rule set; official CME notices not retrieved (cmegroup.com timed out 2026-10-26)",
        },
        "rules": {
            "session": "NYSE trading day (08:30 CT cash open exists)",
            "live_window": "08:45 CT through exit minute (15:07, or CME close minus 3 min on early-close days)",
            "atr_warmup": "each of the 14 prior NYSE sessions has >=1 bar 08:30-15:00 CT on the same dated contract",
            "contract": "D-ROLL-01 fixed calendar roll",
        },
        "MNQ": summarize([r for r in rows if r.root == "MNQ"]),
        "MES": summarize([r for r in rows if r.root == "MES"]),
    }
    (OUT / "session-audit-dev.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({k: summary[k] for k in ("MNQ", "MES")}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

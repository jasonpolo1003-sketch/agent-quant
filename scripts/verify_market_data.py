"""Classify every market dataset as accepted / unregistered / incomplete / invalid.

Read-only. Exit 1 if any dataset is invalid; incomplete and unregistered
artifacts are reported for a manual decision (nothing is deleted).

    uv run python scripts/verify_market_data.py
"""

from __future__ import annotations

import sys

from quant_brain.config import PROJECT_ROOT
from quant_brain.data.market_data import verify_datasets
from quant_brain.db.init_db import DEFAULT_DB_PATH


def main() -> int:
    reports = verify_datasets(PROJECT_ROOT, DEFAULT_DB_PATH)
    if not reports:
        print("no datasets found")
    for report in reports:
        print(f"{report.state.upper():12} {report.dataset_id}  {report.path or ''}")
        for problem in report.problems:
            print(f"             {problem}")
    return 1 if any(report.state == "invalid" for report in reports) else 0


if __name__ == "__main__":
    sys.exit(main())

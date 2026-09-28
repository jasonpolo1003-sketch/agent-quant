"""Verify every hash each Failed_Runs receipt records against the evidence on disk.

Read-only. Follows brain/00_Inbox/Source_Snapshots/reconciliation.json where
snapshot bytes were moved, and checks each moved file's own sha256.

    uv run python scripts/verify_receipts.py

Exit 0 only if every recorded hash verifies.
"""

from __future__ import annotations

import sys

from quant_brain.config import PROJECT_ROOT
from quant_brain.research.receipts import verify_all_receipts


def main() -> int:
    results = verify_all_receipts(PROJECT_ROOT)
    for result in results:
        status = "OK" if not result.problems else "FAIL"
        print(f"{status}  {result.run_id}: {result.checked} recorded hashes checked")
        for problem in result.problems:
            print(f"      {problem}")
    return 0 if all(not result.problems for result in results) else 1


if __name__ == "__main__":
    sys.exit(main())

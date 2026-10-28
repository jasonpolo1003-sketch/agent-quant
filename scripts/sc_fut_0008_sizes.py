"""SC-FUT-0008 sleeve sizes from volatility only (no strategy result is read).

For each market: the median, over practice days, of the session range (highest high -
lowest low from the session open to the flatten bar) in dollars per traded contract.
MNQ is fixed at 2 contracts; every other market gets round(2 x MNQ range / its range)
contracts, and is dropped if that rounds to 0.

    uv run python scripts/sc_fut_0008_sizes.py --out brain/_system/futures/sc-fut-0008-sizes.json
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

from quant_brain.config import PROJECT_ROOT
from quant_brain.futures.orb import TICK_CENTS
from quant_brain.workbench import engine
from quant_brain.workbench.noise import _session

MNQ_SIZE = 2


def _workbench():
    spec = importlib.util.spec_from_file_location("wb", PROJECT_ROOT / "scripts" / "workbench.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def median_range_usd(days, market: str) -> tuple[float, int]:
    open_at, _, flat = _session(market)
    ranges = []
    for d in days:
        bars = [b for m, b in d.bars.items() if open_at <= m < flat]
        if bars:
            ranges.append(max(b[1] for b in bars) - min(b[2] for b in bars))
    return float(np.median(ranges)) * TICK_CENTS[market] / 100, len(ranges)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    wb = _workbench()
    start, end = engine.PRACTICE
    out = {}
    mnq_days = wb.dev_loader(wb.DEV_DIR)("MNQ", start, end, "volume_roll_date")
    mnq, n = median_range_usd(mnq_days, "MNQ")
    out["MNQ"] = {"median_session_range_usd": round(mnq, 2), "days": n, "size": MNQ_SIZE}
    load = wb.multi_loader(wb.MULTI_DIR)
    for market in ("ZN", "M6E", "MGC"):  # ZC not bought: credits ran out (402), 2026-10-28
        r, n = median_range_usd(load(market, start, end, "volume_roll_date"), market)
        size = round(MNQ_SIZE * mnq / r)
        out[market] = {"median_session_range_usd": round(r, 2), "days": n, "size": size}
        print(market, out[market], flush=True)
    print("MNQ", out["MNQ"])
    path = PROJECT_ROOT / args.out
    path.write_text(json.dumps({"rule": __doc__.split("\n\n")[1], "sizes": out}, indent=2) + "\n")
    print(f"written {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""SC-FUT-0006 high-volatility day filter (frozen spec sc-fut-0006-spec.v1.json).

Pure functions over daily bars; scripts/build_hv_days.py feeds them NQ daily bars and
writes the day list the noise-area plug-in reads. Only information from bars that end
before the trade date's open is used.
"""

from __future__ import annotations

import math
import statistics
from bisect import bisect_left
from collections.abc import Iterable
from datetime import date
from itertools import pairwise

WINDOW = 20
LOOKBACK = 252


def front_returns(rows: Iterable[tuple[date, str, float, int]]) -> list[tuple[date, float]]:
    """(bar date, ln return) for the highest-volume contract of each weekday bar date.

    The return is against that same contract's previous bar, so rolls never create a jump.
    """
    by_contract: dict[str, list[tuple[date, float]]] = {}
    best: dict[date, tuple[int, str]] = {}
    for day, contract, close, volume in rows:
        if day.weekday() >= 5:
            continue
        by_contract.setdefault(contract, []).append((day, close))
        if day not in best or volume > best[day][0]:
            best[day] = (volume, contract)
    previous: dict[tuple[str, date], float] = {}
    for contract, bars in by_contract.items():
        bars.sort()
        for (_, before), (day, _) in pairwise(bars):
            previous[(contract, day)] = before
    closes = {(c, d): close for c, bars in by_contract.items() for d, close in bars}
    out = []
    for day in sorted(best):
        contract = best[day][1]
        before = previous.get((contract, day))
        if before is not None and before > 0:
            out.append((day, math.log(closes[(contract, day)] / before)))
    return out


def vol_series(returns: list[tuple[date, float]], window: int = WINDOW) -> list[tuple[date, float]]:
    """(bar date, sample std of the last `window` returns up to and including it)."""
    return [
        (returns[i][0], statistics.stdev(r for _, r in returns[i - window + 1 : i + 1]))
        for i in range(window - 1, len(returns))
    ]


def high_vol_days(
    trade_dates: Iterable[date], vols: list[tuple[date, float]], lookback: int = LOOKBACK
) -> list[tuple[date, date | None, float | None, float | None, bool]]:
    """(trade date, bar date used, vol, median of the previous `lookback` vols, high?)."""
    dates = [d for d, _ in vols]
    out = []
    for trade_date in trade_dates:
        i = bisect_left(dates, trade_date) - 1  # last bar strictly before the trade date
        if i < lookback:
            out.append((trade_date, dates[i] if i >= 0 else None, None, None, False))
            continue
        vol = vols[i][1]
        median = statistics.median(v for _, v in vols[i - lookback : i])
        out.append((trade_date, dates[i], vol, median, vol > median))
    return out

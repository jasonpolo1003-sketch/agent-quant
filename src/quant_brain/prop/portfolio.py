"""Several sleeves (one rule on one market at a fixed size) in one prop account (plan A1).

Each sleeve's day (close, low) in dollars comes from `replay.day_dollars`, so costs and
non-evaluable stress days are handled exactly as for a single market. Sleeves are
aligned on the calendar: a date a market did not trade adds $0 to that sleeve.

- Day close = sum of sleeve closes.
- Day low = sum of sleeve lows. The lows can happen at different minutes, so this is
  never kinder than the true combined low (pessimistic for every loss-limit check).
- The daily loss limit applies to the combined day, with each sleeve's slippage.
- Luck: every sleeve takes random direction, the same draw column per day; each
  market's control is seeded by its own root, so the sleeves' luck is independent.
  The resampled days are shared, so cross-market correlation is kept.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from quant_brain.futures.orb import TICK_CENTS
from quant_brain.prop import funded
from quant_brain.prop.account import Rules
from quant_brain.prop.replay import DLL_SLIP_TICKS, SEED, _cash_stats, block_paths, day_dollars
from quant_brain.workbench.engine import DayTable


@dataclass(frozen=True)
class Sleeve:
    name: str
    table: DayTable
    market: str
    size: int


@dataclass
class Book:
    """Combined day arrays: strategy (close, low) per date, control per date x draw."""

    dates: np.ndarray
    close: np.ndarray
    low: np.ndarray
    c_close: np.ndarray
    c_low: np.ndarray
    slip: float  # dollars added to the DLL exit for the whole book


def combine(sleeves: list[Sleeve], level: str = "L3", draws: int | None = None) -> Book:
    if not sleeves:
        raise ValueError("no sleeves")
    dates = np.array(sorted(set().union(*(s.table.dates.tolist() for s in sleeves))))
    k = draws or min(s.table.ctrl_gross.shape[1] for s in sleeves)
    close, low = np.zeros(len(dates)), np.zeros(len(dates))
    c_close, c_low = np.zeros((len(dates), k)), np.zeros((len(dates), k))
    slip = 0.0
    for s in sleeves:
        sc, sl, cc, cl = day_dollars(s.table, s.market, s.size, level)
        at = np.searchsorted(dates, s.table.dates)
        close[at] += sc
        low[at] += sl
        c_close[at] += cc[:, :k]
        c_low[at] += cl[:, :k]
        slip += s.size * DLL_SLIP_TICKS * TICK_CENTS[s.market] / 100
    return Book(dates, close, np.minimum(low, close), c_close, np.minimum(c_low, c_close), slip)


def _bootstrap(book: Book, combine_rules, xfa_rules, horizon, n_paths, rng, dll, order=None):
    close, low, c_close, c_low = book.close, book.low, book.c_close, book.c_low
    if dll is not None:
        close, low = funded.apply_dll(close, low, dll, book.slip)
        c_close, c_low = funded.apply_dll(c_close, c_low, dll, book.slip)
    if order is not None:
        close, low, c_close, c_low = close[order], low[order], c_close[order], c_low[order]
    idx = block_paths(len(close), horizon, n_paths, rng)
    draws = rng.integers(c_close.shape[1], size=idx.shape)
    strat = [funded.lifecycle(close[i], low[i], combine_rules, xfa_rules, horizon) for i in idx]
    luck = [
        funded.lifecycle(c_close[i, d], c_low[i, d], combine_rules, xfa_rules, horizon)
        for i, d in zip(idx, draws, strict=True)
    ]
    return strat, luck


def evaluate(
    book: Book,
    combine_rules: Rules,
    xfa_rules: funded.XfaRules,
    *,
    payout_range: tuple[float, float],
    horizon: int = 42,
    dll: float | None = 1_000,
    n_paths: int = 2_000,
    outer: int = 40,
    inner: int = 300,
    seed: int = SEED,
) -> dict[str, Any]:
    """Cash gate: mean net > $0 AND lower 90% bound of (net - luck) > $0 AND payout chance in range.

    Luck plays the same sleeves and sizes, so volatility alone earns it nothing extra.
    """
    rng = np.random.default_rng(seed)
    strat, luck = _bootstrap(book, combine_rules, xfa_rules, horizon, n_paths, rng, dll)
    diffs = []
    for _ in range(outer):
        order = block_paths(len(book.dates), len(book.dates), 1, rng)[0]
        s, lk = _bootstrap(book, combine_rules, xfa_rules, horizon, inner, rng, dll, order)
        diffs.append(np.mean([o.net for o in s]) - np.mean([o.net for o in lk]))
    lo, hi = float(np.percentile(diffs, 5)), float(np.percentile(diffs, 95))
    st = _cash_stats(strat)
    payout = st["chance_any_payout"]
    checks = {
        "mean_net_cash_positive": st["mean_net_cash"] > 0,
        "beats_luck": lo > 0,
        "payout_chance_in_stated_range": payout_range[0] <= payout <= payout_range[1],
    }
    return {
        "horizon_days": horizon,
        "daily_loss_limit": dll,
        "days": len(book.dates),
        "strategy": st,
        "luck": _cash_stats(luck),
        "net_cash_minus_luck_90ci": [lo, hi],
        "stated_payout_range": list(payout_range),
        "checks": checks,
        "gate": "pass" if all(checks.values()) else "fail",
    }

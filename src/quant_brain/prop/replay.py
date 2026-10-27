"""Replays of a workbench run through the evaluation account (plan P4).

- Bootstrap: non-wrapping stationary blocks of whole days (mean 20 days, so
  volatile stretches stay together). The strategy and its luck baseline use the
  same resampled days; the baseline takes one random control draw per day.
- Outer resampling of history gives a range for the strategy-minus-luck pass rate.
- Walk-forward: an attempt starting on every real day, run on the actual
  sequence; overlapping attempts are reported with an effective sample size,
  and attempts that run out of data are counted as censored.
Days the engine marked non-evaluable are kept at a stress value (the 5th
percentile of evaluable day lows) rather than dropped.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from quant_brain.prop.account import Outcome, Rules, attempt
from quant_brain.workbench.analysis import COSTS
from quant_brain.workbench.engine import EVALUABLE, DayTable

MEAN_BLOCK = 20
SEED = 20261027


def day_dollars(table: DayTable, market: str, size: int, level: str = "L3"):
    """Strategy (closes, lows) per day and control (closes, lows) per day x draw, in dollars."""
    cost = COSTS[level][market]
    close = (size * table.orb_gross - size * cost * table.orb_trades) / 100
    low = (size * table.orb_low - size * cost * table.orb_trades) / 100
    c_close = (size * table.ctrl_gross - size * cost * table.ctrl_trades) / 100
    c_low = (size * table.ctrl_low - size * cost * table.ctrl_trades) / 100
    good = np.isin(table.status, EVALUABLE)
    stress = float(np.percentile(low[good], 5)) if good.any() else 0.0
    close, low = np.where(good, close, stress), np.where(good, low, stress)
    bad_ctrl = ~table.ctrl_ok
    c_stress = float(np.percentile(c_low[table.ctrl_ok], 5)) if table.ctrl_ok.any() else 0.0
    c_close[bad_ctrl], c_low[bad_ctrl] = c_stress, c_stress
    return close, np.minimum(low, close), c_close, np.minimum(c_low, c_close)


def block_paths(
    n_days: int, length: int, n_paths: int, rng: np.random.Generator, mean_block: int = MEAN_BLOCK
):
    """Non-wrapping stationary bootstrap: a block never runs past the last day into the first."""
    out = np.empty((n_paths, length), dtype=np.int64)
    for p in range(n_paths):
        j = 0
        while j < length:
            start = int(rng.integers(n_days))
            run = min(int(rng.geometric(1 / mean_block)), n_days - start, length - j)
            out[p, j : j + run] = np.arange(start, start + run)
            j += run
    return out


def _stats(outcomes: list[Outcome]) -> dict[str, Any]:
    passed = [o for o in outcomes if o.passed]
    n = len(outcomes)
    return {
        "attempts": n,
        # Passing within the horizon with unlimited resets can be bought; the fair comparison is
        # passing an account before blowing it up (first account, no reset).
        "first_account_pass_rate": sum(o.passed and o.resets == 0 for o in outcomes) / n
        if n
        else None,
        "pass_rate_with_resets": len(passed) / n if n else None,
        "median_days_to_pass": float(np.median([o.days for o in passed])) if passed else None,
        "mean_fees": float(np.mean([o.fees for o in outcomes])) if n else None,
        "fees_per_pass": float(sum(o.fees for o in outcomes) / len(passed)) if passed else None,
        "mean_resets": float(np.mean([o.resets for o in outcomes])) if n else None,
        "censored_share": sum(o.censored for o in outcomes) / n if n else None,
    }


def bootstrap(table, market, size, rules, horizon, n_paths, rng, level="L3", order=None):
    close, low, c_close, c_low = day_dollars(table, market, size, level)
    if order is not None:  # a resampled history (outer loop)
        close, low, c_close, c_low = close[order], low[order], c_close[order], c_low[order]
    idx = block_paths(len(close), horizon, n_paths, rng)
    draws = rng.integers(c_close.shape[1], size=idx.shape)
    strat = [attempt(close[i], low[i], rules, horizon) for i in idx]
    luck = [
        attempt(c_close[i, d], c_low[i, d], rules, horizon) for i, d in zip(idx, draws, strict=True)
    ]
    return strat, luck


def walk_forward(table, market, size, rules, horizon, level="L3"):
    close, low, _, _ = day_dollars(table, market, size, level)
    outcomes = [attempt(close[s:], low[s:], rules, horizon) for s in range(len(close))]
    finished = [o for o in outcomes if not o.censored]
    rate = sum(o.passed for o in finished) / len(finished) if finished else None
    n_eff = max(1, len(close) // horizon)
    lo = hi = None
    if rate is not None:  # Wilson interval on the effective (non-overlapping) sample
        z = 1.645
        centre = (rate + z * z / (2 * n_eff)) / (1 + z * z / n_eff)
        half = (
            z * math.sqrt(rate * (1 - rate) / n_eff + z * z / (4 * n_eff**2)) / (1 + z * z / n_eff)
        )
        lo, hi = max(0.0, centre - half), min(1.0, centre + half)
    return _stats(outcomes) | {
        "finished_attempts": len(finished),
        "pass_rate_finished": rate,
        "effective_n": n_eff,
        "pass_rate_90ci": [lo, hi],
    }


def evaluate(
    table: DayTable,
    market: str,
    rules: Rules,
    *,
    frozen_size: int,
    horizon: int = 126,
    sizes: tuple[int, ...] = (1, 2, 3, 5),
    n_paths: int = 2_000,
    outer: int = 40,
    inner: int = 300,
    level: str = "L3",
    seed: int = SEED,
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    by_size = {}
    for size in sizes:
        strat, luck = bootstrap(table, market, size, rules, horizon, n_paths, rng, level)
        by_size[str(size)] = {"strategy": _stats(strat), "luck": _stats(luck)}
    luck_best = max(sizes, key=lambda s: by_size[str(s)]["luck"]["first_account_pass_rate"] or 0)
    diffs = []
    n = len(table.dates)
    for _ in range(outer):
        order = block_paths(n, n, 1, rng)[0]
        s_out, _ = bootstrap(table, market, frozen_size, rules, horizon, inner, rng, level, order)
        _, l_out = bootstrap(table, market, luck_best, rules, horizon, inner, rng, level, order)
        first = lambda outs: np.mean([o.passed and o.resets == 0 for o in outs])  # noqa: E731
        diffs.append(first(s_out) - first(l_out))
    lo, hi = (float(np.percentile(diffs, 5)), float(np.percentile(diffs, 95)))
    frozen = by_size[str(frozen_size)]["strategy"]
    timely = frozen["median_days_to_pass"] is not None and frozen["median_days_to_pass"] <= horizon
    return {
        "rules": rules.__dict__,
        "horizon_days": horizon,
        "cost_level": level,
        "frozen_size": frozen_size,
        "luck_best_size": luck_best,
        "by_size": by_size,
        "first_account_pass_minus_luck_90ci": [lo, hi],
        "walk_forward": walk_forward(table, market, frozen_size, rules, horizon, level),
        "phase1_gate": "pass" if (lo > 0 and timely) else "fail",
        "note": "Phase 1: evaluation only; payouts not estimable until Phase 2.",
    }

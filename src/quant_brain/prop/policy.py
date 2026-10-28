"""Account-aware sizing policies (Phase 2, Q6-Q7), from the frozen menu.

A policy picks each morning's size from the account's cushion (equity minus the
loss floor) and may add a daily loss limit (DLL) and, in the Combine only, a
profit stop. Day outcomes for n contracts are built from per-contract day data:
costs are taken from the start of the day (as in `replay.day_dollars`), a DLL day
ends at -(limit + slippage), and a profit stop uses the minute-ordered records
to see whether +stop came before the DLL (a minute touching both is adverse).

The random-direction control gets the identical policy on the same resampled
days, so a policy only counts if it beats luck playing by the same rules.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from quant_brain.futures.orb import TICK_CENTS
from quant_brain.prop import funded
from quant_brain.prop.account import Rules
from quant_brain.prop.replay import DLL_SLIP_TICKS, SEED, _cash_stats, block_paths
from quant_brain.workbench.analysis import COSTS
from quant_brain.workbench.engine import EVALUABLE, DayTable


@dataclass(frozen=True)
class Policy:
    name: str
    fixed: int | None  # None: cushion-based
    dll: bool
    profit_stop: float | None  # Combine only
    stress: float = 629  # worst practice day per contract, dollars
    max_n: int = 5

    def size(self, cushion: float) -> int:
        if self.fixed:
            return self.fixed
        return max(1, min(self.max_n, math.floor(cushion / self.stress)))


def load_policies(path: Path) -> list[Policy]:
    c = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for name, p in c["policies"].items():
        fixed = int(p["size"].split()[0]) if p["size"].split()[0].isdigit() else None
        out.append(
            Policy(
                name,
                fixed,
                p["dll"],
                p["profit_stop_usd"],
                c["stress_day_loss_per_contract_usd"],
                c["max_contracts"],
            )
        )
    return out


class Days:
    """Per-contract day data (dollars) for the strategy (draw None) or one control draw."""

    def __init__(self, table: DayTable, market: str, level: str = "L3"):
        cost = COSTS[level][market] / 100
        self.tick = TICK_CENTS[market] / 100
        good = np.isin(table.status, EVALUABLE)
        self.s_net = table.orb_gross / 100 - cost * table.orb_trades
        self.s_low = np.minimum(table.orb_low / 100 - cost * table.orb_trades, self.s_net)
        self.s_cost = cost * table.orb_trades
        self.s_good = good
        self.s_stress = float(np.percentile(self.s_low[good], 5)) if good.any() else 0.0
        self.c_net = table.ctrl_gross / 100 - cost * table.ctrl_trades
        self.c_low = np.minimum(table.ctrl_low / 100 - cost * table.ctrl_trades, self.c_net)
        self.c_cost = cost * table.ctrl_trades
        self.c_good = table.ctrl_ok
        ok = table.ctrl_ok
        self.c_stress = float(np.percentile(self.c_low[ok], 5)) if ok.any() else 0.0
        self.t = table
        self.n_days = len(table.dates)
        self.draws = table.ctrl_gross.shape[1]
        self._max_high: dict[tuple[int, int | None], float] = {}

    def _records(self, day: int, draw: int | None) -> np.ndarray:
        t = self.t
        if draw is None:
            return t.orb_rec[t.orb_rec_off[day] : t.orb_rec_off[day + 1]] / 100
        k = int(t.ctrl_rec_idx[day, draw])
        if k < 0:
            raise ValueError("this workbench run has no control records; re-run it")
        return t.ctrl_rec[t.ctrl_rec_off[k] : t.ctrl_rec_off[k + 1]] / 100

    def outcome(
        self, day: int, draw: int | None, n: int, dll: float | None, stop: float | None
    ) -> tuple[float, float]:
        """(close, low) in dollars for n contracts."""
        slip = n * DLL_SLIP_TICKS * self.tick
        if draw is None:
            good, net, low, cost = (
                self.s_good[day],
                self.s_net[day],
                self.s_low[day],
                self.s_cost[day],
            )
            stress = self.s_stress
        else:
            good, net, low = self.c_good[day], self.c_net[day, draw], self.c_low[day, draw]
            cost, stress = self.c_cost[day, draw], self.c_stress
        if not good:  # non-evaluable day: stress value, still capped by the DLL
            close = lo = n * stress
        else:
            close, lo = n * net, n * low
            if stop is not None:
                run_low = 0.0 - n * cost
                for r_lo, r_hi in self._records(day, draw):
                    lo_d, hi_d = n * (r_lo - cost), n * (r_hi - cost)
                    run_low = min(run_low, lo_d)
                    if dll is not None and lo_d <= -dll:
                        break  # the DLL comes first (adverse first within a minute)
                    if hi_d >= stop:
                        return stop - slip, min(run_low, stop - slip)
        if dll is not None and lo <= -dll:
            out = -(dll + slip)
            return out, min(lo, out)
        return close, lo

    @property
    def has_records(self) -> bool:
        t = self.t
        return t.orb_rec_off.size == self.n_days + 1 and t.ctrl_rec_idx.shape == (
            self.n_days,
            self.draws,
        )

    def max_high(self, day: int, draw: int | None) -> float:
        """Highest equity record of the day per contract, net of the day's cost (inf if unknown).

        A profit stop above n x this can never trigger, so callers may drop it (same outcome).
        """
        if not self.has_records:
            return math.inf
        key = (day, draw)
        cache = self._max_high
        if key not in cache:
            good = self.s_good[day] if draw is None else self.c_good[day]
            cost = self.s_cost[day] if draw is None else self.c_cost[day, draw]
            recs = self._records(day, draw) if good else np.zeros((0, 2))
            cache[key] = (float(recs[:, 1].max()) if len(recs) else 0.0) - cost
        return cache[key]

    def extremes(
        self, day: int, draw: int | None, n: int, dll: float | None, stop: float | None
    ) -> tuple[float, float, float]:
        """(high, give-back, stop_low) in dollars for n contracts, with the same exits as `outcome`.

        high: the day's highest equity (>= 0, the open). give-back: the largest fall from the
        running high to a later low, counting a minute's high before its low (conservative for a
        trailing floor). stop_low: the lowest equity until the day's exit (the DLL fill, the
        profit-stop fill, or the close); `outcome`'s low keeps lows after a DLL exit instead.
        Within a minute the DLL wins a profit stop (adverse first), as in `outcome`.
        Non-evaluable days have no path: high 0, give-back = -low. Needs minute records.
        """
        close, low = self.outcome(day, draw, n, dll, stop)
        good = self.s_good[day] if draw is None else self.c_good[day]
        if not good:
            lo = min(low, close)
            return 0.0, max(0.0, -lo), lo
        if not self.has_records:
            raise ValueError("day highs need minute records; re-run the workbench trial")
        cost = self.s_cost[day] if draw is None else self.c_cost[day, draw]
        slip = n * DLL_SLIP_TICKS * self.tick
        run_low = 0.0 - n * cost
        high, give = 0.0, n * cost
        for r_lo, r_hi in self._records(day, draw):
            lo_d, hi_d = n * (r_lo - cost), n * (r_hi - cost)
            if dll is not None and lo_d <= -dll:
                out = -(dll + slip)
                high = max(high, hi_d)
                return high, max(give, high - min(lo_d, out)), min(run_low, out)
            if stop is not None and hi_d >= stop:
                give = max(give, high - lo_d)
                run_low = min(run_low, lo_d)
                high = max(high, stop)
                return high, max(give, high - (stop - slip)), min(run_low, stop - slip)
            high = max(high, hi_d)
            run_low = min(run_low, lo_d)
            give = max(give, high - lo_d)
        high = max(high, close)
        return high, max(give, high - close), min(run_low, close)


def _pnl(days: Days, policy: Policy, dll_usd: float, idx, draws=None):
    dll = dll_usd if policy.dll else None
    memo: dict[tuple, tuple[float, float]] = {}

    def pnl(d: int, cushion: float, phase: str) -> tuple[float, float]:
        n = policy.size(cushion)
        day = int(idx[d])
        draw = None if draws is None else int(draws[d])
        stop = policy.profit_stop if phase == "combine" else None
        key = (day, draw, n, stop)
        if key not in memo:
            memo[key] = days.outcome(day, draw, n, dll, stop)
        return memo[key]

    return pnl


def run_policy(
    days: Days,
    policy: Policy,
    combine: Rules,
    xfa_rules: funded.XfaRules,
    horizon: int,
    n_paths: int,
    rng: np.random.Generator,
    dll_usd: float = 1_000,
    order: np.ndarray | None = None,
):
    """Strategy and luck lifecycles on the same resampled days (one control draw per day)."""
    base = order if order is not None else np.arange(days.n_days)
    idx = block_paths(len(base), horizon, n_paths, rng)
    draws = rng.integers(days.draws, size=idx.shape)
    zeros = [0.0] * horizon
    strat, luck = [], []
    for i, d in zip(idx, draws, strict=True):
        days_i = base[i]
        s_pnl = _pnl(days, policy, dll_usd, days_i)
        l_pnl = _pnl(days, policy, dll_usd, days_i, d)
        strat.append(funded.lifecycle(zeros, zeros, combine, xfa_rules, horizon, s_pnl))
        luck.append(funded.lifecycle(zeros, zeros, combine, xfa_rules, horizon, l_pnl))
    return strat, luck


def evaluate_policy(
    table: DayTable,
    market: str,
    policy: Policy,
    combine: Rules,
    xfa_rules: funded.XfaRules,
    *,
    horizon: int = 42,
    dll_usd: float = 1_000,
    n_paths: int = 2_000,
    outer: int = 40,
    inner: int = 300,
    level: str = "L3",
    seed: int = SEED,
) -> dict[str, Any]:
    """Net cash for one policy vs luck under the same policy; paired outer resampling."""
    rng = np.random.default_rng(seed)
    days = Days(table, market, level)
    strat, luck = run_policy(days, policy, combine, xfa_rules, horizon, n_paths, rng, dll_usd)
    diffs = []
    for _ in range(outer):
        order = block_paths(days.n_days, days.n_days, 1, rng)[0]
        s, lk = run_policy(days, policy, combine, xfa_rules, horizon, inner, rng, dll_usd, order)
        diffs.append(np.mean([o.net for o in s]) - np.mean([o.net for o in lk]))
    lo, hi = float(np.percentile(diffs, 5)), float(np.percentile(diffs, 95))
    st = _cash_stats(strat)
    first = st["median_days_to_first_payout"]
    eligible = lo > 0 and first is not None and first <= horizon
    return {
        "policy": policy.__dict__,
        "combine_rules": combine.__dict__,
        "xfa_rules": xfa_rules.__dict__,
        "horizon_days": horizon,
        "cost_level": level,
        "strategy": st,
        "luck": _cash_stats(luck),
        "net_cash_minus_luck_90ci": [lo, hi],
        "eligible": eligible,
    }

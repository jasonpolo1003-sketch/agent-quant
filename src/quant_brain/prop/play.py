"""Phase-aware account play across firms (plan E1), from a frozen menu.

A `Play` fixes the contracts in each phase (evaluation, funded), an optional daily
profit stop per phase (dollars, or a named rule resolved against the firm), the
bot's own daily loss stop, stop-at-target, and whether to take a firm's optional
daily loss limit. `resolve` turns a play + firm into per-phase numbers:

- size: cut to the firm's max micros for that phase;
- "consistency_safe": 0.9 x eval consistency share x target (none without the rule);
  "funded_consistency_safe": 0.9 x funded consistency share x (the funded profit
  requirement, else the eval target) (none without the rule);
- daily loss (soft, flatten at -limit, +2 ticks/contract): the tighter of the firm's
  soft limit for that phase and the bot's own stop. A hard firm limit is not a
  flatten level: the state machine fails the account if the low until the exit
  touches it.
- stop at target (evaluation): the day's profit stop is lowered to the profit still
  needed + slippage + $0.01, so the fill lands on the target and the attempt passes.

Day outcomes reuse `policy.Days.outcome` (minute-ordered records: a profit stop vs
the DLL, adverse first within a minute) and `Days.extremes` for intraday highs. A
profit stop the day never reaches is dropped first (same outcome, better memo).
The luck control gets the identical resolved play on the same resampled days.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from quant_brain.prop import firm_sim
from quant_brain.prop.firm_sim import DayContext, DayPath
from quant_brain.prop.firms import Firm
from quant_brain.prop.policy import Days
from quant_brain.prop.replay import DLL_SLIP_TICKS, SEED, _cash_stats, block_paths
from quant_brain.workbench.engine import DayTable

SAFE_SHARE = 0.9  # named stops sit at 90% of the consistency line (menu PROP-PLAY-v1)
NAMED_STOPS = {
    "combine_profit_stop": ("consistency_safe",),
    "funded_profit_stop": ("funded_consistency_safe",),
}
TARGET_EPS = 0.01  # dollars above the target, so a stop-at-target fill passes


@dataclass(frozen=True)
class Play:
    name: str
    combine_size: int
    funded_size: int
    combine_profit_stop: float | str | None = None
    funded_profit_stop: float | str | None = None
    daily_loss_stop: float | None = None  # the bot's own soft stop, both phases
    stop_at_target: bool = True
    optional_daily_loss: bool = True


@dataclass(frozen=True)
class PhasePlan:
    size: int
    stop: float | None  # daily profit stop, dollars
    dll: float | None  # soft daily loss (flatten level), dollars
    walk: bool  # the day's high / give-back / low-until-exit are needed


@dataclass(frozen=True)
class Resolved:
    play: Play
    firm: Firm  # with the optional daily loss applied if the play takes it
    eval: PhasePlan
    funded: PhasePlan
    stop_at_target: bool
    notes: tuple[str, ...] = field(default=())

    def phase(self, name: str) -> PhasePlan:
        return self.eval if name == "eval" else self.funded


def _min(*xs: float | None) -> float | None:
    vals = [x for x in xs if x is not None]
    return min(vals) if vals else None


def resolve(p: Play, firm: Firm) -> Resolved:
    f = firm.with_optional_daily_loss(p.optional_daily_loss)
    ev, fu = f.evaluation, f.funded
    notes = []

    def stop(v, line: float | None) -> float | None:
        if v is None or isinstance(v, int | float):
            return v
        return None if line is None else SAFE_SHARE * line

    e_line = ev.consistency * ev.target if ev is not None and ev.consistency else None
    f_share, f_goal = fu.consistency_at(0), fu.min_profit_at(0)
    if f_goal is None and ev is not None:
        f_goal = ev.target
    f_line = f_share * f_goal if f_share and f_goal else None

    def size(n: int, cap: int | None, phase: str) -> int:
        if cap is not None and n > cap:
            notes.append(f"{phase} size {n} cut to the firm's max {cap}")
            return cap
        return n

    def soft(r) -> float | None:
        return r.daily_loss if r.daily_loss_kind == "soft_pause" else None

    def plan(r, n, cap, s, line, phase) -> PhasePlan:
        if r is None:  # bought funded: the evaluation phase never runs
            return PhasePlan(n, None, None, False)
        walk = r.drawdown == "intraday_trailing" or r.daily_loss_kind == "hard_fail"
        return PhasePlan(size(n, cap, phase), stop(s, line), _min(soft(r), p.daily_loss_stop), walk)

    return Resolved(
        play=p,
        firm=f,
        eval=plan(ev, p.combine_size, f.max_micros, p.combine_profit_stop, e_line, "eval"),
        funded=plan(fu, p.funded_size, f.funded_max_micros, p.funded_profit_stop, f_line, "funded"),
        stop_at_target=p.stop_at_target,
        notes=tuple(notes),
    )


def day_fn(
    days: Days, r: Resolved, idx, draws=None, post_exit_lows: bool = False
) -> firm_sim.DayFn:
    """Day function for one resampled path: strategy (draws None) or one control draw per day.

    The floor is checked against the lowest equity until the day's exit (QA 2026-10-28: after
    a soft-DLL flatten the account is flat, so later market lows cannot breach it).
    `post_exit_lows=True` restores the old `policy` path, which kept the whole day's low
    (pessimistic; only for reproducing the earlier Topstep results).
    """
    memo: dict[tuple, DayPath] = {}

    def fn(ctx: DayContext) -> DayPath:
        ph = r.phase(ctx.phase)
        n = ph.size
        day = int(idx[ctx.day])
        draw = None if draws is None else int(draws[ctx.day])
        stop = ph.stop
        if ctx.phase == "eval" and r.stop_at_target and ctx.to_target is not None:
            at = max(ctx.to_target, 0.0) + n * DLL_SLIP_TICKS * days.tick + TARGET_EPS
            stop = at if stop is None else min(stop, at)
        if stop is not None and stop > n * days.max_high(day, draw):
            stop = None  # never reached today: same outcome without it
        key = (day, draw, n, ph.dll, stop, ph.walk)
        if key not in memo:
            close, low = days.outcome(day, draw, n, ph.dll, stop)
            dll_fired = ph.dll is not None and close <= -ph.dll
            if ph.walk:
                high, give, stop_low = days.extremes(day, draw, n, ph.dll, stop)
                memo[key] = DayPath(
                    close, low if post_exit_lows else stop_low, high, give, stop_low
                )
            elif dll_fired and not post_exit_lows and days.has_records:
                _, _, stop_low = days.extremes(day, draw, n, ph.dll, stop)
                high = max(0.0, close)
                memo[key] = DayPath(close, stop_low, high, high - min(stop_low, close))
            else:
                high = max(0.0, close)
                memo[key] = DayPath(close, low, high, high - min(low, close))
        return memo[key]

    return fn


def run_play(
    days: Days,
    p: Play,
    firm: Firm,
    horizon: int,
    n_paths: int,
    rng: np.random.Generator,
    order: np.ndarray | None = None,
    post_exit_lows: bool = False,
):
    """Strategy and luck lifecycles on the same resampled days (one control draw per day).

    Draws from `rng` exactly as `policy.run_policy`, so the two can be compared path by path.
    """
    r = resolve(p, firm)
    base = order if order is not None else np.arange(days.n_days)
    idx = block_paths(len(base), horizon, n_paths, rng)
    draws = rng.integers(days.draws, size=idx.shape)
    strat, luck = [], []
    for i, d in zip(idx, draws, strict=True):
        days_i = base[i]
        s_fn = day_fn(days, r, days_i, None, post_exit_lows)
        l_fn = day_fn(days, r, days_i, d, post_exit_lows)
        strat.append(firm_sim.lifecycle(r.firm, s_fn, horizon, horizon))
        luck.append(firm_sim.lifecycle(r.firm, l_fn, horizon, horizon))
    return strat, luck


def evaluate_play(
    table: DayTable,
    market: str,
    p: Play,
    firm: Firm,
    *,
    horizon: int = 42,
    n_paths: int = 2_000,
    outer: int = 40,
    inner: int = 300,
    level: str = "L3",
    seed: int = SEED,
) -> dict[str, Any]:
    """Net cash for one firm x play vs luck under the same play.

    Outer resampling of history gives 90% bounds on the mean net cash and on the paired
    (net - luck). Gate: both lower bounds > $0. Luck averaging positive is flagged: it
    points at a simulator or rules-reading error before it points at an edge.
    """
    rng = np.random.default_rng(seed)
    days = Days(table, market, level)
    r = resolve(p, firm)
    strat, luck = run_play(days, p, firm, horizon, n_paths, rng)
    nets, diffs = [], []
    for _ in range(outer):
        order = block_paths(days.n_days, days.n_days, 1, rng)[0]
        s, lk = run_play(days, p, firm, horizon, inner, rng, order)
        nets.append(np.mean([o.net for o in s]))
        diffs.append(nets[-1] - np.mean([o.net for o in lk]))

    def ci(x):
        return [float(np.percentile(x, 5)), float(np.percentile(x, 95))]

    net_ci, diff_ci = ci(nets), ci(diffs)
    st, lk = _cash_stats(strat), _cash_stats(luck)
    return {
        "play": asdict(p),
        "resolved": {
            "eval": asdict(r.eval),
            "funded": asdict(r.funded),
            "notes": list(r.notes),
        },
        "firm": _firm_dict(r.firm),
        "horizon_days": horizon,
        "cost_level": level,
        "strategy": st,
        "luck": lk,
        "net_cash_90ci": net_ci,
        "net_cash_minus_luck_90ci": diff_ci,
        "luck_positive_flag": lk["mean_net_cash"] > 0,
        "gate": "pass" if net_ci[0] > 0 and diff_ci[0] > 0 else "fail",
    }


def _firm_dict(f: Firm) -> dict[str, Any]:
    d = asdict(f)
    d.pop("notes", None)
    return d


# --- menu -------------------------------------------------------------------------------------

_KEYS = {
    "combine_size",
    "funded_size",
    "combine_profit_stop",
    "funded_profit_stop",
    "daily_loss_stop_usd",
    "stop_at_target",
    "optional_daily_loss",
    "note",
}


def load_plays(path: Path) -> list[Play]:
    """Plays from a menu file ("policies": {name: {...}}); unknown keys or stop names raise."""
    c = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for name, p in c["policies"].items():
        extra = set(p) - _KEYS
        if extra:
            raise ValueError(f"policy {name}: unknown keys {sorted(extra)}")
        for k, allowed in NAMED_STOPS.items():
            v = p.get(k)
            if isinstance(v, str) and v not in allowed:
                raise ValueError(f"policy {name}: {k} {v!r} is not one of {allowed}")
        for k in ("combine_size", "funded_size"):
            if not isinstance(p.get(k), int) or p[k] < 1:
                raise ValueError(f"policy {name}: {k} must be a whole number of contracts >= 1")
        out.append(
            Play(
                name,
                p["combine_size"],
                p["funded_size"],
                p.get("combine_profit_stop"),
                p.get("funded_profit_stop"),
                p.get("daily_loss_stop_usd"),
                p.get("stop_at_target", True),
                p.get("optional_daily_loss", True),
            )
        )
    return out

"""Conditions grid (W2), luck checks (W5) and the honesty counter (W6).

Years, volatility regimes and cost levels are slices of one stored run, so they
need no re-simulation. Slices are diagnostics of the same trial; the headline
verdict is the full practice period at L3, judged against a pass bar that
tightens with every distinct trial in the strategy family (Sidak).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from quant_brain.futures import inference
from quant_brain.workbench.engine import DayTable, read_ledger
from quant_brain.workbench.strategies import GRADING

COSTS = {
    # fees + 1 / 2 / 4 / 8 ticks of the traded contract (extra markets: see orb.L3_ROUND_TRIP_CENTS)
    "L1": {"MNQ": 172, "MES": 247, "ZN": 1893, "M6E": 225, "MGC": 292, "ZC": 1778},
    "L2": {"MNQ": 222, "MES": 372, "ZN": 3455, "M6E": 350, "MGC": 392, "ZC": 3028},
    "L3": {"MNQ": 322, "MES": 622, "ZN": 6580, "M6E": 600, "MGC": 592, "ZC": 5528},
    "L4": {"MNQ": 522, "MES": 1122, "ZN": 12830, "M6E": 1100, "MGC": 992, "ZC": 10528},
}
REGIME_LOOKBACK = 250
GRID_REPLICATES = 1_999


def honesty(root: Path, family: str) -> dict[str, Any]:
    """Distinct trials so far in a family, and the pass bar they imply."""
    # Count distinct strategy variations, not fingerprints: a code change re-running the same
    # settings must not inflate the count.
    trials = len(
        {
            json.dumps([e["settings"], e["market"], e["roll"]], sort_keys=True)
            for e in read_ledger(root)
            if e["family"] == family
        }
    )
    n = max(trials, 1)
    alpha = 1 - (1 - inference.ALPHA) ** (1 / n)
    return {"family": family, "trials": trials, "alpha": alpha}


def regimes(table: DayTable) -> np.ndarray:
    """calm / normal / volatile from where today's ATR sits among the prior 250 sessions only."""
    labels = np.full(len(table.atr), "warm-up", dtype="<U8")
    for i in range(REGIME_LOOKBACK, len(table.atr)):
        past = table.atr[i - REGIME_LOOKBACK : i]
        rank = (past < table.atr[i]).mean()
        labels[i] = "calm" if rank < 1 / 3 else "volatile" if rank >= 2 / 3 else "normal"
    return labels


def _nets(table: DayTable, market: str, level: str, *, stress: bool = False):
    cost = COSTS[level][market]
    orb_gross = table.orb_stress_gross if stress else table.orb_gross
    ctrl_gross = table.ctrl_stress_gross if stress else table.ctrl_gross
    orb = orb_gross - cost * table.orb_trades
    draws = ctrl_gross - cost * table.ctrl_trades
    return orb.astype(float), draws.astype(float)


def slice_stats(
    table: DayTable,
    market: str,
    mask: np.ndarray,
    level: str = "L3",
    *,
    replicates: int = GRID_REPLICATES,
) -> dict[str, Any]:
    keep = mask & table.evaluable
    orb, draws = _nets(table, market, level)
    orb, draws = orb[keep], draws[keep]
    out: dict[str, Any] = {"days": int(keep.sum()), "trades": int(table.orb_trades[keep].sum())}
    if out["days"] < 2:
        return out | {"note": "too few days"}
    control = draws.mean(axis=1)
    test = inference.paired_test(orb, control, replicates=replicates)
    totals = draws.sum(axis=0)
    return out | {
        "per_day": orb.mean() / 100,
        "vs_random_per_day": test["observed_cents"] / 100,
        "p_value": test["p_value"],
        "beat_share_of_random": float((totals < orb.sum()).mean()),
    }


def grid(table: DayTable, market: str, *, replicates: int = GRID_REPLICATES) -> dict[str, Any]:
    everything = np.ones(len(table.dates), dtype=bool)
    years = sorted({d[:4] for d in table.dates})
    labels = regimes(table)
    return {
        "costs": {
            lvl: slice_stats(table, market, everything, lvl, replicates=replicates) for lvl in COSTS
        },
        "years": {
            y: slice_stats(table, market, np.char.startswith(table.dates, y), replicates=replicates)
            for y in years
        },
        "regimes": {
            r: slice_stats(table, market, labels == r, replicates=replicates)
            for r in ("calm", "normal", "volatile")
        },
    }


def annual_sharpe(daily_cents: np.ndarray) -> float | None:
    sd = daily_cents.std(ddof=1) if len(daily_cents) > 1 else 0.0
    return None if sd == 0 else float(daily_cents.mean() / sd * np.sqrt(252))


def grade(per_day_cents: float, tiers: list[tuple[int, str]]) -> str:
    label = "fail"
    for floor, name in tiers:
        if per_day_cents >= floor:
            label = name
    return label


def verdict(
    table: DayTable,
    market: str,
    alpha: float,
    family: str = "orb",
    *,
    replicates: int = inference.BOOTSTRAP_DRAWS,
) -> dict[str, Any]:
    """Headline: full practice period at L3, the family's frozen grading and honesty-adjusted bar."""
    rules = GRADING[family]
    good = table.evaluable
    trades = int(table.orb_trades[good].sum())
    affected = int(((table.gap_trades > 0) & good).sum() + (~good).sum())
    missing_share = affected / len(good) if len(good) else 0.0
    out: dict[str, Any] = {
        "days": int(good.sum()),
        "non_evaluable_days": int((~good).sum()),
        "trades": trades,
        "alpha": alpha,
        "floor_cents": rules["floor_cents"],
        "sharpe_min": rules["sharpe_min"],
        "missing_session_share": missing_share,
        "ambiguity_share": float(table.entry_bar_stops[good].sum() / trades) if trades else None,
        "reasons": [],
    }
    if trades == 0 or good.sum() < 2:
        return out | {"outcome": "inconclusive", "grade": "fail", "reasons": ["no trades"]}

    def decide(stress: bool) -> tuple[bool, dict]:
        orb, draws = _nets(table, market, "L3", stress=stress)
        test = inference.paired_test(orb[good], draws[good].mean(axis=1), replicates=replicates)
        absolute = float(orb[good].mean())
        sharpe = annual_sharpe(orb[good])
        ok = test["p_value"] < alpha and absolute >= rules["floor_cents"]
        if rules["sharpe_min"] is not None:
            ok = ok and sharpe is not None and sharpe >= rules["sharpe_min"]
        return ok, test | {"absolute": absolute, "sharpe": sharpe}

    passed, stats = decide(False)
    stress_passed, _ = decide(True)
    outcome = "pass_to_execution_calibration" if passed else "not_demonstrated"
    if missing_share > inference.MISSING_ALARM_SHARE:
        out["reasons"].append("missing-minute alarm above 1%")
        outcome = "inconclusive"
    if passed != stress_passed:
        out["reasons"].append("verdict flips under the worst-case gap bound")
        outcome = "inconclusive"
    if outcome == "not_demonstrated":
        if stats["p_value"] >= alpha:
            out["reasons"].append(
                f"not better than the random benchmark (p {stats['p_value']:.3f} vs bar {alpha:.4f})"
            )
        if stats["absolute"] < rules["floor_cents"]:
            out["reasons"].append(f"below the ${rules['floor_cents'] / 100:.0f}/day floor")
        if rules["sharpe_min"] is not None and (stats["sharpe"] or 0) < rules["sharpe_min"]:
            out["reasons"].append(f"Sharpe {stats['sharpe'] or 0:.2f} below {rules['sharpe_min']}")
    return out | {
        "outcome": outcome,
        "grade": grade(stats["absolute"], rules["tiers"])
        if outcome == "pass_to_execution_calibration"
        else "fail",
        "per_day": stats["absolute"] / 100,
        "vs_random_per_day": stats["observed_cents"] / 100,
        "p_value": stats["p_value"],
        "sharpe": stats["sharpe"],
    }


def always_long(table: DayTable, market: str) -> dict[str, Any]:
    """Diagnostic: the same trades taken long every time (does a plain drift explain it?)."""
    good = table.evaluable & (table.orb_trades > 0)
    if good.sum() < 2:
        return {}
    long_gross = table.orb_side[good] * table.orb_gross[good]
    net = (long_gross - COSTS["L3"][market] * table.orb_trades[good]).astype(float)
    return {
        "days": int(good.sum()),
        "per_trade_day": float(net.mean() / 100),
        "sharpe": annual_sharpe(net),
    }


def summary(
    root: Path,
    table: DayTable,
    record: dict[str, Any],
    *,
    replicates: int = inference.BOOTSTRAP_DRAWS,
) -> dict[str, Any]:
    bar = honesty(root, record["family"])
    return {
        "run": record,
        "honesty": bar,
        "verdict": verdict(
            table, record["market"], bar["alpha"], record["family"], replicates=replicates
        ),
        "always_long": always_long(table, record["market"]),
        "grid": grid(table, record["market"], replicates=min(replicates, GRID_REPLICATES)),
    }

"""Risk Center math for the learning terminal (PROP-010 §5.3).

Plain functions, each returning numbers plus a one-line explanation a beginner
can read. "R" is the amount risked on one trade: a loss of 1R means the stop
was hit; a win of 2R means the trade made twice what was risked.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import pandas as pd


def position_size(account: float, risk_pct: float, entry: float, stop: float) -> dict[str, Any]:
    """Shares to buy so that hitting the stop loses about ``risk_pct`` % of the account."""
    if account <= 0 or entry <= 0 or stop <= 0:
        raise ValueError("account, entry and stop must be positive")
    if not 0 < risk_pct <= 100:
        raise ValueError("risk_pct must be between 0 and 100")
    per_share = abs(entry - stop)
    if per_share == 0:
        raise ValueError("the stop must differ from the entry")
    budget = account * risk_pct / 100
    shares = min(math.floor(budget / per_share), math.floor(account / entry))
    side = "long" if stop < entry else "short"
    value = shares * entry
    risk = shares * per_share
    capped = shares < math.floor(budget / per_share)
    return {
        "side": side, "shares": shares, "position_value": value,
        "dollar_risk": risk, "risk_pct_of_account": 100 * risk / account,
        "position_pct_of_account": 100 * value / account, "capped_by_cash": capped,
        "explain": (
            f"Risking {risk_pct:g}% of ${account:,.0f} is ${budget:,.2f}. The stop is "
            f"${per_share:,.2f} per share away, so buy {shares} shares (${value:,.0f}). "
            f"If the stop is hit you lose about ${risk:,.2f}"
            + (", less than planned because you cannot buy more than your cash." if capped else ".")
        ),
    }


def recovery_needed(loss_pct: float) -> float:
    """The gain (%) needed to get back to even after losing ``loss_pct`` %."""
    if not 0 <= loss_pct < 100:
        raise ValueError("loss_pct must be in [0, 100)")
    return 100 * (1 / (1 - loss_pct / 100) - 1)


def drawdown_table(losses: Sequence[float] = (10, 20, 30, 40, 50, 60, 75, 90)) -> list[dict]:
    return [{"loss_pct": x, "gain_needed_pct": round(recovery_needed(x), 1)} for x in losses]


def expectancy(win_rate: float, payoff: float) -> float:
    """Average result per trade in R: win_rate x payoff - (1 - win_rate) x 1."""
    _check_edge_inputs(win_rate, payoff)
    return win_rate * payoff - (1 - win_rate)


def kelly_fraction(win_rate: float, payoff: float) -> dict[str, Any]:
    """Kelly's bet size as a fraction of the account (never below 0)."""
    _check_edge_inputs(win_rate, payoff)
    full = max(0.0, win_rate - (1 - win_rate) / payoff)
    return {
        "full": full, "half": full / 2,
        "explain": (
            "No edge: Kelly says bet nothing." if full == 0 else
            f"Full Kelly bets {full:.1%} of the account per trade. It assumes your win rate "
            f"and payoff are known exactly, which they never are; overestimate them and full "
            f"Kelly can ruin you. Many traders use half ({full / 2:.1%}) or less."
        ),
    }


def _check_edge_inputs(win_rate: float, payoff: float) -> None:
    if not 0 <= win_rate <= 1:
        raise ValueError("win_rate must be between 0 and 1")
    if payoff <= 0:
        raise ValueError("payoff must be positive")


def simulate_paths(
    win_rate: float, payoff: float, risk_pct: float, *, trades: int = 200, paths: int = 2000,
    ruin_drawdown_pct: float = 50.0, seed: int = 7, sample_paths: int = 20,
) -> dict[str, Any]:
    """Monte Carlo of an account risking ``risk_pct`` % of equity per trade.

    Each trade wins ``payoff`` R with probability ``win_rate`` and otherwise loses
    1R. "Ruin" is a peak-to-trough drawdown of at least ``ruin_drawdown_pct``.
    """
    _check_edge_inputs(win_rate, payoff)
    if not 0 < risk_pct < 100:
        raise ValueError("risk_pct must be between 0 and 100")
    rng = np.random.default_rng(seed)
    wins = rng.random((paths, trades)) < win_rate
    r = risk_pct / 100
    growth = np.where(wins, 1 + r * payoff, 1 - r)
    equity = np.cumprod(growth, axis=1)
    with_start = np.concatenate([np.ones((paths, 1)), equity], axis=1)
    peaks = np.maximum.accumulate(with_start, axis=1)
    worst = (1 - with_start / peaks).max(axis=1) * 100
    final = equity[:, -1]
    ruined = float((worst >= ruin_drawdown_pct).mean())
    return {
        "inputs": {"win_rate": win_rate, "payoff": payoff, "risk_pct": risk_pct,
                   "trades": trades, "paths": paths, "ruin_drawdown_pct": ruin_drawdown_pct,
                   "seed": seed},
        "expectancy_r": expectancy(win_rate, payoff),
        "probability_of_ruin": ruined,
        "final_equity_percentiles": {p: float(np.percentile(final, p)) for p in (5, 25, 50, 75, 95)},
        "worst_drawdown_median_pct": float(np.median(worst)),
        "sample_paths": with_start[:sample_paths].round(4).tolist(),
        "explain": (
            f"Out of {paths:,} simulated traders with the same edge, {ruined:.1%} suffered a "
            f"drop of {ruin_drawdown_pct:g}% or more at some point over {trades} trades. "
            f"The median trader ended at {np.median(final):.2f}x their starting account. "
            "Same rules, very different luck."
        ),
    }


def portfolio_heat(account: float, positions: Sequence[Mapping[str, float]]) -> dict[str, Any]:
    """Total loss if every open position hits its stop at once.

    Each position is ``{"shares": ..., "entry": ..., "stop": ...}``.
    """
    risks = [abs(p["entry"] - p["stop"]) * p["shares"] for p in positions]
    total = float(sum(risks))
    return {
        "dollar_risk": total, "heat_pct": 100 * total / account if account else float("nan"),
        "per_position": risks,
        "explain": (f"If every stop were hit at once you would lose ${total:,.2f} "
                    f"({100 * total / account:.1f}% of the account)." if account else ""),
    }


def correlation_matrix(closes: Mapping[str, pd.Series], window: int | None = None) -> dict[str, Any]:
    """Correlation of daily returns between symbols, on their shared dates."""
    frame = pd.DataFrame({s: pd.Series(c).astype(float) for s, c in closes.items()}).dropna()
    returns = frame.pct_change().dropna()
    if window:
        returns = returns.tail(window)
    corr = returns.corr()
    return {"symbols": list(corr.columns), "matrix": corr.round(3).values.tolist(),
            "days": len(returns),
            "first_date": str(returns.index[0]) if len(returns) else None,
            "last_date": str(returns.index[-1]) if len(returns) else None}

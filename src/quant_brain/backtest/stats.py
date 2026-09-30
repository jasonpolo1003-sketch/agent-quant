"""Performance statistics and the deflated Sharpe ratio, as SC-0002 pins them.

Sharpe: per-period mean / sample std (ddof=1), risk-free 0, annualised by
sqrt(252). DSR (Bailey and Lopez de Prado, 2014), as a probability:
Phi(((SR - SR*) * sqrt(T - 1)) / sqrt(1 - skew * SR + ((kurt - 1) / 4) * SR^2)),
with biased skew and biased raw kurtosis of the returns, and
SR* = sqrt(V) * ((1 - g) * Phi^-1(1 - 1/N) + g * Phi^-1(1 - 1/(N e))),
V = ddof=1 variance of the trials' per-period Sharpe ratios (SR* = 0 if V = 0).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from statistics import NormalDist
from typing import Any

import numpy as np
import pandas as pd

EULER_GAMMA = 0.5772156649
TRADING_DAYS = 252


def sharpe_per_period(returns: Sequence[float] | pd.Series) -> float:
    x = np.asarray(returns, dtype=float)
    std = x.std(ddof=1) if len(x) > 1 else 0.0
    return 0.0 if std == 0 else float(x.mean() / std)


def annualised_sharpe(returns: Sequence[float] | pd.Series) -> float:
    return sharpe_per_period(returns) * math.sqrt(TRADING_DAYS)


def max_drawdown(equity: pd.Series, start: float = 1.0) -> float:
    """Worst peak-to-trough, measured from the starting equity (so a day-1 loss counts)."""
    values = np.concatenate([[start], np.asarray(equity, dtype=float)])
    return float((values / np.maximum.accumulate(values) - 1).min())


def cagr(equity: pd.Series) -> float:
    return float(np.asarray(equity, dtype=float)[-1] ** (TRADING_DAYS / len(equity)) - 1)


def _biased_moments(x: np.ndarray) -> tuple[float, float]:
    centred = x - x.mean()
    m2 = float(np.mean(centred**2))
    if m2 == 0:
        return 0.0, 3.0
    return float(np.mean(centred**3) / m2**1.5), float(np.mean(centred**4) / m2**2)


def deflated_sharpe(returns: Sequence[float], trial_sharpes: Sequence[float]) -> dict[str, Any]:
    x = np.asarray(returns, dtype=float)
    sr = sharpe_per_period(x)
    n = len(trial_sharpes)
    variance = float(np.var(np.asarray(trial_sharpes, dtype=float), ddof=1)) if n > 1 else 0.0
    normal = NormalDist()
    sr_star = 0.0 if variance == 0 else math.sqrt(variance) * (
        (1 - EULER_GAMMA) * normal.inv_cdf(1 - 1 / n)
        + EULER_GAMMA * normal.inv_cdf(1 - 1 / (n * math.e))
    )
    skew, kurt = _biased_moments(x)
    t = len(x)
    denominator = math.sqrt(1 - skew * sr + ((kurt - 1) / 4) * sr**2)
    dsr = normal.cdf((sr - sr_star) * math.sqrt(t - 1) / denominator)
    return {"dsr": dsr, "sr": sr, "sr_star": sr_star, "variance": variance, "n_trials": n,
            "t": t, "skew": skew, "kurtosis": kurt}


def percentile_strictly_below(values: Sequence[float], x: float) -> float | None:
    if not values:
        return None
    return 100.0 * sum(1 for v in values if v < x) / len(values)


def trade_summary(trade_returns: Sequence[float], holding_days: Sequence[int]) -> dict[str, Any]:
    r = np.asarray(trade_returns, dtype=float)
    wins, losses = r[r > 0], r[r < 0]
    return {
        "trades": len(r),
        "average_trade": float(r.mean()) if len(r) else None,
        "win_rate": float(len(wins) / len(r)) if len(r) else None,
        "profit_factor": float(wins.sum() / -losses.sum()) if len(losses) else None,
        "holding_days_mean": float(np.mean(holding_days)) if len(r) else None,
        "holding_days_max": int(np.max(holding_days)) if len(r) else None,
    }

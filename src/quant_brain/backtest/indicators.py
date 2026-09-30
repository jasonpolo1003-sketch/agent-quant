"""Indicators exactly as SC-0002's ``implementation`` block pins them.

- SMA: simple mean of the last n values including the current bar; NaN until
  a full window exists.
- Wilder RSI: average gain and loss seeded with the simple mean of the first
  n changes, then avg = (prev * (n - 1) + current) / n. RSI = 100 when the
  average loss is 0.
- Cutler RSI: simple n-day means of gains and losses. RSI = 100 when the mean
  loss is 0.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def sma(values: pd.Series, n: int) -> pd.Series:
    return values.rolling(n, min_periods=n).mean()


def _rsi_from_averages(avg_gain: np.ndarray, avg_loss: np.ndarray) -> np.ndarray:
    with np.errstate(divide="ignore", invalid="ignore"):
        rsi = 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
    rsi[avg_loss == 0] = 100.0
    rsi[np.isnan(avg_gain) | np.isnan(avg_loss)] = np.nan
    return rsi


def rsi_wilder(values: pd.Series, n: int) -> pd.Series:
    changes = values.diff().to_numpy(dtype="float64")
    gains = np.where(changes > 0, changes, 0.0)
    losses = np.where(changes < 0, -changes, 0.0)
    avg_gain = np.full(len(values), np.nan)
    avg_loss = np.full(len(values), np.nan)
    if len(values) > n:
        avg_gain[n] = gains[1 : n + 1].mean()
        avg_loss[n] = losses[1 : n + 1].mean()
        for i in range(n + 1, len(values)):
            avg_gain[i] = (avg_gain[i - 1] * (n - 1) + gains[i]) / n
            avg_loss[i] = (avg_loss[i - 1] * (n - 1) + losses[i]) / n
    return pd.Series(_rsi_from_averages(avg_gain, avg_loss), index=values.index)


def rsi_cutler(values: pd.Series, n: int) -> pd.Series:
    changes = values.diff()
    gains = changes.clip(lower=0).rolling(n, min_periods=n).mean()
    losses = (-changes).clip(lower=0).rolling(n, min_periods=n).mean()
    avg_gain = gains.to_numpy(dtype="float64", copy=True)
    avg_loss = losses.to_numpy(dtype="float64", copy=True)
    return pd.Series(_rsi_from_averages(avg_gain, avg_loss), index=values.index)

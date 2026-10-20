"""Screener rows and teaching presets for the learning terminal (PROP-010 phase 2).

Each row describes one symbol on its latest bar, from adjusted closes: returns
over common windows, RSI, distance from moving averages, volatility and the
52-week range. Presets are filters with a plain-language "why a quant looks at
this" and "the trap".
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Any

import numpy as np
import pandas as pd

from quant_brain.backtest import indicators as ind

WINDOWS = {"1d": 1, "1w": 5, "1m": 21, "3m": 63, "1y": 252}


def _pct(a: float, b: float) -> float | None:
    return None if b is None or a is None or not b or math.isnan(a) or math.isnan(b) else 100 * (a / b - 1)


def _clean(value: Any) -> Any:
    if isinstance(value, (float, np.floating)):
        return None if math.isnan(value) else round(float(value), 4)
    return value


def screen_row(frame: pd.DataFrame) -> dict[str, Any]:
    """Metrics on the last bar of one symbol's daily frame (needs date, adj_close, close, volume)."""
    close = frame["adj_close"].astype(float).reset_index(drop=True)
    last = len(close) - 1
    row: dict[str, Any] = {"last_date": str(frame["date"].iloc[-1]), "close": close[last],
                           "bars": len(close)}
    for label, n in WINDOWS.items():
        row[f"change_{label}_pct"] = _pct(close[last], close[last - n]) if last >= n else None
    year = str(frame["date"].iloc[-1])[:4]
    prior = frame["date"].astype(str) < year
    row["change_ytd_pct"] = _pct(close[last], close[prior.to_numpy()].iloc[-1]) if prior.any() else None
    row["rsi_2"] = ind.rsi_wilder(close, 2).iloc[-1]
    row["rsi_14"] = ind.rsi_wilder(close, 14).iloc[-1]
    for n in (50, 200):
        sma = ind.sma(close, n).iloc[-1]
        row[f"sma_{n}"] = sma
        row[f"vs_sma_{n}_pct"] = _pct(close[last], sma)
    row["above_sma_200"] = None if math.isnan(row["sma_200"]) else bool(close[last] > row["sma_200"])
    returns = close.pct_change()
    row["volatility_20d_pct"] = returns.tail(20).std(ddof=1) * math.sqrt(252) * 100 if last >= 20 else None
    year_window = close.tail(252)
    row["high_52w"], row["low_52w"] = year_window.max(), year_window.min()
    row["from_52w_high_pct"] = _pct(close[last], row["high_52w"])
    row["from_52w_low_pct"] = _pct(close[last], row["low_52w"])
    dollar = (frame["close"].astype(float) * frame["volume"].astype(float)).tail(20)
    row["avg_dollar_volume_20d"] = dollar.mean()
    peak = close.cummax()
    row["drawdown_from_peak_pct"] = 100 * (close[last] / peak[last] - 1)
    return {k: _clean(v) for k, v in row.items()}


PRESETS: dict[str, dict[str, Any]] = {
    "oversold_uptrend": {
        "title": "Oversold in an uptrend",
        "rule": "RSI(2) below 10 and close above its 200-day average",
        "why": "The entry of the Connors RSI(2) idea tested in SC-0002: a sharp short dip inside a long uptrend.",
        "trap": "SC-0002 showed this setup barely beat random entries after costs on SPY (2016-2026). A list is not an edge.",
        "test": lambda r: r["rsi_2"] is not None and r["rsi_2"] < 10 and r["above_sma_200"] is True,
    },
    "near_high": {
        "title": "Within 3% of the 52-week high",
        "rule": "close at most 3% below the highest close of the last 252 bars",
        "why": "Academic momentum research found that recent 3-12 month winners tended to keep outperforming for a while (Jegadeesh and Titman, 1993, Journal of Finance).",
        "trap": "Momentum can crash when markets rebound sharply, as in 2009 (Daniel and Moskowitz, 2016, Journal of Financial Economics). Compare with a benchmark and count every variant you try.",
        "test": lambda r: r["from_52w_high_pct"] is not None and r["from_52w_high_pct"] >= -3,
    },
    "below_200": {
        "title": "Below the 200-day average",
        "rule": "close below its 200-day simple moving average",
        "why": "A common trend filter: many systems stand aside when price is below its long average.",
        "trap": "It lags. It exits late after crashes and re-enters late after recoveries.",
        "test": lambda r: r["above_sma_200"] is False,
    },
    "calm": {
        "title": "Calmest (lowest 20-day volatility)",
        "rule": "20-day annualised volatility under 15%",
        "why": "Volatility sets position size: a calmer asset can be held in a larger size for the same risk.",
        "trap": "Calm periods end suddenly. Low recent volatility is not low risk.",
        "test": lambda r: r["volatility_20d_pct"] is not None and r["volatility_20d_pct"] < 15,
    },
    "deep_drawdown": {
        "title": "Down 20% or more from its all-time high",
        "rule": "close at least 20% below its highest close in this dataset",
        "why": "Shows how deep and long drawdowns get, even for famous names.",
        "trap": "Cheap can get cheaper. A big drop is not a reason to buy on its own.",
        "test": lambda r: r["drawdown_from_peak_pct"] is not None and r["drawdown_from_peak_pct"] <= -20,
    },
}


def screen(rows: Iterable[dict[str, Any]], preset: str | None = None) -> list[dict[str, Any]]:
    rows = list(rows)
    if preset is None:
        return rows
    test = PRESETS[preset]["test"]
    return [r for r in rows if test(r)]


def presets_public() -> list[dict[str, str]]:
    return [{"id": k, **{f: v[f] for f in ("title", "rule", "why", "trap")}} for k, v in PRESETS.items()]

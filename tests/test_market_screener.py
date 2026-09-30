"""Screener rows on hand-checkable series, and presets that filter them."""

import math

import numpy as np
import pandas as pd
import pytest

from quant_brain.market import screener


def frame(closes, start="2025-01-01"):
    closes = np.asarray(closes, dtype=float)
    return pd.DataFrame({
        "date": pd.bdate_range(start, periods=len(closes)).strftime("%Y-%m-%d"),
        "adj_close": closes, "close": closes * 1.1, "volume": np.full(len(closes), 1000.0),
    })


def test_returns_windows_and_52_week_range():
    closes = np.linspace(100, 200, 300)
    row = screener.screen_row(frame(closes))
    assert row["change_1d_pct"] == pytest.approx(100 * (closes[-1] / closes[-2] - 1), abs=1e-4)
    assert row["change_1y_pct"] == pytest.approx(100 * (closes[-1] / closes[-253] - 1), abs=1e-4)
    assert row["high_52w"] == pytest.approx(200) and row["from_52w_high_pct"] == 0
    assert row["above_sma_200"] is True and row["drawdown_from_peak_pct"] == 0
    assert row["avg_dollar_volume_20d"] == pytest.approx(np.mean(closes[-20:] * 1.1 * 1000), rel=1e-6)


def test_short_history_gives_nulls_not_errors():
    row = screener.screen_row(frame([100, 101, 99]))
    assert row["change_1m_pct"] is None and row["sma_200"] is None
    assert row["above_sma_200"] is None and row["volatility_20d_pct"] is None


def test_ytd_uses_the_last_close_of_the_prior_year():
    f = frame(np.linspace(100, 130, 300), start="2024-06-03")
    row = screener.screen_row(f)
    prior = f[f["date"] < row["last_date"][:4]]["adj_close"].iloc[-1]
    assert row["change_ytd_pct"] == pytest.approx(100 * (130 / prior - 1), abs=1e-4)


def test_a_drop_after_a_long_rise_is_oversold_in_an_uptrend():
    closes = [*np.linspace(100, 200, 260), 190, 180]
    row = screener.screen_row(frame(closes))
    assert row["rsi_2"] < 10 and row["above_sma_200"] is True
    rows = [{"symbol": "X", **row}, {"symbol": "Y", **screener.screen_row(frame(np.linspace(200, 100, 260)))}]
    assert [r["symbol"] for r in screener.screen(rows, "oversold_uptrend")] == ["X"]
    assert [r["symbol"] for r in screener.screen(rows, "below_200")] == ["Y"]
    assert all(not isinstance(v, float) or not math.isnan(v) for v in row.values())


def test_every_preset_explains_itself():
    for p in screener.presets_public():
        assert p["title"] and p["rule"] and p["why"] and p["trap"]

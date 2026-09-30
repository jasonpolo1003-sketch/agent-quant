"""Trade replay reports what the engine saw and did, bar by bar, without changing it."""

import numpy as np
import pandas as pd
import pytest

from quant_brain.backtest import engine
from quant_brain.market.replay import build_replay

RULE = engine.RuleSpec(rule_id="A", rsi_period=2, rsi_method="wilder", filter_sma=5,
                       entry_below=70, exit_kind="close_above_sma", exit_value=2,
                       add_below=None, max_units=1, unit_fraction=1.0)


def frame(closes):
    closes = np.asarray(closes, dtype=float)
    opens = np.concatenate([[closes[0]], closes[:-1]]) + 0.25
    return pd.DataFrame({
        "date": pd.bdate_range("2020-01-01", periods=len(closes)).strftime("%Y-%m-%d"),
        "adj_open": opens, "adj_high": np.maximum(opens, closes) + 1,
        "adj_low": np.minimum(opens, closes) - 1, "adj_close": closes,
        "volume": np.arange(len(closes)) * 100,
    })


CLOSES = [100, 102, 104, 106, 108, 110, 109, 107, 110, 112, 114, 113, 111, 114, 116, 118, 117, 115]


def replay(closes=CLOSES, **kw):
    f = frame(closes)
    return f, build_replay(f, RULE, cost_bps=kw.get("cost", 5.0), start=f["date"].iloc[0],
                           end=f["date"].iloc[-1])


def test_trades_are_exactly_the_engines_trades():
    f, r = replay()
    result = engine.simulate(f, RULE, cost_bps=5.0, start=f["date"].iloc[0], end=f["date"].iloc[-1])

    assert [(t["entry_date"], t["exit_date"]) for t in r["trades"]] == [
        (f["date"][t.entry_index], f["date"][t.exit_index]) for t in result.trades]
    assert [t["return"] for t in r["trades"]] == pytest.approx(
        [t.trade_return for t in result.trades], abs=1e-6)
    assert r["summary"]["trades"] == len(result.trades) > 0


def test_each_trade_fills_the_day_after_its_signal_with_a_reason():
    f, r = replay()
    dates = list(f["date"])
    for t in r["trades"]:
        assert dates.index(t["entry_date"]) == dates.index(t["signal_date"]) + 1
        assert t["entry_price"] == pytest.approx(f["adj_open"][dates.index(t["entry_date"])])
        assert t["why_entry"].startswith("RSI(2)") and "SMA5" in t["why_entry"]
        if not t["forced_close"]:
            assert dates.index(t["exit_date"]) == dates.index(t["exit_signal_date"]) + 1
            assert "SMA2" in t["why_exit"]


def test_bar_flags_match_the_signals_and_nan_warmup_is_null():
    f, r = replay()
    entry, exit_, _ = engine.build_signals(f["adj_close"], RULE)
    assert [b["entry_condition"] for b in r["bars"]] == list(entry)
    assert [b["exit_condition"] for b in r["bars"]] == list(exit_)
    assert r["bars"][0]["rsi"] is None and r["bars"][0]["sma_filter"] is None
    assert len(r["bars"]) == len(f) == len(r["equity"])


def test_an_open_trade_at_the_end_is_forced_closed_at_the_last_close():
    f, r = replay()
    assert len(r["trades"]) == 3
    last = r["trades"][-1]
    assert last["forced_close"] and last["exit_date"] == f["date"].iloc[-1]
    assert last["exit_price"] == pytest.approx(f["adj_close"].iloc[-1])
    assert last["exit_signal_date"] is None

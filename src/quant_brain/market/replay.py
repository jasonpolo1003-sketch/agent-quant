"""Trade replay: what a rule saw on every bar, and every trade it made.

For the terminal's chart page (PROP-010 phase 1). It re-runs the frozen engine
read-only over one period and returns, for each bar, the adjusted prices, the
rule's indicators and whether its entry and exit conditions were true, plus
each trade with the reason it fired. Nothing here changes a card or a result.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from quant_brain.backtest import engine
from quant_brain.backtest import indicators as ind

PRICE_NOTE = (
    "Prices are dividend-adjusted (Yahoo adj_close basis), so they read lower than the "
    "prices a charting site shows for past dates. Signals and fills use these prices."
)


def _num(value: float) -> float | None:
    return None if value is None or (isinstance(value, float) and math.isnan(value)) else round(
        float(value), 6)


def _reason(spec: engine.RuleSpec, rsi: float, close: float, trend: float | None) -> str:
    parts = [f"RSI({spec.rsi_period}) {rsi:.1f} < {spec.entry_below:g}"]
    if trend is not None:
        parts.append(f"close {close:.2f} > SMA{spec.filter_sma} {trend:.2f}")
    return " and ".join(parts)


def _exit_reason(spec: engine.RuleSpec, rsi: float, close: float, exit_sma: float | None) -> str:
    if spec.exit_kind == "close_above_sma":
        return f"close {close:.2f} > SMA{int(spec.exit_value)} {exit_sma:.2f}"
    return f"RSI({spec.rsi_period}) {rsi:.1f} > {spec.exit_value:g}"


def build_replay(
    frame: pd.DataFrame, spec: engine.RuleSpec, *, cost_bps: float, start: str, end: str,
) -> dict[str, Any]:
    """Bars, indicators, signal flags and trades for one rule over one period."""
    frame = frame.reset_index(drop=True)
    closes = frame["adj_close"].reset_index(drop=True)
    opens = frame["adj_open"].to_numpy(float)
    rsi = engine.indicator(closes, spec)
    trend = ind.sma(closes, spec.filter_sma) if spec.filter_sma else None
    exit_sma = ind.sma(closes, int(spec.exit_value)) if spec.exit_kind == "close_above_sma" else None
    entry, exit_, _add = engine.build_signals(closes, spec)
    p0, p1 = engine.period_bounds(frame["date"], start, end)
    result = engine.simulate(frame, spec, cost_bps=cost_bps, start=start, end=end)

    dates = frame["date"].astype(str)
    bars = []
    for t in range(p0, p1 + 1):
        bars.append({
            "date": dates[t],
            "open": _num(opens[t]),
            "high": _num(frame["adj_high"][t]),
            "low": _num(frame["adj_low"][t]),
            "close": _num(closes[t]),
            "volume": int(frame["volume"][t]) if "volume" in frame else None,
            "rsi": _num(rsi[t]),
            "sma_filter": _num(trend[t]) if trend is not None else None,
            "sma_exit": _num(exit_sma[t]) if exit_sma is not None else None,
            "entry_condition": bool(entry[t]),
            "exit_condition": bool(exit_[t]),
        })

    trades = []
    for number, trade in enumerate(result.trades, start=1):
        s, fill, out = trade.signal_index, trade.entry_index, trade.exit_index
        exit_signal = out if trade.forced else out - 1
        trades.append({
            "number": number,
            "signal_date": dates[s],
            "entry_date": dates[fill],
            "entry_price": _num(opens[fill]),
            "exit_signal_date": None if trade.forced else dates[exit_signal],
            "exit_date": dates[out],
            "exit_price": _num(closes[out] if trade.forced else opens[out]),
            "holding_days": trade.holding_days,
            "return": _num(trade.trade_return),
            "forced_close": trade.forced,
            "units": len(trade.unit_indices),
            "why_entry": _reason(spec, rsi[s], closes[s], trend[s] if trend is not None else None),
            "why_exit": ("period ended: closed at the last bar's close" if trade.forced else
                         _exit_reason(spec, rsi[exit_signal], closes[exit_signal],
                                      exit_sma[exit_signal] if exit_sma is not None else None)),
        })

    returns = np.array([t["return"] for t in trades], dtype=float)
    return {
        "rule_id": spec.rule_id,
        "period": [start, end],
        "cost_bps_per_side": cost_bps,
        "execution": "signal at a close, filled at the next day's open",
        "price_note": PRICE_NOTE,
        "indicators": {
            "rsi": f"RSI({spec.rsi_period}), {spec.rsi_method}",
            "sma_filter": f"SMA{spec.filter_sma}" if spec.filter_sma else None,
            "sma_exit": f"SMA{int(spec.exit_value)}" if exit_sma is not None else None,
        },
        "summary": {
            "trades": len(trades),
            "average_return": _num(returns.mean()) if len(returns) else None,
            "win_rate": _num((returns > 0).mean()) if len(returns) else None,
            "final_equity": _num(result.equity.iloc[-1]),
        },
        "bars": bars,
        "equity": [_num(v) for v in result.equity.to_numpy(float)],
        "trades": trades,
    }

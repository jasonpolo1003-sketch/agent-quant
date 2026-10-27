"""Intraday equity path of a day's trades, per contract, gross of costs (plan P2).

A prop account dies the moment equity *including open positions* touches the
loss limit, so we need each day's lowest point, not just its close. Rules for
1-minute bars:

- bars strictly inside a trade contribute their adverse extreme (low for longs,
  high for shorts) and their favourable extreme;
- the exit bar contributes the exit fill price as its adverse point: a stop
  fills at the stop (or the gap open), a flatten at the bar open, so price
  beyond the fill is never suffered;
- missing bars contribute nothing (the engine's stress bound covers them);
- with several trades, earlier realised P&L carries into later open P&L.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import time

from quant_brain.futures.orb import Bar, Trade, minute_span


def trade_extremes(bars: Mapping[time, Bar], trade: Trade, tick_cents: int) -> tuple[int, int]:
    """(worst open P&L, best open P&L) in cents per contract, both counted from entry."""
    side, entry = trade.side, trade.entry_ticks
    worst = best = 0
    for minute in minute_span(trade.entry_minute, trade.exit_minute):
        if minute == trade.exit_minute:
            adverse = trade.exit_ticks
            bar = bars.get(minute)
            if trade.exit_reason in ("flatten", "close", "gap_stop") or bar is None:
                favourable = trade.exit_ticks  # out at the bar open
            else:  # stopped inside this bar: its favourable extreme may have come first
                favourable = bar[1] if side > 0 else bar[2]
        else:
            bar = bars.get(minute)
            if bar is None:
                continue
            adverse = bar[2] if side > 0 else bar[1]
            favourable = bar[1] if side > 0 else bar[2]
        worst = min(worst, side * (adverse - entry))
        best = max(best, side * (favourable - entry))
    return worst * tick_cents, best * tick_cents


def day_path(bars: Mapping[time, Bar], trades: Sequence[Trade], tick_cents: int) -> tuple[int, int]:
    """(lowest equity, closing P&L) for the day in cents per contract, gross; low <= close."""
    realised = low = 0
    for trade in trades:
        worst, _ = trade_extremes(bars, trade, tick_cents)
        low = min(low, realised + worst)
        realised += trade.gross_cents
    return min(low, realised), realised


def flipped_path(worst: int, best: int, gross: int) -> tuple[int, int]:
    """Same single trade taken in the opposite direction: its worst is minus the original best."""
    return min(0, -best, -gross), -gross

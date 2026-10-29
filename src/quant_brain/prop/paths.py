"""Intraday equity path of a day's trades, per contract, gross of costs (plan P2).

A prop account dies the moment equity *including open positions* touches the
loss limit, so we need each day's lowest point, not just its close. Rules for
1-minute bars:

- bars strictly inside a trade contribute their adverse extreme (low for longs,
  high for shorts) and their favourable extreme;
- the exit bar contributes the exit fill price as its adverse point: a stop
  fills at the stop (or the gap open), a flatten at the bar open, so price
  beyond the fill is never suffered; a target filled inside a bar (resting
  limit) also counts that bar's adverse extreme, which may have come first;
- missing bars contribute nothing (the engine's stress bound covers them);
- with several trades, earlier realised P&L carries into later open P&L.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import time

from quant_brain.futures.orb import Bar, Trade, minute_span


def _minute_points(bars: Mapping[time, Bar], trade: Trade):
    """(minute, adverse, favourable) open P&L in ticks per contract, in time order."""
    side, entry = trade.side, trade.entry_ticks
    for minute in minute_span(trade.entry_minute, trade.exit_minute):
        if minute == trade.exit_minute:
            adverse = trade.exit_ticks
            bar = bars.get(minute)
            if (
                trade.exit_reason in ("flatten", "close", "gap_stop", "signal_exit", "gap_target")
                or bar is None
            ):
                favourable = trade.exit_ticks  # out at the bar open
            elif trade.exit_reason == "target":
                # limit filled inside this bar: its adverse extreme may have come first
                worst = bar[2] if side > 0 else bar[1]
                adverse = worst if side * (worst - trade.exit_ticks) < 0 else trade.exit_ticks
                favourable = trade.exit_ticks
            else:  # stopped inside this bar: its favourable extreme may have come first
                favourable = bar[1] if side > 0 else bar[2]
        else:
            bar = bars.get(minute)
            if bar is None:
                continue
            adverse = bar[2] if side > 0 else bar[1]
            favourable = bar[1] if side > 0 else bar[2]
        yield minute, side * (adverse - entry), side * (favourable - entry)


def trade_extremes(bars: Mapping[time, Bar], trade: Trade, tick_cents: int) -> tuple[int, int]:
    """(worst open P&L, best open P&L) in cents per contract, both counted from entry."""
    worst = best = 0
    for _, adverse, favourable in _minute_points(bars, trade):
        worst, best = min(worst, adverse), max(best, favourable)
    return worst * tick_cents, best * tick_cents


def day_records(
    bars: Mapping[time, Bar], trades: Sequence[Trade], tick_cents: int
) -> list[tuple[int, int]]:
    """Each minute that sets a new day low or high: (equity low, equity high) in that minute.

    Cents per contract, gross, in time order. Enough to tell which of an upper and
    a lower level the day's equity touched first (a minute touching both counts as
    adverse first). The smallest low equals `day_path`'s low.
    """
    realised = run_low = run_high = 0
    out: list[tuple[int, int]] = []
    for trade in trades:
        for _, adverse, favourable in _minute_points(bars, trade):
            lo, hi = realised + adverse * tick_cents, realised + favourable * tick_cents
            if lo < run_low or hi > run_high:
                out.append((lo, hi))
                run_low, run_high = min(run_low, lo), max(run_high, hi)
        realised += trade.gross_cents
    return out


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


def book_records(
    bars: Mapping[time, Bar], trades: Sequence[Trade], tick_cents: int
) -> list[tuple[int, int]]:
    """`day_records` for units that can be held at the same time (SC-FUT-0007 pyramids).

    Each minute: realised P&L of units already out plus every open unit's adverse and
    favourable point in that minute. One market, so a missing bar is missing for all.
    """
    points: dict[time, list[tuple[int, int]]] = {}
    for trade in trades:
        for minute, adverse, favourable in _minute_points(bars, trade):
            points.setdefault(minute, []).append((adverse, favourable))
    run_low = run_high = 0
    out: list[tuple[int, int]] = []
    for minute in sorted(points):
        realised = sum(x.gross_cents for x in trades if x.exit_minute < minute)
        lo = realised + sum(a for a, _ in points[minute]) * tick_cents
        hi = realised + sum(f for _, f in points[minute]) * tick_cents
        if lo < run_low or hi > run_high:
            out.append((lo, hi))
            run_low, run_high = min(run_low, lo), max(run_high, hi)
    return out


def book_path(
    bars: Mapping[time, Bar], trades: Sequence[Trade], tick_cents: int
) -> tuple[int, int]:
    """(lowest equity, closing P&L) for units held at the same time; low <= close."""
    close = sum(x.gross_cents for x in trades)
    low = min([0] + [lo for lo, _ in book_records(bars, trades, tick_cents)])
    return min(low, close), close

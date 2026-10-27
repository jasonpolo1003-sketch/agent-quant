"""SC-FUT-0001 rule engine: cash-open 15-minute ORB with the R2 ATR stop.

Implements the frozen spec `brain/_system/futures/sc-fut-0001-spec.v1.json`.
Prices are integer ticks, money is integer cents, minutes are America/Chicago
bar starts. Fixtures: `brain/_system/futures/orb-fixtures.md`.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from fractions import Fraction

Bar = tuple[int, int, int, int]  # open, high, low, close (ticks)

TICK_CENTS = {"MNQ": 50, "MES": 125}
L3_ROUND_TRIP_CENTS = {"MNQ": 322, "MES": 622}
RANGE_START = time(8, 30)
RANGE_BARS = 15
SIGNAL_START = time(8, 45)
ENTRY_CUTOFF = time(14, 30)
ATR_SESSIONS = 14


def add_minutes(minute: time, n: int) -> time:
    return (datetime.combine(date.min, minute) + timedelta(minutes=n)).time()


def minute_span(start: time, end: time) -> list[time]:
    """Minutes from start to end inclusive."""
    out, current = [], start
    while current <= end:
        out.append(current)
        current = add_minutes(current, 1)
    return out


def entry_cutoff(exit_minute: time) -> time:
    return min(ENTRY_CUTOFF, add_minutes(exit_minute, -1))


def true_range(session: Bar | tuple[int, int, int], prior_close: int) -> int:
    high, low = session[0], session[1]
    return max(high - low, abs(high - prior_close), abs(low - prior_close))


def true_range_sum(sessions: Sequence[tuple[int, int, int] | None]) -> int | None:
    """Sum of the 14 true ranges from 15 prior sessions (high, low, close), oldest first."""
    if len(sessions) != ATR_SESSIONS + 1 or any(s is None for s in sessions):
        return None
    return sum(true_range(sessions[i], sessions[i - 1][2]) for i in range(1, len(sessions)))


def stop_from_sum(total: int, fraction: Fraction = Fraction(1, 10)) -> int:
    """fraction x (total / 14) ticks, exact half rounds up, minimum one tick."""
    return max(1, math.floor(Fraction(total) * fraction / ATR_SESSIONS + Fraction(1, 2)))


def stop_distance_ticks(sessions: Sequence[tuple[int, int, int] | None]) -> int | None:
    """0.10 x mean of 14 true ranges, half-up to a tick, minimum one (frozen SC-FUT-0001).

    `sessions` are the 15 prior NYSE sessions (high, low, regular-hours close),
    oldest first; the first supplies only the prior close. Any gap -> None.
    """
    total = true_range_sum(sessions)
    return None if total is None else stop_from_sum(total)


@dataclass(frozen=True)
class DayInput:
    trade_date: date
    root: str
    bars: Mapping[time, Bar]
    exit_minute: time
    stop_ticks: int | None
    atr_tr_sum: int | None = None  # sum of the 14 prior true ranges, for other stop fractions
    prev_close: int | None = None  # previous NYSE session's regular close, same contract
    context: Mapping | None = None  # strategy-specific point-in-time inputs (e.g. scales)
    volumes: Mapping | None = None  # 1-minute volume by bar start (for VWAP)


@dataclass(frozen=True)
class Trade:
    side: int  # +1 long, -1 short
    signal_minute: time | None
    entry_minute: time
    entry_ticks: int
    stop_level_ticks: int
    exit_minute: time
    exit_ticks: int
    exit_reason: str  # stop | gap_stop | flatten
    gross_cents: int
    net_cents: int
    entry_bar_stop: bool
    gap_affected: bool
    stress_exit_ticks: int | None
    stress_net_cents: int


@dataclass(frozen=True)
class DayResult:
    trade_date: date
    root: str
    status: str  # traded | no_trade | void_range | ineligible | non_evaluable
    net_cents: int
    stress_net_cents: int
    trades: list[Trade] = field(default_factory=list)
    events: list[tuple[str, time]] = field(default_factory=list)


def _net(root: str, side: int, entry: int, exit_: int) -> tuple[int, int]:
    gross = side * (exit_ - entry) * TICK_CENTS[root]
    return gross, gross - L3_ROUND_TRIP_CENTS[root]


def run_trade(
    bars: Mapping[time, Bar],
    *,
    root: str,
    side: int,
    entry_minute: time,
    stop_ticks: int,
    exit_minute: time,
    signal_minute: time | None = None,
) -> Trade | None:
    """Enter at `entry_minute`'s open; None if the flatten bar is missing (non-evaluable)."""
    entry = bars[entry_minute][0]
    stop = entry - side * stop_ticks
    gap_seen = False
    stress_exit: int | None = None
    exit_at, exit_px, reason = None, None, "flatten"
    for minute in minute_span(entry_minute, add_minutes(exit_minute, -1)):
        bar = bars.get(minute)
        if bar is None:
            gap_seen = True
            continue
        open_, high, low, _ = bar
        adverse = low if side > 0 else high
        if gap_seen and stress_exit is None:
            stress_exit = min(stop, adverse) if side > 0 else max(stop, adverse)
        if side * (open_ - stop) <= 0:
            exit_at, exit_px, reason = minute, open_, "gap_stop"
            break
        if side * (adverse - stop) <= 0:
            exit_at, exit_px, reason = minute, stop, "stop"
            break
    if exit_at is None:
        flatten_bar = bars.get(exit_minute)
        # Missing flatten, or a gap with no visible bar before the flatten: non-evaluable.
        if flatten_bar is None or (gap_seen and stress_exit is None):
            return None
        exit_at, exit_px = exit_minute, flatten_bar[0]
    if stress_exit is not None:
        # The bound is never less adverse than the observed primary exit.
        stress_exit = min(stress_exit, exit_px) if side > 0 else max(stress_exit, exit_px)
    gross, net = _net(root, side, entry, exit_px)
    stress_net = _net(root, side, entry, stress_exit)[1] if stress_exit is not None else net
    return Trade(
        side=side,
        signal_minute=signal_minute,
        entry_minute=entry_minute,
        entry_ticks=entry,
        stop_level_ticks=stop,
        exit_minute=exit_at,
        exit_ticks=exit_px,
        exit_reason=reason,
        gross_cents=gross,
        net_cents=net,
        entry_bar_stop=exit_at == entry_minute,
        gap_affected=gap_seen,
        stress_exit_ticks=stress_exit,
        stress_net_cents=stress_net,
    )


def simulate_day(day: DayInput, *, range_bars: int = RANGE_BARS) -> DayResult:
    def result(status: str, trades=(), events=()) -> DayResult:
        trades = list(trades)
        return DayResult(
            trade_date=day.trade_date,
            root=day.root,
            status=status,
            net_cents=sum(tr.net_cents for tr in trades),
            stress_net_cents=sum(tr.stress_net_cents for tr in trades),
            trades=trades,
            events=list(events),
        )

    if day.stop_ticks is None or not day.bars:
        return result("ineligible")  # no ATR history, or no bars in the cash window
    range_minutes = minute_span(RANGE_START, add_minutes(RANGE_START, range_bars - 1))
    if any(m not in day.bars for m in range_minutes):
        return result("void_range")
    high = max(day.bars[m][1] for m in range_minutes)
    low = min(day.bars[m][2] for m in range_minutes)
    assert high >= low

    cutoff = entry_cutoff(day.exit_minute)
    used: set[int] = set()
    trades: list[Trade] = []
    events: list[tuple[str, time]] = []
    minute = add_minutes(RANGE_START, range_bars)  # first bar after the range
    while minute < cutoff:
        bar = day.bars.get(minute)
        side = 0 if bar is None else 1 if bar[3] > high else -1 if bar[3] < low else 0
        if side == 0 or side in used:
            minute = add_minutes(minute, 1)
            continue
        used.add(side)
        fill = add_minutes(minute, 1)
        if fill not in day.bars:
            events.append(("entry_missing", fill))
            minute = fill
            continue
        trade = run_trade(
            day.bars,
            root=day.root,
            side=side,
            entry_minute=fill,
            stop_ticks=day.stop_ticks,
            exit_minute=day.exit_minute,
            signal_minute=minute,
        )
        if trade is None:
            return result("non_evaluable", trades, events)
        trades.append(trade)
        minute = add_minutes(trade.exit_minute, 1)
    return result("traded" if trades else "no_trade", trades, events)

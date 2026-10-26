"""Independent reference implementation of SC-FUT-0001, for cross-checking `orb.py`.

Written separately on purpose: one forward pass over every minute with an
explicit state machine, Decimal arithmetic for the ATR, and no helpers shared
with the engine beyond the input and output record types.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from quant_brain.futures.orb import DayInput, DayResult, Trade

_TICK = {"MNQ": 50, "MES": 125}
_COST = {"MNQ": 322, "MES": 622}


def stop_distance_ticks(sessions):
    if len(sessions) != 15 or None in sessions:
        return None
    ranges = []
    for previous, current in zip(sessions, sessions[1:], strict=False):
        prior_close = previous[2]
        ranges.append(
            max(
                current[0] - current[1],
                abs(current[0] - prior_close),
                abs(current[1] - prior_close),
            )
        )
    atr = Decimal(sum(ranges)) / Decimal(len(ranges))
    distance = (atr * Decimal("0.10")).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    return max(1, int(distance))


@dataclass
class _Open:
    side: int
    signal: object
    entry_minute: object
    entry: int
    stop: int
    gap: bool = False
    stress: int | None = None


def _close(root, position, minute, price, reason) -> Trade:
    gross = (price - position.entry) * position.side * _TICK[root]
    stress_price = position.stress if position.stress is not None else price
    return Trade(
        side=position.side,
        signal_minute=position.signal,
        entry_minute=position.entry_minute,
        entry_ticks=position.entry,
        stop_level_ticks=position.stop,
        exit_minute=minute,
        exit_ticks=price,
        exit_reason=reason,
        gross_cents=gross,
        net_cents=gross - _COST[root],
        entry_bar_stop=minute == position.entry_minute,
        gap_affected=position.gap,
        stress_exit_ticks=position.stress,
        stress_net_cents=(stress_price - position.entry) * position.side * _TICK[root]
        - _COST[root],
    )


def simulate_day(day: DayInput) -> DayResult:
    root = day.root
    if day.stop_ticks is None:
        return DayResult(day.trade_date, root, "ineligible", 0, 0, [], [])

    anchor = datetime(2000, 1, 1, 8, 30)
    clock = [(anchor + timedelta(minutes=i)).time() for i in range(15)]
    if not all(m in day.bars for m in clock):
        return DayResult(day.trade_date, root, "void_range", 0, 0, [], [])
    range_high = max(day.bars[m][1] for m in clock)
    range_low = min(day.bars[m][2] for m in clock)

    last = datetime.combine(anchor.date(), day.exit_minute)
    cutoff = min(datetime(2000, 1, 1, 14, 30), last - timedelta(minutes=1))
    trades: list[Trade] = []
    events = []
    used_long = used_short = False
    position: _Open | None = None
    pending = None  # (side, signal minute) awaiting next-minute fill
    exit_bar = None

    now = anchor + timedelta(minutes=15)
    while now <= last:
        minute = now.time()
        bar = day.bars.get(minute)

        if pending is not None:
            side, signal = pending
            pending = None
            if bar is None:
                events.append(("entry_missing", minute))
            else:
                position = _Open(side, signal, minute, bar[0], bar[0] - side * day.stop_ticks)

        if now == last:
            if position is not None:
                if bar is None:
                    # Completed trades stay on the record; the day itself is excluded by status.
                    return DayResult(
                        day.trade_date,
                        root,
                        "non_evaluable",
                        sum(tr.net_cents for tr in trades),
                        sum(tr.stress_net_cents for tr in trades),
                        trades,
                        events,
                    )
                if position.gap and position.stress is None:
                    adverse = bar[2] if position.side == 1 else bar[1]
                    position.stress = (
                        min(position.stop, adverse)
                        if position.side == 1
                        else max(position.stop, adverse)
                    )
                trades.append(_close(root, position, minute, bar[0], "flatten"))
            break

        if position is not None:
            if bar is None:
                position.gap = True
            else:
                o, h, low, _ = bar
                if position.gap and position.stress is None:
                    adverse = low if position.side == 1 else h
                    position.stress = (
                        min(position.stop, adverse)
                        if position.side == 1
                        else max(position.stop, adverse)
                    )
                if position.side == 1 and o <= position.stop:
                    trades.append(_close(root, position, minute, o, "gap_stop"))
                    position, exit_bar = None, minute
                elif position.side == 1 and low <= position.stop:
                    trades.append(_close(root, position, minute, position.stop, "stop"))
                    position, exit_bar = None, minute
                elif position.side == -1 and o >= position.stop:
                    trades.append(_close(root, position, minute, o, "gap_stop"))
                    position, exit_bar = None, minute
                elif position.side == -1 and h >= position.stop:
                    trades.append(_close(root, position, minute, position.stop, "stop"))
                    position, exit_bar = None, minute
        elif bar is not None and minute != exit_bar and now < cutoff:
            close = bar[3]
            if close > range_high and not used_long:
                used_long, pending = True, (1, minute)
            elif close < range_low and not used_short:
                used_short, pending = True, (-1, minute)
        now += timedelta(minutes=1)

    status = "traded" if trades else "no_trade"
    return DayResult(
        day.trade_date,
        root,
        status,
        sum(tr.net_cents for tr in trades),
        sum(tr.stress_net_cents for tr in trades),
        trades,
        events,
    )

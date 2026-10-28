"""Evaluation-account state machine (plan P3). Pure functions, dollars, one row per day.

Per day: if equity at the day's lowest point (balance + day low) touches the
trailing floor, the account fails (failure wins any same-day target, fixture
F4) and is reset next day for a fee. Otherwise the close is booked, the floor
trails the highest end-of-day balance (locking at the start balance), and the
target is checked on the end-of-day balance, raised by the consistency rule.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Rules:
    start: float = 50_000
    target: float = 3_000
    max_loss: float = 2_000
    lock_at_start: bool = True
    trailing: bool = True
    consistency: float | None = 0.55
    subscription: float = 49
    reset: float = 49
    days_per_month: int = 21

    @classmethod
    def from_json(cls, path: Path) -> Rules:
        c = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            start=c["start_balance_usd"],
            target=c["profit_target_usd"],
            max_loss=c["max_loss_limit_usd"],
            lock_at_start=c["max_loss_limit_locks_at_start_balance"],
            consistency=c["consistency_best_day_max_share"],
            subscription=c["subscription_usd_per_month"],
            reset=c["reset_usd"],
            days_per_month=c["trading_days_per_month"],
        )


@dataclass(frozen=True)
class Outcome:
    passed: bool
    days: int  # trading days used (to the pass, or the whole horizon)
    resets: int
    fees: float
    censored: bool  # data ran out before a pass or the horizon end


# (day index, cushion = equity - floor at the open) -> that day's (close, low) in dollars
DayPnl = Callable[[int, float], tuple[float, float]]


def attempt(
    closes: Sequence[float],
    lows: Sequence[float],
    rules: Rules,
    horizon: int,
    pnl: DayPnl | None = None,
) -> Outcome:
    """Run one funded attempt over up to `horizon` days of (close, low) day P&L in dollars.

    With `pnl`, each day's P&L comes from it instead (so size can follow the account);
    `closes` then only sets how many days there are.
    """
    balance, peak = rules.start, rules.start
    floor = rules.start - rules.max_loss
    best_day = 0.0
    resets = 0
    fees = rules.subscription
    days = min(horizon, len(closes))
    for day in range(days):
        if day and day % rules.days_per_month == 0:
            fees += rules.subscription
        close, low = pnl(day, balance - floor) if pnl else (closes[day], lows[day])
        if balance + min(low, close) <= floor:
            resets += 1
            fees += rules.reset
            balance, peak, floor, best_day = (
                rules.start,
                rules.start,
                rules.start - rules.max_loss,
                0.0,
            )
            continue
        balance += close
        best_day = max(best_day, close)
        if rules.trailing and balance > peak:
            peak = balance
            floor = peak - rules.max_loss
            if rules.lock_at_start:
                floor = min(floor, rules.start)
        profit = balance - rules.start
        needed = rules.target
        if rules.consistency and best_day > rules.consistency * profit:
            needed = max(needed, best_day / rules.consistency)
        if profit >= needed:
            return Outcome(True, day + 1, resets, fees, False)
    return Outcome(False, days, resets, fees, len(closes) < horizon)

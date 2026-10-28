"""Funded account (XFA), payouts and the whole Combine -> XFA lifecycle (Phase 2, Q2-Q4).

Pure functions over day (close, low) P&L in dollars, like `account.attempt`.

XFA, per day: if equity at the day's lowest point touches the floor the account is
closed. Otherwise the close is booked; the floor trails the highest end-of-day
balance, locks at $0 once the balance reaches the loss limit, and is $0 for good
after a payout. A payout is requested at the end of the first eligible day for
min(50% of balance, cap) and the trader keeps 90%.

Lifecycle: Combine (with resets) -> activation -> XFA -> payouts until the XFA is
closed, then a new Combine, until the horizon. Net cash = trader payouts - fees.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

from quant_brain.prop.account import DayPnl, Rules, attempt


@dataclass(frozen=True)
class XfaRules:
    path: str = "standard"  # or "consistency"; fixed at activation
    max_loss: float = 2_000
    split: float = 0.9
    min_payout: float = 125
    payout_share: float = 0.5
    cap: float = 2_000
    winning_days: int = 5  # standard path
    winning_day_min: float = 150
    trading_days: int = 3  # consistency path
    largest_day_share: float = 0.40
    activation: float = 149

    @classmethod
    def from_json(cls, path: Path, payout_path: str, *, dll: bool, activation: float) -> XfaRules:
        c = json.loads(path.read_text(encoding="utf-8"))
        p = c["paths"][payout_path]
        return cls(
            path=payout_path,
            max_loss=c["max_loss_limit_usd"],
            split=c["profit_split_trader"],
            min_payout=c["min_payout_usd"],
            payout_share=c["payout_share_of_balance"],
            cap=p["cap_with_dll_usd"] if dll else p["cap_usd"],
            winning_days=p.get("winning_days", cls.winning_days),
            winning_day_min=p.get("winning_day_min_usd", cls.winning_day_min),
            trading_days=p.get("trading_days", cls.trading_days),
            largest_day_share=p.get("largest_day_max_share", cls.largest_day_share),
            activation=activation,
        )


def plan_rules(combine_json: Path, plan: str) -> tuple[Rules, float]:
    """Combine rules with one pricing plan's fees, and that plan's XFA activation fee."""
    c = json.loads(combine_json.read_text(encoding="utf-8"))
    p = c["plans"][plan]
    rules = replace(
        Rules.from_json(combine_json),
        subscription=p["subscription_usd_per_month"],
        reset=p["reset_usd"],
    )
    return rules, p["xfa_activation_usd"]


def apply_dll(closes: np.ndarray, lows: np.ndarray, limit: float, slip: float = 0.0):
    """Daily loss limit: a day whose low reaches -limit is flattened there and stops.

    The day low is the first point the limit could trigger, so the day ends at
    -(limit + slip) and nothing after it counts. Not a rule violation.
    """
    hit = lows <= -limit
    out = -(limit + slip)
    return np.where(hit, out, closes), np.where(hit, np.minimum(lows, out), lows)


@dataclass(frozen=True)
class XfaOutcome:
    days: int  # trading days used
    paid: tuple[float, ...]  # gross payout amounts, in order
    payout_days: tuple[int, ...]  # 1-based day of each payout
    closed: bool  # the loss limit was touched


def _eligible(r: XfaRules, since: list[float], traded: list[bool], first: bool) -> bool:
    profit = sum(since)
    if r.path == "standard":
        wins = sum(d >= r.winning_day_min for d in since)
        return wins >= r.winning_days and (first or profit > 0)
    days = sum(traded)
    return days >= r.trading_days and profit > 0 and max(since) <= r.largest_day_share * profit


def xfa(
    closes: Sequence[float],
    lows: Sequence[float],
    r: XfaRules,
    horizon: int,
    traded: Sequence[bool] | None = None,
    pnl: DayPnl | None = None,
) -> XfaOutcome:
    """Run one funded account over up to `horizon` days (balance starts at $0).

    `pnl` works as in `account.attempt`.
    """
    balance = peak = 0.0
    floor = -r.max_loss
    paid: list[float] = []
    payout_days: list[int] = []
    since: list[float] = []
    since_traded: list[bool] = []
    days = min(horizon, len(closes))
    for day in range(days):
        close, low = pnl(day, balance - floor) if pnl else (closes[day], lows[day])
        if balance + min(low, close) <= floor:
            return XfaOutcome(day + 1, tuple(paid), tuple(payout_days), True)
        balance += close
        since.append(close)
        since_traded.append(bool(traded[day]) if traded is not None else (close != 0 or low != 0))
        if not paid and balance > peak:
            peak = balance
            floor = min(peak - r.max_loss, 0.0)
        if _eligible(r, since, since_traded, first=not paid):
            amount = min(r.payout_share * balance, r.cap)
            if amount >= r.min_payout:
                balance -= amount
                paid.append(amount)
                payout_days.append(day + 1)
                floor = 0.0
                since, since_traded = [], []
    return XfaOutcome(days, tuple(paid), tuple(payout_days), False)


@dataclass(frozen=True)
class CashOutcome:
    net: float  # trader payouts - all fees
    payouts: float  # trader share
    fees: float
    combines_passed: int
    xfas_closed: int
    first_payout_day: int | None  # 1-based, from the start of the horizon


# (day index from the start of the horizon, cushion, "combine" | "xfa") -> (close, low)
PhasePnl = Callable[[int, float, str], tuple[float, float]]


def lifecycle(
    closes: Sequence[float],
    lows: Sequence[float],
    combine: Rules,
    r: XfaRules,
    horizon: int,
    pnl: PhasePnl | None = None,
) -> CashOutcome:
    """Combine -> XFA -> payouts, restarting with a new Combine after an XFA closes.

    With `pnl`, day P&L comes from it (size and in-day rules can follow the account).
    """

    def phase(start: int, name: str) -> DayPnl | None:
        return (lambda d, cushion: pnl(start + d, cushion, name)) if pnl else None

    day, fees, payouts = 0, 0.0, 0.0
    passed = closed = 0
    first_payout = None
    end = min(horizon, len(closes))
    while day < end:
        c = attempt(closes[day:end], lows[day:end], combine, end - day, phase(day, "combine"))
        fees += c.fees
        day += c.days
        if not c.passed:
            break
        passed += 1
        fees += r.activation
        x = xfa(closes[day:end], lows[day:end], r, end - day, pnl=phase(day, "xfa"))
        if x.payout_days and first_payout is None:
            first_payout = day + x.payout_days[0]
        payouts += r.split * sum(x.paid)
        day += x.days
        closed += x.closed
    return CashOutcome(payouts - fees, payouts, fees, passed, closed, first_payout)

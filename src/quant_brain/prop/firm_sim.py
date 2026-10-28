"""Generic evaluation and funded state machines for any `firms.Firm` (plan E1).

Pure functions in dollars, one day at a time; generalise `account.attempt` and
`funded.xfa`/`funded.lifecycle`, and reproduce them exactly for Topstep 50K
(tests/test_prop_firms.py runs both on the same days).

A day is a `DayPath` from a day function, asked each morning with a `DayContext`
(phase, cushion, profit still needed), so size and in-day stops can follow the
account. Per day, in order:
1. Breach: equity at the day low (balance + min(low, close)) <= floor; or, with an
   intraday-trailing floor, the day's give-back from its running high >= max loss
   (see below); or a hard daily loss: min(low, close) <= -limit (the low up to the
   trader's own exit, `stop_low`). A breach wins any same-day target or payout.
   Evaluation: reset next day for the reset fee. Funded: the account is closed.
2. Book the close. Soft daily losses are not checked here: the day function has
   already flattened the day at -limit (it knows size and slippage).
3. Move the floor: EOD trailing to (highest end-of-day balance - max loss);
   intraday trailing to (highest intraday equity - max loss); both capped at
   start + lock; static never.
4. Evaluation: pass at the close if profit >= target (raised to best day / share
   by a consistency rule) and the minimum trading days are met. Funded: pay out at
   the end of the first eligible day (`_eligible`, and balance - start >= min_balance if
   set), min(share x (balance - start - buffer, or the cycle's profit - buffer with
   payout_base "cycle"), max_cycle_multiple x cycle profit, cap) if >= the minimum (with a
   min_balance, clipped to stay FLOOR_MARGIN above the post-payout floor); then the floor moves to start + floor_after_payout
   and stops trailing (or, if unset, stays where it was and keeps trailing from the
   lower balance), and the since-payout counters restart.

Intraday trailing with only (close, low, high) per day. The floor at minute t is
min(L, max(F, B + H_t - M)) (F: floor at the open, B: open balance, H_t: running
high incl. the open, M: max loss, L: lock level). Equity B + l_t breaches iff
B + l_t <= F, or (H_t - l_t >= M and B + l_t <= L). The day's give-back
D = max_t (H_t - l_t) is exact from the minute records (policy.Days.extremes,
counting a minute's high before its low: conservative). The second test uses the
day low in place of l_t at the give-back minute, so it can only add breaches.
Without records the array path assumes the high came before the low (D = high -
min(low, close)); intraday-trailing firms refuse arrays without highs.

Fees: the evaluation price on the first day of each attempt and, if billed
monthly, every 21 trading days of that attempt (a new account with no reset
product restarts the clock); a reset fee per failure (or the full price if
there is no reset); the activation fee per pass; the platform fee for every month
the run touches (ceil(days / 21)).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from quant_brain.prop.account import Outcome
from quant_brain.prop.firms import Firm, months
from quant_brain.prop.funded import CashOutcome, XfaOutcome


@dataclass(frozen=True)
class DayPath:
    close: float
    low: float  # lowest equity until the day's exit (play.day_fn; the old path kept later lows)
    high: float  # highest equity of the day, >= 0 (the open)
    drawdown: float  # largest give-back from the running high
    stop_low: float | None = None  # lowest equity until the trader's own exit (None: = low)


@dataclass(frozen=True)
class DayContext:
    phase: str  # "eval" | "funded"
    day: int  # index from the start of the horizon
    cushion: float  # equity - floor at the open
    to_target: float | None  # eval: profit still needed to pass at today's close (if allowed)


DayFn = Callable[[DayContext], DayPath]

FLOOR_MARGIN = 1.0  # dollars a clipped payout leaves above the post-payout floor


def array_days(
    firm: Firm,
    closes: Sequence[float],
    lows: Sequence[float],
    highs: Sequence[float] | None = None,
    drawdowns: Sequence[float] | None = None,
) -> DayFn:
    """Day function over fixed (close, low[, high, give-back]) arrays, indexed by ctx.day.

    A soft daily loss flattens a day at exactly -limit (no slippage: the policy path
    adds it). Without highs, high = max(0, close); give-back = high - min(low, close).
    """
    phases = [r for r in (firm.evaluation, firm.funded) if r is not None]
    if highs is None and any(r.drawdown == "intraday_trailing" for r in phases):
        raise ValueError("an intraday-trailing firm needs day highs (or minute records)")
    soft = {"eval": _soft(firm.evaluation), "funded": _soft(firm.funded)}

    def fn(ctx: DayContext) -> DayPath:
        close, low = closes[ctx.day], lows[ctx.day]
        hi = max(0.0, close) if highs is None else max(0.0, highs[ctx.day], close)
        dd = hi - min(low, close) if drawdowns is None else drawdowns[ctx.day]
        limit = soft[ctx.phase]
        if limit is not None and low <= -limit:
            out = -(limit + 0.0)
            close, low = out, min(low, out)
        return DayPath(close, low, hi, dd)

    return fn


def _soft(r) -> float | None:
    return r.daily_loss if r is not None and r.daily_loss_kind == "soft_pause" else None


def _traded(p: DayPath) -> bool:
    return p.close != 0 or p.low != 0


def _breached(r, p: DayPath, balance: float, floor: float, lock: float | None, trailing: bool):
    worst = min(p.low, p.close) if r.breach_intraday else p.close
    if balance + worst <= floor:
        return True
    if trailing and r.drawdown == "intraday_trailing" and p.drawdown >= r.max_loss:
        if lock is None or balance + worst <= lock:
            return True
    if r.daily_loss_kind == "hard_fail":
        low = p.low if p.stop_low is None else p.stop_low
        if min(low, p.close) <= -r.daily_loss:
            return True
    return False


def _trail(r, peak: float, floor: float, open_balance: float, balance: float, p: DayPath, lock):
    """New (peak, floor) after the day; the floor never moves down."""
    level = balance if r.drawdown == "eod_trailing" else open_balance + p.high
    if level > peak:
        peak = level
        floor = peak - r.max_loss
        if lock is not None:
            floor = min(floor, lock)
    return peak, floor


def _needed(r, best: float, profit: float) -> float:
    needed = r.target
    if r.consistency and best > r.consistency * profit:
        needed = max(needed, best / r.consistency)
    return needed


def evaluation(firm: Firm, day: DayFn, n_days: int, horizon: int, first: int = 0) -> Outcome:
    """One evaluation attempt (with resets) from day index `first`, like `account.attempt`."""
    r, f = firm.evaluation, firm.fees
    if r is None:
        raise ValueError(f"{firm.name} has no evaluation")
    lock = None if r.lock is None else r.start + r.lock
    trailing = r.drawdown != "static"
    balance = peak = r.start
    floor = r.start - r.max_loss
    best, traded, resets, clock = 0.0, 0, 0, 0
    fees = f.price
    days = min(horizon, n_days)
    for i in range(days):
        if f.billing == "monthly" and i > clock and (i - clock) % f.days_per_month == 0:
            fees += f.price
        profit = balance - r.start
        to_target = _needed(r, best, profit) - profit if traded + 1 >= r.min_days else None
        p = day(DayContext("eval", first + i, balance - floor, to_target))
        if _breached(r, p, balance, floor, lock, trailing):
            resets += 1
            if f.reset is not None:
                fees += f.reset
            else:  # a new account at full price; a monthly bill restarts tomorrow
                fees += f.price
                clock = i + 1
            balance, peak, floor, best, traded = r.start, r.start, r.start - r.max_loss, 0.0, 0
            continue
        open_balance = balance
        balance += p.close
        best = max(best, p.close)
        traded += _traded(p)
        if trailing:
            peak, floor = _trail(r, peak, floor, open_balance, balance, p, lock)
        profit = balance - r.start
        if profit >= _needed(r, best, profit) and traded >= r.min_days:
            return Outcome(True, i + 1, resets, fees, False)
    return Outcome(False, days, resets, fees, n_days < horizon)


def _eligible(r, since: list[float], traded: list[bool], every: list[float], k: int) -> bool:
    """Payout number k (0-based) allowed today? `since`: closes since the last payout;
    `every`: closes since the account started (for the total / best-ever consistency)."""
    profit = sum(since)
    if r.winning_days and sum(d >= r.winning_day_min for d in since) < r.winning_days:
        return False
    if r.trading_days and sum(traded) < r.trading_days:
        return False
    if r.needs_profit == "always" or (r.needs_profit == "after_first" and k > 0):
        if not profit > 0:
            return False
    goal = r.min_profit_at(k)
    if goal is not None and profit < goal:
        return False
    share = r.consistency_at(k)
    if share is None:
        return True
    if r.consistency_scope == "total":
        largest, base = max(every), sum(every)
    else:
        largest, base = (max(since) if r.consistency_scope == "cycle" else max(every)), profit
    return base > 0 and largest <= share * base


def funded_account(firm: Firm, day: DayFn, n_days: int, horizon: int, first: int = 0) -> XfaOutcome:
    """One funded account from day index `first`, like `funded.xfa`."""
    r = firm.funded
    lock = None if r.lock is None else r.start + r.lock
    trailing = r.drawdown != "static"
    balance = peak = r.start
    floor = r.start - r.max_loss
    paid: list[float] = []
    payout_days: list[int] = []
    since: list[float] = []
    since_traded: list[bool] = []
    every: list[float] = []
    days = min(horizon, n_days)
    for i in range(days):
        p = day(DayContext("funded", first + i, balance - floor, None))
        if _breached(r, p, balance, floor, lock, trailing):
            return XfaOutcome(i + 1, tuple(paid), tuple(payout_days), True)
        open_balance = balance
        balance += p.close
        since.append(p.close)
        since_traded.append(_traded(p))
        every.append(p.close)
        if trailing:
            peak, floor = _trail(r, peak, floor, open_balance, balance, p, lock)
        if _eligible(r, since, since_traded, every, len(paid)) and (
            r.min_balance is None or balance - r.start >= r.min_balance
        ):
            base = sum(since) if r.payout_base == "cycle" else balance - r.start
            amount = r.payout_share * (base - r.buffer)
            if r.max_cycle_multiple is not None:
                amount = min(amount, r.max_cycle_multiple * sum(since))
            cap = r.cap_at(len(paid))
            if cap is not None:
                amount = min(amount, cap)
            after = floor if r.floor_after_payout is None else r.start + r.floor_after_payout
            if r.min_balance is not None:  # a capped request can't take the balance to the floor
                amount = min(amount, balance - after - FLOOR_MARGIN)
            if amount >= r.min_payout and balance - amount > after:
                balance -= amount
                paid.append(amount)
                payout_days.append(i + 1)
                since, since_traded = [], []
                if r.floor_after_payout is not None:
                    floor, trailing = r.start + r.floor_after_payout, False
                else:
                    peak -= amount
                if r.max_payouts is not None and len(paid) >= r.max_payouts:
                    return XfaOutcome(i + 1, tuple(paid), tuple(payout_days), False)
    return XfaOutcome(days, tuple(paid), tuple(payout_days), False)


def lifecycle(firm: Firm, day: DayFn, n_days: int, horizon: int) -> CashOutcome:
    """Evaluation -> activation -> funded -> payouts, a new evaluation after a funded
    account ends, until the horizon. Net cash = trader payouts - all fees.

    Without an evaluation each funded account is bought at the price (and counted in
    `combines_passed`). The platform fee is charged for ceil(days run / 21) months.
    """
    at, fees, payouts = 0, 0.0, 0.0
    passed = closed = 0
    first_payout = None
    end = min(horizon, n_days)
    while at < end:
        if firm.evaluation is None:  # bought funded: the price per account, no evaluation
            fees += firm.fees.price
        else:
            c = evaluation(firm, day, end - at, end - at, at)
            fees += c.fees
            at += c.days
            if not c.passed:
                break
        passed += 1
        fees += firm.fees.activation
        x = funded_account(firm, day, end - at, end - at, at)
        if x.payout_days and first_payout is None:
            first_payout = at + x.payout_days[0]
        payouts += firm.funded.split * sum(x.paid)
        at += x.days
        closed += x.closed
    if firm.fees.platform_per_month:
        fees += firm.fees.platform_per_month * months(end, firm.fees.days_per_month)
    return CashOutcome(payouts - fees, payouts, fees, passed, closed, first_payout)


def lifecycle_arrays(
    firm: Firm,
    closes: Sequence[float],
    lows: Sequence[float],
    highs: Sequence[float] | None = None,
    drawdowns: Sequence[float] | None = None,
    *,
    horizon: int,
) -> CashOutcome:
    """`lifecycle` over fixed day arrays (same days in both phases)."""
    return lifecycle(firm, array_days(firm, closes, lows, highs, drawdowns), len(closes), horizon)

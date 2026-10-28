"""SC-FUT-0005 driven bar by bar: the noise.py rule as an incremental engine.

Frozen rules: brain/_system/futures/sc-fut-0005-spec.v1.json. The batch rule is
`workbench.noise.NoiseArea._legs`; this module must give the same legs. It reuses noise.py's
session table (`_session`), its move function (`NoiseArea._moves`, for the sigma table) and its
Trade builder (`NoiseArea._trade`); only the per-check decision is restated (`decide`), because
noise.py keeps it inline. Equivalence is proven by tests/test_live_engine.py (hand-worked days
and random synthetic days) and by scripts/live_replay_check.py (every practice day, MNQ).

Timing. A bar is keyed by its CT start minute and arrives when it closes. When the bar
starting at check-1 arrives (i.e. at the HH:00/HH:30 check), the engine decides at once and
emits a Signal carrying the Order to send now; noise.py fills it at the open of the
check-minute bar. The next bar confirms the model fill at its open (ModelFill); if the next bar
is not the check-minute bar (the minute had no trades), the check is voided, exactly as
noise.py skips a check whose fill bar is missing (Void; in live trading a sent market order
normally creates that bar, so a Void is a reconciliation event for the runner).
The flatten order is emitted when the bar before the flatten minute arrives; a missing flatten
bar makes the day non-evaluable, as in noise.py.

Prices are integer ticks, volumes are 1-minute contract counts, minutes are CT bar starts.
Positions are units of +1/0/-1; the runner scales them to contracts.
"""

from __future__ import annotations

import dataclasses
from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, time
from types import SimpleNamespace

import numpy as np

from quant_brain.futures.orb import DayInput, Trade
from quant_brain.workbench.noise import NoiseArea, _checks, _n, _session, _t


@dataclass(frozen=True)
class Bar:
    minute: time  # CT bar start
    open: int
    high: int
    low: int
    close: int
    volume: float = 1  # noise.py: missing volume counts as 1, zero as 0


@dataclass(frozen=True)
class SessionContext:
    trade_date: date
    root: str
    prev_close: int | None  # previous NYSE session's regular close, same contract (ticks)
    sigma: Mapping[int, float]  # check minute-of-day -> sigma (SigmaHistory.sigma())
    early_close: bool = False  # 12:00 CT flatten, checks to 11:30


@dataclass(frozen=True)
class Order:
    check: time  # the minute whose open is the model fill
    quantity: int  # signed units: + buy, - sell
    target: int  # position after the fill (+1/0/-1)
    reason: str  # long | short | exit | reverse_long | reverse_short | flatten


@dataclass(frozen=True)
class Signal:
    check: time
    price: int  # close of the bar ending at the check
    upper: float | None
    lower: float | None
    vwap: float | None
    sigma: float | None
    position: int  # before the check
    target: int
    order: Order | None


@dataclass(frozen=True)
class Leg:
    side: int
    entry_at: time
    entry: int
    exit_at: time
    exit: int
    reason: str  # signal_exit | close


@dataclass(frozen=True)
class ModelFill:
    at: time
    price: int  # open of the check-minute bar
    position: int  # after the fill
    closed: tuple[Leg, ...]


@dataclass(frozen=True)
class Void:
    check: time
    reason: str


def decide(side: int, price: float, upper: float, lower: float, vwap: float) -> tuple[bool, int]:
    """One check of the frozen rule: (exit the current side?, side afterwards).

    Long exits below max(upper, VWAP), short above min(lower, VWAP). When flat (or just
    exited), enter long above upper / short below lower; after an exit only the opposite
    direction may be entered at the same check. Restates noise.py's inline rule.
    """
    exited = 0
    if side != 0:
        stop = max(upper, vwap) if side > 0 else min(lower, vwap)
        if (side > 0 and price < stop) or (side < 0 and price > stop):
            exited, side = side, 0
        else:
            return False, side
    if price > upper and exited != 1:
        return exited != 0, 1
    if price < lower and exited != -1:
        return exited != 0, -1
    return exited != 0, 0


class SigmaHistory:
    """Rolling sigma table: mean move per check over the previous sessions that had bars.

    Mirrors NoiseArea.prepare_all: keep the moves (NoiseArea._moves) of the last `lookback`
    sessions with any bar; a check needs `min_observations` values. Feed every session in
    order with `add_session` (also no-bar ones: they are skipped, as in prepare_all).
    """

    def __init__(self, root: str = "MNQ", lookback: int = 14, min_observations: int = 10):
        self.root = root
        self.min_observations = min_observations
        self._history: deque[dict[int, float]] = deque(maxlen=lookback)

    def sigma(self) -> dict[int, float]:
        out = {}
        for n in _checks(early=False, root=self.root):
            values = [h[n] for h in self._history if n in h]
            if len(values) >= self.min_observations:
                out[n] = float(np.mean(values))
        return out

    def add_session(self, bars: Mapping[time, tuple[int, int, int, int]]) -> None:
        if bars:
            self._history.append(NoiseArea._moves(SimpleNamespace(root=self.root, bars=bars)))


@dataclass
class _Pending:
    check: int
    exit_leg: tuple[int, time, int] | None  # position being closed
    new_side: int
    flatten: bool = False


class NoiseEngine:
    """One session of SC-FUT-0005. Feed closed bars in minute order with `on_bar`, then call
    `end_session`. `legs`, `status` and `trades()` then equal NoiseArea().simulate's."""

    def __init__(self, ctx: SessionContext):
        self.ctx = ctx
        self._open_n = _n(_session(ctx.root)[0])
        _, checks, flat_at = _session(ctx.root, ctx.early_close)
        self._checks = frozenset(checks)
        self._flat_n = _n(flat_at)
        self.legs: list[Leg] = []
        self.position: tuple[int, time, int] | None = None  # (side, entry_at, entry)
        self.status = "waiting_open"  # -> running -> done | no_trade | non_evaluable
        self._anchors: tuple[int, int] | None = None
        self._pv = self._vol = 0.0
        self._pending: _Pending | None = None
        self._last = -1

    @property
    def side(self) -> int:
        return 0 if self.position is None else self.position[0]

    def on_bar(self, bar: Bar) -> list[Signal | ModelFill | Void]:
        n = _n(bar.minute)
        if n <= self._last:
            raise ValueError(f"bar {bar.minute} out of order (last {_t(self._last)})")
        self._last = n
        events: list[Signal | ModelFill | Void] = []
        if self._pending is not None:
            events.append(self._resolve(n, bar.open))
        if self.status in ("done", "no_trade", "non_evaluable") or n < self._open_n:
            return events
        if self.status == "waiting_open":
            if n != self._open_n or self.ctx.prev_close is None:
                self.status = "no_trade"  # noise.py: no 08:30 bar or no previous close
                return events
            self._anchors = (max(bar.open, self.ctx.prev_close), min(bar.open, self.ctx.prev_close))
            self.status = "running"
        if n >= self._flat_n:
            if self.position is not None:
                if n == self._flat_n:
                    side, entry_at, entry = self.position
                    leg = Leg(side, entry_at, entry, bar.minute, bar.open, "close")
                    self.legs.append(leg)
                    self.position = None
                    events.append(ModelFill(bar.minute, bar.open, 0, (leg,)))
                else:
                    self.status = "non_evaluable"  # flatten bar missing
                    return events
            self.status = "done"
            return events
        v = bar.volume or 0
        self._pv += v * (bar.high + bar.low + bar.close) / 3
        self._vol += v
        check = n + 1
        if check in self._checks and check in self.ctx.sigma:
            events.append(self._check(check, bar.close))
        elif check == self._flat_n and self.position is not None:
            side = self.side
            order = Order(_t(check), -side, 0, "flatten")
            events.append(Signal(_t(check), bar.close, None, None, None, None, side, 0, order))
        return events

    def _check(self, check: int, price: int) -> Signal:
        s = self.ctx.sigma[check]
        hi, lo = self._anchors
        upper = hi * (1 + s)
        lower = lo * (1 - s)
        vwap = self._pv / self._vol if self._vol else price
        before = self.side
        exited, after = decide(before, price, upper, lower, vwap)
        order = None
        if exited or after != before:
            self._pending = _Pending(check, self.position if exited else None, after)
            if exited and after:
                reason = "reverse_long" if after > 0 else "reverse_short"
            elif exited:
                reason = "exit"
            else:
                reason = "long" if after > 0 else "short"
            order = Order(_t(check), after - before, after, reason)
        return Signal(_t(check), price, upper, lower, vwap, s, before, after, order)

    def _resolve(self, n: int, open_: int) -> ModelFill | Void:
        p, self._pending = self._pending, None
        if n != p.check:
            return Void(_t(p.check), "check-minute bar missing")
        at = _t(n)
        closed = ()
        if p.exit_leg is not None:
            side, entry_at, entry = p.exit_leg
            closed = (Leg(side, entry_at, entry, at, open_, "signal_exit"),)
            self.legs.extend(closed)
            self.position = None
        if p.new_side:
            self.position = (p.new_side, at, open_)
        return ModelFill(at, open_, self.side, closed)

    def end_session(self) -> str:
        """Close the books: a pending check voids, an unflattened position is non-evaluable."""
        self._pending = None
        if self.status == "running" and self.position is not None:
            self.status = "non_evaluable"
        if self.status in ("running", "done", "waiting_open"):
            self.status = "traded" if self.legs else "no_trade"
        return self.status

    def trades(self) -> list[Trade]:
        """The closed legs as workbench Trades (NoiseArea._trade: L3 costs, gross/net cents)."""
        day = SimpleNamespace(root=self.ctx.root)
        return [NoiseArea._trade(day, dataclasses.asdict(x), x.side) for x in self.legs]


def bars_of(day: DayInput) -> list[Bar]:
    """A workbench DayInput as the closed-bar stream a live feed would deliver (minute order).

    Volume follows noise.py's VWAP read: a bar with no volume entry counts as 1.
    """
    vols = day.volumes or {}
    return [Bar(m, *day.bars[m], vols.get(m, 1)) for m in sorted(day.bars)]


def context_of(day: DayInput, sigma: Mapping[int, float]) -> SessionContext:
    """Session context for a workbench day: early close as noise.py infers it."""
    early = day.exit_minute < _session(day.root)[2]
    return SessionContext(day.trade_date, day.root, day.prev_close, sigma, early)


def replay(day: DayInput, sigma: Mapping[int, float]) -> NoiseEngine:
    """Feed a whole day through a fresh engine (the equivalence harness)."""
    engine = NoiseEngine(context_of(day, sigma))
    for bar in bars_of(day):
        engine.on_bar(bar)
    engine.end_session()
    return engine

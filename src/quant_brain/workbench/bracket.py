"""SC-FUT-0009 / 0010 / 0011 plug-ins: reversion trades held in a bracket (target + stop).

Frozen rules: brain/_system/futures/sc-fut-0009-spec.v1.json (fade_band),
sc-fut-0010-spec.v1.json (gap_fill) and sc-fut-0011-spec.v1.json (evening_revert); the
`fills` and `luck` sections are shared. Fixtures: tests/test_bracket_fixtures.py.

Fills, as implemented (one 1-minute bar at a time, integer ticks):
- decision on the close of the bar ending at the decision minute; entry at the open of the
  decision-minute bar;
- stop (resting stop): checked from the entry bar on; fills at the stop, or at the bar open if
  the bar opens at or beyond it (`gap_stop`);
- target (resting limit): fills at the target only on a bar after the entry bar whose range
  trades through it by at least 1 tick (`target`); a later bar that opens beyond the target
  still fills at the target. If the entry fill itself is already beyond the target, the limit
  is marketable and fills at the entry price (`gap_target`, gross 0, costs paid);
- a bar reaching both: stop first;
- flatten at the open of the flatten-minute bar; a day with any trade whose flatten bar is
  missing is non-evaluable (the matched control may need that bar too);
- rounding to the tick grid: targets toward the entry, stops away from it.

Matched control (spec `luck`): every leg keeps its entry minute and its target and stop
distances from the entry; its direction is redrawn at random and it is re-simulated on the same
bars with the same fill rules. Redrawn legs can overlap in time, so equity paths use
`paths.book_*` for both the strategy and the control.
"""

from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass
from datetime import time
from typing import Any, ClassVar

import numpy as np

from quant_brain.futures import orb
from quant_brain.futures.controls import ROOT_CODE
from quant_brain.futures.orb import Bar, DayInput, DayResult, Trade
from quant_brain.prop import paths
from quant_brain.workbench.noise import FIRST_CHECK, NoiseArea, _session

BRACKET_SEED = 20261028
EPS = 1e-9


def _n(m: time) -> int:
    return m.hour * 60 + m.minute


def _t(n: int) -> time:
    return time(n // 60, n % 60)


def to_tick(level: float, side: int) -> int:
    """A target or stop level on the tick grid for a trade of direction `side`.

    A long's target sits above the entry (toward it = down) and its stop below (away = down);
    a short's are mirrored (up). So both round down for longs and up for shorts. EPS absorbs
    float noise such as 105 * 1.02 = 107.10000000000001.
    """
    return math.floor(level + EPS) if side > 0 else math.ceil(level - EPS)


def run_bracket(
    bars: dict[time, Bar],
    *,
    root: str,
    side: int,
    entry_at: time,
    target: int,
    stop: int,
    flatten_at: time,
    signal_at: time | None = None,
) -> Trade | None:
    """One bracketed trade entered at `entry_at`'s open; None if the flatten bar is needed but
    missing. A missing minute had no trades, so nothing can fill in it."""
    entry = bars[entry_at][0]
    exit_at, exit_px, reason = flatten_at, None, "flatten"
    for n in range(_n(entry_at), _n(flatten_at)):
        bar = bars.get(_t(n))
        if bar is None:
            continue
        open_, high, low, _ = bar
        adverse, favourable = (low, high) if side > 0 else (high, low)
        if side * (open_ - stop) <= 0:
            exit_at, exit_px, reason = _t(n), open_, "gap_stop"
        elif side * (adverse - stop) <= 0:
            exit_at, exit_px, reason = _t(n), stop, "stop"
        elif n == _n(entry_at):
            if side * (open_ - target) > 0:  # entry already beyond the target: marketable limit
                exit_at, exit_px, reason = _t(n), open_, "gap_target"
        elif side * (favourable - target) >= 1:
            exit_at, exit_px, reason = _t(n), target, "target"
        if exit_px is not None:
            break
    if exit_px is None:
        flat = bars.get(flatten_at)
        if flat is None:
            return None
        exit_px = flat[0]
    gross, net = orb._net(root, side, entry, exit_px)
    return Trade(
        side=side,
        signal_minute=signal_at,
        entry_minute=entry_at,
        entry_ticks=entry,
        stop_level_ticks=stop,
        exit_minute=exit_at,
        exit_ticks=exit_px,
        exit_reason=reason,
        gross_cents=gross,
        net_cents=net,
        entry_bar_stop=exit_at == entry_at and reason in ("stop", "gap_stop"),
        gap_affected=False,  # 1-minute bars omit minutes with no trades: nothing to fill there
        stress_exit_ticks=None,
        stress_net_cents=net,
    )


def control_trade(day: DayInput, leg: dict, side: int) -> Trade:
    """The leg re-simulated in direction `side` with the same target and stop distances."""
    entry = day.bars[leg["entry_at"]][0]
    to_target = leg["side"] * (leg["target"] - entry)
    to_stop = leg["side"] * (entry - leg["stop"])
    trade = run_bracket(
        day.bars,
        root=day.root,
        side=side,
        entry_at=leg["entry_at"],
        target=entry + side * to_target,
        stop=entry - side * to_stop,
        flatten_at=leg["flatten_at"],
        signal_at=leg["signal_at"],
    )
    assert trade is not None  # traded days always have their flatten bar
    return trade


Plan = tuple[str, list[Trade], list[dict], list[tuple[str, time]]]


class _BracketCard:
    """Shared simulate / matched control; each card plans its own legs in `_plan`."""

    seed_tag: ClassVar[int]

    def prepare(self, day: DayInput) -> DayInput:
        return day

    def _plan(self, day: DayInput) -> Plan:
        raise NotImplementedError

    def _enter(
        self, day: DayInput, side: int, n: int, target: int, stop: int, flatten_at: time
    ) -> tuple[dict, Trade | None]:
        leg = {
            "side": side,
            "signal_at": _t(n - 1),
            "entry_at": _t(n),
            "target": target,
            "stop": stop,
            "flatten_at": flatten_at,
        }
        trade = run_bracket(
            day.bars,
            root=day.root,
            side=side,
            entry_at=leg["entry_at"],
            target=target,
            stop=stop,
            flatten_at=flatten_at,
            signal_at=leg["signal_at"],
        )
        return leg, trade

    @staticmethod
    def _finish(
        day: DayInput, trades: list[Trade], legs: list[dict], events: list, flatten_at: time
    ) -> Plan:
        if trades and flatten_at not in day.bars:
            return "non_evaluable", [], [], [*events, ("flatten_missing", flatten_at)]
        return ("traded" if trades else "no_trade"), trades, legs, events

    def simulate(self, day: DayInput) -> DayResult:
        if not day.bars:
            return DayResult(day.trade_date, day.root, "ineligible", 0, 0, [], [])
        status, trades, _, events = self._plan(day)
        net = sum(x.net_cents for x in trades)
        return DayResult(day.trade_date, day.root, status, net, net, trades, events)

    @staticmethod
    def equity_path(bars, trades, tick: int) -> tuple[int, list[tuple[int, int]]]:
        return paths.book_path(bars, trades, tick)[0], paths.book_records(bars, trades, tick)

    def matched_control(
        self, day: DayInput, result: DayResult, draws: int
    ) -> tuple[list[int], list[int], list[int], list[list[tuple[int, int]]]]:
        """(gross, trades, day low, equity records) per draw: each leg in a random direction."""
        if result.status != "traded":
            return [0] * draws, [0] * draws, [0] * draws, [[]] * draws
        _, _, legs, _ = self._plan(day)
        stamp = int(day.trade_date.strftime("%Y%m%d"))
        seq = np.random.SeedSequence([BRACKET_SEED, ROOT_CODE[day.root], stamp, self.seed_tag])
        flips = np.random.Generator(np.random.PCG64(seq)).integers(0, 2, size=(draws, len(legs)))
        tick = orb.TICK_CENTS[day.root]
        cache: dict[tuple[int, ...], tuple[int, int, list[tuple[int, int]]]] = {}
        gross, lows, recs = [], [], []
        for row in flips:
            key = tuple(int(x) for x in row)
            if key not in cache:
                trades = [
                    control_trade(day, leg, 1 if f else -1)
                    for leg, f in zip(legs, key, strict=True)
                ]
                low, rec = self.equity_path(day.bars, trades, tick)
                cache[key] = (sum(x.gross_cents for x in trades), low, rec)
            g, lo, rec = cache[key]
            gross.append(g)
            lows.append(lo)
            recs.append(rec)
        return gross, [len(legs)] * draws, lows, recs


@dataclass(frozen=True)
class FadeBand(_BracketCard):
    """SC-FUT-0009: inside the SC-FUT-0005 noise band, past half-way to its edge, trade back
    toward the 08:30 open; stop at the band edge; flat at 15:00 (12:00 on early-close days)."""

    family: str = dataclasses.field(default="fade_band", init=False)
    seed_tag: ClassVar[int] = 9
    ENTRY_FRACTION: ClassVar[float] = 0.5
    MAX_ENTRIES: ClassVar[int] = 3

    def settings(self) -> dict[str, Any]:
        return {
            "card": "SC-FUT-0009",
            "band": "SC-FUT-0005 (sigma over 14 sessions, >= 10 values)",
            "entry_fraction": self.ENTRY_FRACTION,
            "target": "08:30 open",
            "stop": "band edge",
            "max_entries": self.MAX_ENTRIES,
            "size": 1,
        }

    @property
    def first_fill(self) -> time:
        return FIRST_CHECK

    def prepare_all(self, days: list[DayInput]) -> list[DayInput]:
        """Exactly SC-FUT-0005's sigma per check, from the previous 14 sessions only."""
        return NoiseArea().prepare_all(days)

    def _plan(self, day: DayInput) -> Plan:
        sigma = (day.context or {}).get("sigma") or {}
        open_at, _, close_at = _session(day.root)
        first = day.bars.get(open_at)
        if first is None or day.prev_close is None:
            return "no_trade", [], [], []
        open_ = first[0]
        hi_anchor, lo_anchor = max(open_, day.prev_close), min(open_, day.prev_close)
        _, checks, flat_at = _session(day.root, day.exit_minute < close_at)
        trades: list[Trade] = []
        legs: list[dict] = []
        busy_until = -1  # minute of the last exit: a new entry needs a later check
        for n in checks:
            if len(trades) >= self.MAX_ENTRIES:
                break
            price_bar, fill_bar = day.bars.get(_t(n - 1)), day.bars.get(_t(n))
            if n <= busy_until or n not in sigma or price_bar is None or fill_bar is None:
                continue
            price = price_bar[3]
            upper = hi_anchor * (1 + sigma[n])
            lower = lo_anchor * (1 - sigma[n])
            if open_ < price < upper and price >= open_ + self.ENTRY_FRACTION * (upper - open_):
                side, edge = -1, upper
            elif lower < price < open_ and price <= open_ - self.ENTRY_FRACTION * (open_ - lower):
                side, edge = 1, lower
            else:
                continue
            leg, trade = self._enter(
                day, side, n, to_tick(open_, side), to_tick(edge, side), flat_at
            )
            if trade is None:
                return "non_evaluable", [], [], [("flatten_missing", flat_at)]
            trades.append(trade)
            legs.append(leg)
            busy_until = _n(trade.exit_minute)
        return self._finish(day, trades, legs, [], flat_at)


GAP_SIGNAL = time(8, 30)
GAP_ENTRY = time(8, 31)
GAP_FLATTEN = time(11, 0)


@dataclass(frozen=True)
class GapFill(_BracketCard):
    """SC-FUT-0010: a 0.2-1.0 ATR gap from the previous regular close, still open after the
    08:30 bar, is traded back toward that close at 08:31; stop one gap away; flat at 11:00."""

    family: str = dataclasses.field(default="gap_fill", init=False)
    seed_tag: ClassVar[int] = 10
    MIN_GAP_ATR: ClassVar[str] = "0.20"
    MAX_GAP_ATR: ClassVar[str] = "1.00"

    def settings(self) -> dict[str, Any]:
        return {
            "card": "SC-FUT-0010",
            "atr_sessions": orb.ATR_SESSIONS,
            "gap_atr": [self.MIN_GAP_ATR, self.MAX_GAP_ATR],
            "entry": "08:31",
            "target": "previous regular close",
            "stop": "1 x gap",
            "flatten": "11:00",
            "size": 1,
        }

    @property
    def first_fill(self) -> time:
        return GAP_ENTRY

    def _plan(self, day: DayInput) -> Plan:
        bar = day.bars.get(GAP_SIGNAL)
        if bar is None or day.prev_close is None or day.atr_tr_sum is None:
            return "no_trade", [], [], []
        gap = bar[0] - day.prev_close
        size, total = abs(gap), day.atr_tr_sum  # ATR = total / 14, compared exactly
        if not (gap and total <= 5 * orb.ATR_SESSIONS * size and orb.ATR_SESSIONS * size <= total):
            return "no_trade", [], [], []
        # Still gapped and not filled: the whole 08:30 bar stayed beyond the previous close.
        if (gap > 0 and bar[2] <= day.prev_close) or (gap < 0 and bar[1] >= day.prev_close):
            return "no_trade", [], [], [("filled_in_first_bar", GAP_SIGNAL)]
        if GAP_ENTRY not in day.bars:
            return "no_trade", [], [], [("entry_missing", GAP_ENTRY)]
        side = -1 if gap > 0 else 1
        entry = day.bars[GAP_ENTRY][0]
        leg, trade = self._enter(
            day, side, _n(GAP_ENTRY), day.prev_close, entry - side * size, GAP_FLATTEN
        )
        if trade is None:
            return "non_evaluable", [], [], [("flatten_missing", GAP_FLATTEN)]
        return self._finish(day, [trade], [leg], [], GAP_FLATTEN)


EVENING_OPEN = time(17, 0)
EVENING_FLATTEN = time(20, 30)
EVENING_CHECKS = list(range(17 * 60 + 30, 20 * 60 + 1, 15))
EVENING_WINDOW = range(_n(EVENING_OPEN), _n(EVENING_FLATTEN) + 1)  # 211 bars, 17:00..20:30


@dataclass(frozen=True)
class EveningRevert(_BracketCard):
    """SC-FUT-0011: in the 17:00-20:30 CT evening that starts the trade date, a move from the
    17:00 open (P0) beyond its normal size for that check is traded back to P0; stop at twice
    the normal move on the far side; flat at 20:30.

    Day inputs come from `bars.build_evenings` (session = "evening"): bars keyed 17:00..20:30
    of the previous calendar evening, `trade_date` the trade date they belong to.
    """

    family: str = dataclasses.field(default="evening_revert", init=False)
    session: ClassVar[str] = "evening"
    seed_tag: ClassVar[int] = 11
    LOOKBACK: ClassVar[int] = 14
    MIN_OBSERVATIONS: ClassVar[int] = 10
    MAX_MISSING: ClassVar[int] = 30
    MAX_ENTRIES: ClassVar[int] = 2
    STOP_SIGMAS: ClassVar[int] = 2

    def settings(self) -> dict[str, Any]:
        return {
            "card": "SC-FUT-0011",
            "session": "17:00-20:30 CT, previous evening",
            "lookback_evenings": self.LOOKBACK,
            "min_observations": self.MIN_OBSERVATIONS,
            "checks": "every 15 min 17:30..20:00",
            "max_missing_bars": self.MAX_MISSING,
            "target": "P0 (17:00 open)",
            "stop_sigmas": self.STOP_SIGMAS,
            "max_entries": self.MAX_ENTRIES,
            "size": 1,
            "entry_band": "sigma < |price/P0 - 1| < 2 sigma (addendum 1)",
        }

    @property
    def first_fill(self) -> time:
        return _t(EVENING_CHECKS[0])

    @classmethod
    def _complete(cls, day: DayInput) -> bool:
        """A usable past evening: P0 present and at most 30 of its 211 bars missing."""
        missing = sum(_t(n) not in day.bars for n in EVENING_WINDOW)
        return EVENING_OPEN in day.bars and missing <= cls.MAX_MISSING

    @staticmethod
    def _moves(day: DayInput) -> dict[int, float]:
        p0 = day.bars[EVENING_OPEN][0]
        out = {}
        for n in EVENING_CHECKS:
            bar = day.bars.get(_t(n - 1))
            if bar is not None and p0 > 0:
                out[n] = abs(bar[3] / p0 - 1)
        return out

    def prepare_all(self, days: list[DayInput]) -> list[DayInput]:
        """sigma per check: mean move over the previous 14 usable evenings only."""
        history: list[dict[int, float]] = []
        out = []
        for day in days:
            past = history[-self.LOOKBACK :]
            sigma = {}
            for n in EVENING_CHECKS:
                values = [h[n] for h in past if n in h]
                if len(values) >= self.MIN_OBSERVATIONS:
                    sigma[n] = float(np.mean(values))
            out.append(dataclasses.replace(day, context={"sigma": sigma}))
            if day.bars and self._complete(day):
                history.append(self._moves(day))
        return out

    def _plan(self, day: DayInput) -> Plan:
        sigma = (day.context or {}).get("sigma") or {}
        first = day.bars.get(EVENING_OPEN)
        if first is None:
            return "no_trade", [], [], [("p0_missing", EVENING_OPEN)]
        p0 = first[0]
        trades: list[Trade] = []
        legs: list[dict] = []
        events: list[tuple[str, time]] = []
        busy_until = -1
        for n in EVENING_CHECKS:
            # Point in time: only bars that ended before this check count as missing.
            missing = sum(_t(k) not in day.bars for k in range(_n(EVENING_OPEN), n))
            if missing > self.MAX_MISSING:
                events.append(("too_many_missing", _t(n)))
                break
            if len(trades) >= self.MAX_ENTRIES:
                break
            price_bar, fill_bar = day.bars.get(_t(n - 1)), day.bars.get(_t(n))
            if n <= busy_until or n not in sigma or price_bar is None or fill_bar is None:
                continue
            move = price_bar[3] - p0
            if abs(move) <= sigma[n] * p0:  # |price / P0 - 1| > sigma, without float division
                continue
            if abs(move) >= self.STOP_SIGMAS * sigma[n] * p0:  # addendum 1: inside the stop only
                continue
            side = -1 if move > 0 else 1
            stop = to_tick(p0 * (1 - side * self.STOP_SIGMAS * sigma[n]), side)
            leg, trade = self._enter(day, side, n, p0, stop, EVENING_FLATTEN)
            if trade is None:
                return "non_evaluable", [], [], [*events, ("flatten_missing", EVENING_FLATTEN)]
            trades.append(trade)
            legs.append(leg)
            busy_until = _n(trade.exit_minute)
        return self._finish(day, trades, legs, events, EVENING_FLATTEN)

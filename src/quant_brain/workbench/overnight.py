"""SC-FUT-0012 plug-in: overnight drift, a long hold over the Globex night (17:00 -> 08:29 CT).

Frozen rule: brain/_system/futures/sc-fut-0012-spec.v1.json, with addendum 1
(sc-fut-0012-addendum-1.md, written before any result). Fixtures: tests/test_bracket_fixtures.py.

Day inputs come from `bars.build_overnights` (session = "overnight"): the bars of the night
that ends at D's 08:30 open, keyed by clock time (17:00..23:59 of the previous calendar evening,
then 00:00..08:29 of D), and in `context` the previous NYSE session P, whether a holiday sits
between P and D, and P's (08:30 open, regular close) on D's contract.

As implemented:
- no overnight bars at all -> ineligible (dropped, as in every family);
- a holiday between P and D -> skip, no trade ($0, evaluable);
- a missing 17:00 or 08:29 bar -> non-evaluable (both trials);
- T1 trades every other night; T2 only if P's RTH return (close - open) < 0, else no trade
  ($0), including when P's open or close is missing;
- long 1 at the 17:00 open, out at the 08:29 open; no stop.

Matched control (spec `luck`): the same entry and exit bars, each draw a random direction from
PCG64(SeedSequence([20261029, root, yyyymmdd, 12])); 0 on days without a trade.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from datetime import time
from typing import Any, ClassVar

import numpy as np

from quant_brain.futures import orb
from quant_brain.futures.bars import OVERNIGHT_EXIT, OVERNIGHT_OPEN
from quant_brain.futures.controls import ROOT_CODE
from quant_brain.futures.orb import Bar, DayInput, DayResult, Trade

OVERNIGHT_SEED = 20261029
TRIALS = ("T1_unconditional", "T2_after_down_day")


def _clock(n: int) -> time:
    return time(n // 60 % 24, n % 60)


# The overnight in clock order across midnight: 17:00..23:59, then 00:00..08:29 (930 minutes).
NIGHT = [
    _clock(n)
    for n in range(
        OVERNIGHT_OPEN.hour * 60 + OVERNIGHT_OPEN.minute,
        24 * 60 + OVERNIGHT_EXIT.hour * 60 + OVERNIGHT_EXIT.minute + 1,
    )
]


def night_points(bars: dict[time, Bar], trade: Trade):
    """(adverse, favourable) open P&L in ticks per contract for each minute held, in clock
    order across midnight: bars inside the trade give their extremes, the exit bar its open
    (out at the open); missing bars give nothing."""
    side, entry = trade.side, trade.entry_ticks
    start, stop = NIGHT.index(trade.entry_minute), NIGHT.index(trade.exit_minute)
    for minute in NIGHT[start : stop + 1]:
        if minute == trade.exit_minute:
            yield side * (trade.exit_ticks - entry), side * (trade.exit_ticks - entry)
            continue
        bar = bars.get(minute)
        if bar is None:
            continue
        adverse, favourable = (bar[2], bar[1]) if side > 0 else (bar[1], bar[2])
        yield side * (adverse - entry), side * (favourable - entry)


def night_records(
    bars: dict[time, Bar], trades: list[Trade], tick_cents: int
) -> list[tuple[int, int]]:
    """`paths.day_records` for an overnight hold (minutes ordered across midnight)."""
    realised = run_low = run_high = 0
    out: list[tuple[int, int]] = []
    for trade in trades:
        for adverse, favourable in night_points(bars, trade):
            lo, hi = realised + adverse * tick_cents, realised + favourable * tick_cents
            if lo < run_low or hi > run_high:
                out.append((lo, hi))
                run_low, run_high = min(run_low, lo), max(run_high, hi)
        realised += trade.gross_cents
    return out


@dataclass(frozen=True)
class OvernightDrift:
    """SC-FUT-0012: long 1 MNQ at the 17:00 CT reopen, out at D's 08:29 open (before the RTH
    open). T1 every night; T2 only after a down previous NYSE session (RTH close < 08:30 open)."""

    trial: str = "T1_unconditional"
    family: str = dataclasses.field(default="overnight_drift", init=False)
    session: ClassVar[str] = "overnight"
    seed_tag: ClassVar[int] = 12

    def __post_init__(self) -> None:
        if self.trial not in TRIALS:
            raise ValueError(f"trial must be one of {TRIALS}")

    def settings(self) -> dict[str, Any]:
        return {
            "card": "SC-FUT-0012",
            "trial": self.trial,
            "entry": "long at the 17:00 CT open",
            "exit": "08:29 CT open of D",
            "stop": None,
            "holiday": "skip (addendum 1)",
            "size": 1,
        }

    @property
    def first_fill(self) -> time:
        return OVERNIGHT_OPEN

    def prepare(self, day: DayInput) -> DayInput:
        return day

    def _wants(self, day: DayInput) -> bool:
        if self.trial == "T1_unconditional":
            return True
        open_, close = (day.context or {}).get("previous_rth") or (None, None)
        return open_ is not None and close is not None and close - open_ < 0

    def simulate(self, day: DayInput) -> DayResult:
        def result(status, trades=(), events=()):
            trades = list(trades)
            net = sum(x.net_cents for x in trades)
            return DayResult(day.trade_date, day.root, status, net, net, trades, list(events))

        if not day.bars:
            return result("ineligible")
        context = day.context or {}
        if context.get("holiday_gap"):
            return result("no_trade", events=[("holiday_skip", OVERNIGHT_OPEN)])
        for minute in (OVERNIGHT_OPEN, OVERNIGHT_EXIT):
            if minute not in day.bars:
                return result("non_evaluable", events=[("bar_missing", minute)])
        if not self._wants(day):
            return result("no_trade", events=[("previous_session_not_down", OVERNIGHT_OPEN)])
        entry, exit_ = day.bars[OVERNIGHT_OPEN][0], day.bars[OVERNIGHT_EXIT][0]
        gross, net = orb._net(day.root, 1, entry, exit_)
        trade = Trade(
            side=1,
            signal_minute=None,
            entry_minute=OVERNIGHT_OPEN,
            entry_ticks=entry,
            stop_level_ticks=entry,  # no stop
            exit_minute=OVERNIGHT_EXIT,
            exit_ticks=exit_,
            exit_reason="flatten",
            gross_cents=gross,
            net_cents=net,
            entry_bar_stop=False,
            gap_affected=False,  # no stop: a missing minute inside the hold changes nothing
            stress_exit_ticks=None,
            stress_net_cents=net,
        )
        return result("traded", [trade])

    @staticmethod
    def equity_path(bars, trades, tick: int) -> tuple[int, list[tuple[int, int]]]:
        records = night_records(bars, list(trades), tick)
        close = sum(x.gross_cents for x in trades)
        return min([0, close] + [lo for lo, _ in records]), records

    def matched_control(
        self, day: DayInput, result: DayResult, draws: int
    ) -> tuple[list[int], list[int], list[int], list[list[tuple[int, int]]]]:
        """(gross, trades, day low, equity records) per draw: the same hold, random direction."""
        if result.status != "traded":
            return [0] * draws, [0] * draws, [0] * draws, [[]] * draws
        trade = result.trades[0]
        stamp = int(day.trade_date.strftime("%Y%m%d"))
        seq = np.random.SeedSequence([OVERNIGHT_SEED, ROOT_CODE[day.root], stamp, self.seed_tag])
        signs = np.random.Generator(np.random.PCG64(seq)).integers(0, 2, size=draws) * 2 - 1
        tick = orb.TICK_CENTS[day.root]
        both = {}
        for side in (1, -1):
            gross = side * trade.gross_cents
            flipped = dataclasses.replace(trade, side=side, gross_cents=gross)
            low, records = self.equity_path(day.bars, [flipped], tick)
            both[side] = (gross, low, records)
        picked = [both[int(s)] for s in signs]
        return (
            [g for g, _, _ in picked],
            [1] * draws,
            [lo for _, lo, _ in picked],
            [r for _, _, r in picked],
        )

"""Strategy plug-ins (W1). A strategy is fixed code plus a small dict of settings.

Every plug-in turns a day of minute bars into trades deterministically; no agent
decides anything at run time. Changing a setting makes a different trial.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from datetime import time
from fractions import Fraction
from typing import Any, Protocol

import numpy as np

from quant_brain.futures import orb
from quant_brain.futures.controls import ROOT_CODE
from quant_brain.futures.orb import DayInput, DayResult, Trade


class Strategy(Protocol):
    family: str

    def settings(self) -> dict[str, Any]: ...
    def prepare(self, day: DayInput) -> DayInput: ...
    def simulate(self, day: DayInput) -> DayResult: ...
    @property
    def first_fill(self) -> time: ...


@dataclass(frozen=True)
class OpeningRangeBreakout:
    """Cash-open ORB with an ATR stop (SC-FUT-0001 is range_bars=15, stop_fraction='0.10')."""

    range_bars: int = 15
    stop_fraction: str = "0.10"
    family: str = dataclasses.field(default="orb", init=False)

    def __post_init__(self) -> None:
        if not 1 <= self.range_bars <= 120:
            raise ValueError("range_bars must be 1..120 minutes")
        if not 0 < Fraction(self.stop_fraction) <= 2:
            raise ValueError("stop_fraction must be in (0, 2]")

    def settings(self) -> dict[str, Any]:
        return {"range_bars": self.range_bars, "stop_fraction": self.stop_fraction}

    def prepare(self, day: DayInput) -> DayInput:
        stop = (
            None
            if day.atr_tr_sum is None
            else orb.stop_from_sum(day.atr_tr_sum, Fraction(self.stop_fraction))
        )
        return dataclasses.replace(day, stop_ticks=stop)

    def simulate(self, day: DayInput) -> DayResult:
        return orb.simulate_day(day, range_bars=self.range_bars)

    @property
    def first_fill(self) -> time:
        return orb.add_minutes(orb.RANGE_START, self.range_bars + 1)


CASH_CLOSE = time(15, 0)
RANGE_START_MARK = time(8, 30)  # event timestamp for day-level skips
MATCHED_SEED = 20261026


@dataclass(frozen=True)
class LateDayMomentum:
    """SC-FUT-0002: trade the last `window_minutes` before the 15:00 CT cash close in the
    direction of the move since the previous regular close (Baltussen et al. 2021)."""

    window_minutes: int = 30
    family: str = dataclasses.field(default="late_momentum", init=False)

    def __post_init__(self) -> None:
        if not 5 <= self.window_minutes <= 120:
            raise ValueError("window_minutes must be 5..120")

    def settings(self) -> dict[str, Any]:
        return {"window_minutes": self.window_minutes}

    def prepare(self, day: DayInput) -> DayInput:
        return day

    @property
    def first_fill(self) -> time:
        return orb.add_minutes(CASH_CLOSE, -self.window_minutes)

    def simulate(self, day: DayInput) -> DayResult:
        def result(status, trades=(), events=()):
            trades = list(trades)
            net = sum(t.net_cents for t in trades)
            return DayResult(day.trade_date, day.root, status, net, net, trades, list(events))

        if not day.bars:
            return result("ineligible")
        if day.prev_close is None:  # frozen spec: missing prior close -> no trade ($0)
            return result("no_trade", events=[("prior_close_missing", RANGE_START_MARK)])
        if day.exit_minute < CASH_CLOSE:
            return result("no_trade", events=[("early_close_skip", day.exit_minute)])
        entry_at = self.first_fill
        signal_at = orb.add_minutes(entry_at, -1)
        signal_bar = day.bars.get(signal_at)
        if signal_bar is None:
            return result("no_trade", events=[("signal_missing", signal_at)])
        side = (signal_bar[3] > day.prev_close) - (signal_bar[3] < day.prev_close)
        if side == 0:
            return result("no_trade")
        if entry_at not in day.bars:
            return result("no_trade", events=[("entry_missing", entry_at)])
        exit_bar = day.bars.get(CASH_CLOSE)
        if exit_bar is None:
            return result("non_evaluable")
        entry, exit_ = day.bars[entry_at][0], exit_bar[0]
        gross = side * (exit_ - entry) * orb.TICK_CENTS[day.root]
        net = gross - orb.L3_ROUND_TRIP_CENTS[day.root]
        trade = Trade(
            side=side,
            signal_minute=signal_at,
            entry_minute=entry_at,
            entry_ticks=entry,
            stop_level_ticks=entry,  # no stop
            exit_minute=CASH_CLOSE,
            exit_ticks=exit_,
            exit_reason="close",
            gross_cents=gross,
            net_cents=net,
            entry_bar_stop=False,
            gap_affected=False,
            stress_exit_ticks=None,
            stress_net_cents=net,
        )
        return result("traded", [trade])

    def matched_control(
        self, day: DayInput, result: DayResult, draws: int
    ) -> tuple[list[int], list[int]]:
        """Same trade, random direction: (gross cents, trades) per draw; zeros if no trade."""
        if result.status != "traded":
            return [0] * draws, [0] * draws
        t = result.trades[0]
        move = (t.exit_ticks - t.entry_ticks) * orb.TICK_CENTS[day.root]
        stamp = int(day.trade_date.strftime("%Y%m%d"))
        rng = np.random.Generator(
            np.random.PCG64(np.random.SeedSequence([MATCHED_SEED, ROOT_CODE[day.root], stamp, 2]))
        )
        signs = rng.integers(0, 2, size=draws) * 2 - 1
        return [int(s * move) for s in signs], [1] * draws


REGISTRY: dict[str, type] = {"orb": OpeningRangeBreakout, "late_momentum": LateDayMomentum}
GRADING = {
    "orb": {"floor_cents": 1500, "tiers": [(1500, "pass")], "sharpe_min": None},
    "late_momentum": {
        "floor_cents": 500,
        "tiers": [(500, "small edge"), (1000, "good"), (1500, "strong")],
        "sharpe_min": 1.0,
    },
}
DESCRIPTIONS = {
    "late_momentum": "Late-day momentum: in the last 30 minutes before the 3:00 pm CT cash close, trade in the "
    "direction the market has moved since yesterday's close (forced hedging flows).",
    "orb": "Opening-range breakout: trade a break of the first N minutes' range after the 8:30 CT open, "
    "with a stop at a fraction of the 14-day average range, flat by 3:07 pm.",
}


def make(family: str, settings: dict[str, Any] | None = None) -> Strategy:
    if family not in REGISTRY:
        raise ValueError(f"unknown strategy family {family!r}")
    return REGISTRY[family](**(settings or {}))

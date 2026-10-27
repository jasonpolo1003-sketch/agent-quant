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

from quant_brain.futures import orb
from quant_brain.futures.orb import DayInput, DayResult


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


REGISTRY: dict[str, type] = {"orb": OpeningRangeBreakout}
DESCRIPTIONS = {
    "orb": "Opening-range breakout: trade a break of the first N minutes' range after the 8:30 CT open, "
    "with a stop at a fraction of the 14-day average range, flat by 3:07 pm.",
}


def make(family: str, settings: dict[str, Any] | None = None) -> Strategy:
    if family not in REGISTRY:
        raise ValueError(f"unknown strategy family {family!r}")
    return REGISTRY[family](**(settings or {}))

"""SC-FUT-0001 random-entry controls (frozen spec `controls` section).

Each eligible day gets 500 seeded draws. A draw takes k sequential trades,
k = the ORB's executed entry count that day, each at a uniform legal fill
minute after the previous control exit with a random direction and the same
stop, flatten, cost and missing-minute rules as the ORB. The daily control is
the mean of the evaluable draws.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import time

import numpy as np

from quant_brain.futures.orb import (
    SIGNAL_START,
    DayInput,
    Trade,
    add_minutes,
    entry_cutoff,
    minute_span,
    run_trade,
)

DRAW_SEED = 20261026
DRAWS = 500
ROOT_CODE = {"MNQ": 1, "MES": 2}
FIRST_FILL = add_minutes(SIGNAL_START, 1)  # 08:46, the earliest ORB fill


@dataclass(frozen=True)
class Draw:
    net_cents: int
    stress_net_cents: int
    trades: list[Trade]
    evaluable: bool
    rejections: int
    not_taken: int


@dataclass(frozen=True)
class ControlResult:
    k: int
    mean_cents: float
    stress_mean_cents: float
    evaluable_draws: int
    non_evaluable_draws: int
    rejections: int
    not_taken: int
    draws: list[Draw] = field(default_factory=list)


def day_generator(day: DayInput, seed: int = DRAW_SEED) -> np.random.Generator:
    stamp = int(day.trade_date.strftime("%Y%m%d"))
    return np.random.Generator(
        np.random.PCG64(np.random.SeedSequence([seed, ROOT_CODE[day.root], stamp]))
    )


def _draw(day: DayInput, k: int, rng: np.random.Generator, first_fill: time) -> Draw:
    cutoff = entry_cutoff(day.exit_minute)
    trades: list[Trade] = []
    rejections = not_taken = 0
    previous_exit = None
    for _ in range(k):
        candidates = [
            m for m in minute_span(first_fill, cutoff) if previous_exit is None or m > previous_exit
        ]
        fill = None
        while candidates:
            pick = candidates[int(rng.integers(len(candidates)))]
            if pick in day.bars:
                fill = pick
                break
            rejections += 1
            candidates.remove(pick)
        if fill is None:
            not_taken += 1
            break
        side = 1 if int(rng.integers(2)) == 1 else -1
        trade = run_trade(
            day.bars,
            root=day.root,
            side=side,
            entry_minute=fill,
            stop_ticks=day.stop_ticks,
            exit_minute=day.exit_minute,
        )
        if trade is None:
            return Draw(0, 0, trades, False, rejections, not_taken)
        trades.append(trade)
        previous_exit = trade.exit_minute
    return Draw(
        sum(t.net_cents for t in trades),
        sum(t.stress_net_cents for t in trades),
        trades,
        True,
        rejections,
        not_taken,
    )


def daily_control(
    day: DayInput,
    k: int,
    *,
    seed: int = DRAW_SEED,
    draws: int = DRAWS,
    first_fill: time = FIRST_FILL,
) -> ControlResult:
    if k == 0:
        return ControlResult(0, 0.0, 0.0, 0, 0, 0, 0, [])
    if day.stop_ticks is None:
        raise ValueError("controls require an eligible day with a stop distance")
    rng = day_generator(day, seed)
    results = [_draw(day, k, rng, first_fill) for _ in range(draws)]
    good = [d for d in results if d.evaluable]
    return ControlResult(
        k=k,
        mean_cents=sum(d.net_cents for d in good) / len(good) if good else float("nan"),
        stress_mean_cents=sum(d.stress_net_cents for d in good) / len(good)
        if good
        else float("nan"),
        evaluable_draws=len(good),
        non_evaluable_draws=len(results) - len(good),
        rejections=sum(d.rejections for d in results),
        not_taken=sum(d.not_taken for d in results),
        draws=results,
    )

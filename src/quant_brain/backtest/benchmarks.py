"""Random-entry benchmark, exactly as SC-0002's ``benchmarks.random_entry`` pins it.

Run i uses ``numpy.random.default_rng(seed_start + i)``. Rule A's holding
times are shuffled and each is used once. For each, an entry fill day is drawn
uniformly from period days other than the first, on which the filter was true
at the prior close. The trade must fit inside the period, and must fill at
least one trading day after (or exit at least one day before) every other
trade in the run. Up to ``retry_limit`` draws are allowed per trade; a run that
cannot place every trade is discarded and counted. Returns are fill-open to
fill-open with the same multiplicative costs as the rule.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np


@dataclass
class RandomEntryResult:
    average_returns: list[float]
    completed: int
    discarded: int
    trades: list[list[tuple[int, float, int]]] = field(default_factory=list)


def random_entry(
    *, opens: np.ndarray, filter_ok: np.ndarray, holding_times: Sequence[int], cost: float,
    p0: int, p1: int, runs: int, seed_start: int, retry_limit: int = 10_000,
    record_trades: bool = False,
) -> RandomEntryResult:
    eligible = np.array([d for d in range(p0 + 1, p1 + 1) if filter_ok[d - 1]], dtype=int)
    averages: list[float] = []
    kept: list[list[tuple[int, float, int]]] = []
    discarded = 0
    for i in range(runs):
        rng = np.random.default_rng(seed_start + i)
        placed: list[tuple[int, int]] = []
        trades: list[tuple[int, float, int]] = []
        complete = len(eligible) > 0
        for hold in rng.permutation(np.asarray(holding_times, dtype=int)) if complete else []:
            for _ in range(retry_limit):
                day = int(rng.choice(eligible))
                end = day + int(hold)
                if end > p1:
                    continue
                if all(end <= start - 1 or day >= stop + 1 for start, stop in placed):
                    placed.append((day, end))
                    ret = (1 - cost) * opens[end] / opens[day] * (1 - cost) - 1
                    trades.append((day, float(ret), int(hold)))
                    break
            else:
                complete = False
                break
        if not complete:
            discarded += 1
            continue
        averages.append(float(np.mean([ret for _, ret, _ in trades])))
        if record_trades:
            kept.append(trades)
    return RandomEntryResult(averages, runs - discarded, discarded, kept)

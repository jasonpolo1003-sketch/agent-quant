"""Engine vs independent reference on random synthetic days (must agree exactly)."""

from __future__ import annotations

import random

import pytest
from futures_day_builder import random_day

from quant_brain.futures import orb, orb_reference

DAYS = 12_000


@pytest.mark.parametrize("seed", range(4))
def test_engine_matches_reference_on_random_days(seed):
    rng = random.Random(seed)
    statuses: dict[str, int] = {}
    for _ in range(DAYS // 4):
        day = random_day(rng)
        expected = orb_reference.simulate_day(day)
        actual = orb.simulate_day(day)
        assert actual == expected, day
        statuses[actual.status] = statuses.get(actual.status, 0) + 1
    # The generator must exercise the interesting paths, not just quiet days.
    assert {"traded", "no_trade", "void_range", "non_evaluable"} <= set(statuses)


def test_random_days_exercise_every_exit_and_flag():
    rng = random.Random(99)
    seen = set()
    for _ in range(3_000):
        result = orb.simulate_day(random_day(rng))
        for trade in result.trades:
            seen.add(trade.exit_reason)
            seen.add("entry_bar_stop" if trade.entry_bar_stop else "later_exit")
            seen.add("gap_affected" if trade.gap_affected else "clean")
            seen.add("two_trades" if len(result.trades) == 2 else "one_trade")
        seen.update(kind for kind, _ in result.events)
    assert {
        "stop",
        "gap_stop",
        "flatten",
        "entry_bar_stop",
        "gap_affected",
        "two_trades",
        "entry_missing",
    } <= seen

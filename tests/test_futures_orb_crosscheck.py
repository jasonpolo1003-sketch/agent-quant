"""Engine vs independent reference on random synthetic days (must agree exactly)."""

from __future__ import annotations

import random
from datetime import date, time

import pytest

from quant_brain.futures import orb, orb_reference
from quant_brain.futures.orb import DayInput, minute_span

DAYS = 12_000


def random_day(rng: random.Random) -> DayInput:
    exit_minute = time(12, 12) if rng.random() < 0.1 else time(15, 7)
    gap_rate = rng.choice([0.0, 0.0, 0.002, 0.02, 0.1])
    jump_rate = rng.choice([0.0, 0.01, 0.05])
    price = 10_000
    bars = {}
    for minute in minute_span(time(8, 30), exit_minute):
        open_ = price + (rng.randint(-15, 15) if rng.random() < jump_rate else rng.randint(-1, 1))
        close = open_ + rng.randint(-4, 4)
        high = max(open_, close) + rng.randint(0, 3)
        low = min(open_, close) - rng.randint(0, 3)
        price = close
        if rng.random() >= gap_rate:
            bars[minute] = (open_, high, low, close)
    if rng.random() < 0.05:
        bars.pop(exit_minute, None)  # missing flatten bar
    return DayInput(
        trade_date=date(2020, 1, 2),
        root=rng.choice(["MNQ", "MES"]),
        bars=bars,
        exit_minute=exit_minute,
        stop_ticks=None if rng.random() < 0.01 else rng.randint(1, 12),
    )


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

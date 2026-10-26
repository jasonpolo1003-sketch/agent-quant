"""Synthetic SC-FUT-0001 day builder shared by the futures fixture tests."""

from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta

from quant_brain.futures.orb import DayInput, minute_span

RANGE_BAR = (105, 110, 100, 105)


def t(hhmm: str) -> time:
    return datetime.strptime(hhmm, "%H:%M").time()


def make_day(
    bars: dict[str, tuple[int, int, int, int]] | None = None,
    *,
    missing: tuple[str, ...] = (),
    exit_minute: str = "15:07",
    stop_ticks: int | None = 4,
    root: str = "MNQ",
) -> DayInput:
    """08:30..exit; unlisted minutes are flat at the previous close."""
    listed = {t(k): v for k, v in (bars or {}).items()}
    listed.setdefault(t("08:30"), RANGE_BAR)
    gone = {t(m) for m in missing}
    out: dict[time, tuple[int, int, int, int]] = {}
    previous_close = RANGE_BAR[3]
    minute = datetime.combine(date(2020, 1, 2), t("08:30"))
    end = datetime.combine(date(2020, 1, 2), t(exit_minute))
    while minute <= end:
        key = minute.time()
        bar = listed.get(key, (previous_close,) * 4)
        if key not in gone:
            out[key] = bar
        previous_close = bar[3]
        minute += timedelta(minutes=1)
    return DayInput(
        trade_date=date(2020, 1, 2),
        root=root,
        bars=out,
        exit_minute=t(exit_minute),
        stop_ticks=stop_ticks,
    )


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

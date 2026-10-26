"""Synthetic SC-FUT-0001 day builder shared by the futures fixture tests."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from quant_brain.futures.orb import DayInput

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

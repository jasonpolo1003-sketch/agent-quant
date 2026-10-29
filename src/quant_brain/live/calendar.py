"""NYSE session calendar for live and forward use: the frozen backtest calendar plus a live one.

brain/_system/futures/session-calendar.v1.csv (futures/runner.CALENDAR) is frozen and ends
2026-10-21. brain/_system/futures/session-calendar.live.v1.csv continues it, same format,
from 2026-10-22 to 2027-12-31: every weekday except NYSE full holidays; NYSE early closes
(1:00 p.m. ET = 12:00 CT) carry the same 12:15 / 12:12 / True values as the frozen file.

Source: NYSE "Holidays & Trading Hours", https://www.nyse.com/markets/hours-calendars
(read 2026-10-29). Full closes: 2026-11-26 Thanksgiving, 2026-12-25 Christmas; 2027-01-01,
01-18, 02-15, 03-26 (Good Friday), 05-31, 06-18 (Juneteenth observed), 07-05 (Independence
Day observed), 09-06, 11-25, 12-24 (Christmas observed). Early closes: 2026-11-27,
2026-12-24, 2027-11-26. CME equity futures still trade on some NYSE holidays (Thanksgiving
to 12:00 CT); those days are not sessions here, as in the backtest.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from quant_brain.config import PROJECT_ROOT
from quant_brain.futures.bars import CalendarDay, read_calendar
from quant_brain.futures.runner import CALENDAR

LIVE_CALENDAR = "brain/_system/futures/session-calendar.live.v1.csv"
NYSE_SOURCE = "https://www.nyse.com/markets/hours-calendars"


def sessions(root: Path = PROJECT_ROOT) -> dict[date, CalendarDay]:
    """Every known NYSE session: frozen calendar, then the live one (which must follow it)."""
    frozen = read_calendar(root / CALENDAR)
    live = read_calendar(root / LIVE_CALENDAR)
    if live and frozen and live[0].trade_date <= frozen[-1].trade_date:
        raise ValueError("the live calendar overlaps the frozen one")
    return {c.trade_date: c for c in [*frozen, *live]}


def last_day(root: Path = PROJECT_ROOT) -> date:
    return max(sessions(root))

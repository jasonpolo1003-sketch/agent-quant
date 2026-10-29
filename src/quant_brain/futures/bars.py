"""Minute bars -> SC-FUT-0001 day inputs, following the frozen spec.

Reads a Databento OHLCV-1m DBN file into integer ticks, maps each NYSE session
of the frozen calendar to its D-ROLL-01 dated contract, and computes the ATR
stop distance from that contract's 15 prior sessions (high/low over the whole
CME trade date; close = last bar starting before the regular-hours close).
"""

from __future__ import annotations

import csv
import struct
from collections.abc import Iterator
from dataclasses import dataclass, replace
from datetime import date, time
from pathlib import Path

import numpy as np
import pandas as pd
import zstandard

from quant_brain.futures.orb import Bar, DayInput, stop_from_sum, true_range_sum
from quant_brain.futures.session_audit import (
    CHICAGO,
    RECORD,
    contract_on,
    instrument_for,
    read_mappings,
    selected_contracts,
)

FIXED_PRICE_PER_TICK = 250_000_000  # 0.25 point in DBN 1e-9 fixed point
REGULAR_CLOSE = time(15, 0)
EARLY_CLOSE = time(12, 15)
RANGE_START = time(8, 30)


@dataclass(frozen=True)
class CalendarDay:
    trade_date: date
    exit_minute: time
    early_close: bool

    @property
    def regular_close(self) -> time:
        return EARLY_CLOSE if self.early_close else REGULAR_CLOSE


def read_calendar(path: Path) -> list[CalendarDay]:
    with path.open(encoding="utf-8", newline="") as handle:
        return [
            CalendarDay(
                date.fromisoformat(row["trade_date"]),
                time.fromisoformat(row["exit_minute_ct"]),
                row["early_close"] == "True",
            )
            for row in csv.DictReader(handle)
        ]


def read_tick_bars(path: Path, instruments: set[int]) -> pd.DataFrame:
    """instrument_id, CT minute, CME trade date and OHLC in integer ticks.

    Keeps only `instruments` (outright contracts); calendar spreads trade on a
    different grid and are never used.
    """
    with path.open("rb") as handle:
        raw = zstandard.ZstdDecompressor().stream_reader(handle).read()
    (meta_len,) = struct.unpack_from("<I", raw, 4)
    records = np.frombuffer(memoryview(raw)[8 + meta_len :], dtype=RECORD)
    records = records[np.isin(records["instrument_id"], list(instruments))]
    ohlc = records["ohlc"]
    if np.any(ohlc % FIXED_PRICE_PER_TICK):
        raise ValueError(f"{path.name}: outright prices off the 0.25 tick grid")
    ticks = ohlc // FIXED_PRICE_PER_TICK
    minute = pd.to_datetime(records["ts_event"].astype("int64"), utc=True).tz_convert(CHICAGO)
    # Bars from 17:00 CT belong to the next Globex trade date.
    trade_date = (minute + pd.Timedelta(hours=7)).date
    frame = pd.DataFrame(
        {
            "instrument_id": records["instrument_id"],
            "minute": minute,
            "trade_date": trade_date,
            "open": ticks[:, 0],
            "high": ticks[:, 1],
            "low": ticks[:, 2],
            "close": ticks[:, 3],
            "volume": records["volume"].astype("int64"),
        }
    )
    if frame.duplicated(["instrument_id", "minute"]).any():
        raise ValueError(f"{path.name}: duplicate minute bars for one instrument")
    # Session closes take the last bar, so order explicitly rather than trusting the file.
    return frame.sort_values(["instrument_id", "minute"], kind="stable", ignore_index=True)


@dataclass(frozen=True)
class _Session:
    high: int
    low: int
    close: int | None
    minutes: dict[time, Bar]
    volumes: dict[time, int]


def _sessions(
    frame: pd.DataFrame, calendar: dict[date, CalendarDay]
) -> dict[tuple[int, date], _Session]:
    out = {}
    for (iid, day), group in frame.groupby(["instrument_id", "trade_date"], sort=False):
        if day not in calendar:
            continue
        close_at = calendar[day].regular_close
        same_day = group[group["minute"].dt.date == day]
        local = same_day["minute"].dt.time
        regular = same_day[(local >= RANGE_START) & (local < close_at)]
        minutes = {
            m.time(): (int(o), int(h), int(lo), int(c))
            for m, o, h, lo, c in zip(
                same_day["minute"],
                same_day["open"],
                same_day["high"],
                same_day["low"],
                same_day["close"],
                strict=True,
            )
            if m.time() >= RANGE_START
        }
        volumes = (
            {
                m.time(): int(v)
                for m, v in zip(same_day["minute"], same_day["volume"], strict=True)
                if m.time() >= RANGE_START
            }
            if "volume" in same_day
            else {}
        )
        out[(int(iid), day)] = _Session(
            high=int(group["high"].max()),
            low=int(group["low"].min()),
            close=int(regular["close"].iloc[-1]) if len(regular) else None,
            minutes=minutes,
            volumes=volumes,
        )
    return out


def build_days(
    frame: pd.DataFrame,
    mappings: dict,
    roll_csv: Path,
    calendar: list[CalendarDay],
    *,
    root: str,
    start: date,
    end: date,
    roll_column: str = "roll_trade_date",
) -> Iterator[DayInput]:
    """One DayInput per calendar session in [start, end], in order."""
    by_date = {c.trade_date: c for c in calendar}
    sessions = _sessions(frame, by_date)
    schedule = selected_contracts(roll_csv, root, roll_column)
    order = [c.trade_date for c in calendar]
    for position, day in enumerate(order):
        if not start <= day <= end:
            continue
        info = by_date[day]
        contract = contract_on(schedule, day)
        iid = instrument_for(mappings, contract, day)
        today = sessions.get((iid, day))
        prior = []
        for d in order[max(0, position - 15) : position]:
            s = sessions.get((iid, d))
            prior.append(None if s is None or s.close is None else (s.high, s.low, s.close))
        bars = {m: b for m, b in today.minutes.items() if m <= info.exit_minute} if today else {}
        total = true_range_sum(prior)
        yield DayInput(
            trade_date=day,
            root=root,
            bars=bars,
            exit_minute=info.exit_minute,
            stop_ticks=None if total is None else stop_from_sum(total),
            atr_tr_sum=total,
            prev_close=prior[-1][2] if prior and prior[-1] is not None else None,
            volumes={m: v for m, v in today.volumes.items() if m in bars} if today else {},
        )


def load_days(
    bars_path: Path, roll_csv: Path, calendar_csv: Path, *, root: str, start: date, end: date
) -> list[DayInput]:
    mappings = read_mappings(bars_path)
    outrights = {iid for intervals in mappings.values() for *_, iid in intervals}
    frame = read_tick_bars(bars_path, outrights)
    return list(
        build_days(
            frame,
            mappings,
            roll_csv,
            read_calendar(calendar_csv),
            root=root,
            start=start,
            end=end,
        )
    )


EVENING_OPEN = time(17, 0)
EVENING_END = time(20, 30)


def _evenings(frame: pd.DataFrame) -> dict[tuple[int, date], tuple[dict, dict]]:
    """(bars, volumes) of the 17:00..20:30 CT minutes per (instrument, trade date).

    Those minutes fall on the calendar day before their trade date (trade date = CT + 7h).
    """
    minute_of_day = frame["minute"].dt.hour * 60 + frame["minute"].dt.minute
    lo = EVENING_OPEN.hour * 60 + EVENING_OPEN.minute
    hi = EVENING_END.hour * 60 + EVENING_END.minute
    evening = frame[(minute_of_day >= lo) & (minute_of_day <= hi)]
    out = {}
    for (iid, day), group in evening.groupby(["instrument_id", "trade_date"], sort=False):
        bars = {
            m.time(): (int(o), int(h), int(low), int(c))
            for m, o, h, low, c in zip(
                group["minute"],
                group["open"],
                group["high"],
                group["low"],
                group["close"],
                strict=True,
            )
        }
        volumes = (
            {m.time(): int(v) for m, v in zip(group["minute"], group["volume"], strict=True)}
            if "volume" in group
            else {}
        )
        out[(int(iid), day)] = (bars, volumes)
    return out


def build_evenings(
    frame: pd.DataFrame,
    mappings: dict,
    roll_csv: Path,
    calendar: list[CalendarDay],
    *,
    root: str,
    start: date,
    end: date,
    roll_column: str = "roll_trade_date",
) -> Iterator[DayInput]:
    """`build_days`, but each day's bars (and volumes) are the 17:00..20:30 CT evening that
    starts its trade date (the previous calendar evening; Sunday's for Monday), from the same
    contract `build_days` picks for that trade date. exit_minute is 20:30; ATR and the previous
    regular close are build_days' own. build_days itself is untouched (SC-FUT-0011)."""
    evenings = _evenings(frame)
    schedule = selected_contracts(roll_csv, root, roll_column)
    for day in build_days(
        frame,
        mappings,
        roll_csv,
        calendar,
        root=root,
        start=start,
        end=end,
        roll_column=roll_column,
    ):
        iid = instrument_for(mappings, contract_on(schedule, day.trade_date), day.trade_date)
        bars, volumes = evenings.get((iid, day.trade_date), ({}, {}))
        yield replace(day, bars=bars, volumes=volumes, exit_minute=EVENING_END, stop_ticks=None)


OVERNIGHT_OPEN = time(17, 0)
OVERNIGHT_EXIT = time(8, 29)


def _overnights(frame: pd.DataFrame) -> dict[tuple[int, date], tuple[dict, dict]]:
    """(bars, volumes) of the 17:00..08:29 CT minutes per (instrument, trade date).

    The 17:00..23:59 minutes fall on the calendar day before their trade date (Sunday for
    Monday), the 00:00..08:29 minutes on the trade date itself (trade date = CT + 7h). The two
    halves never share a clock time, so keying by time stays unique.
    """
    minute_of_day = frame["minute"].dt.hour * 60 + frame["minute"].dt.minute
    lo = OVERNIGHT_OPEN.hour * 60 + OVERNIGHT_OPEN.minute
    hi = OVERNIGHT_EXIT.hour * 60 + OVERNIGHT_EXIT.minute
    night = frame[(minute_of_day >= lo) | (minute_of_day <= hi)]
    out = {}
    for (iid, day), group in night.groupby(["instrument_id", "trade_date"], sort=False):
        bars = {
            m.time(): (int(o), int(h), int(low), int(c))
            for m, o, h, low, c in zip(
                group["minute"],
                group["open"],
                group["high"],
                group["low"],
                group["close"],
                strict=True,
            )
        }
        volumes = (
            {m.time(): int(v) for m, v in zip(group["minute"], group["volume"], strict=True)}
            if "volume" in group
            else {}
        )
        out[(int(iid), day)] = (bars, volumes)
    return out


def _weekday_gap(previous: date, day: date) -> bool:
    """A weekday strictly between two sessions that is not itself a session (a holiday)."""
    return any(
        date.fromordinal(n).weekday() < 5 for n in range(previous.toordinal() + 1, day.toordinal())
    )


def build_overnights(
    frame: pd.DataFrame,
    mappings: dict,
    roll_csv: Path,
    calendar: list[CalendarDay],
    *,
    root: str,
    start: date,
    end: date,
    roll_column: str = "roll_trade_date",
) -> Iterator[DayInput]:
    """`build_days`, but each day's bars (and volumes) are the 17:00..08:29 CT overnight that
    ends at its 08:30 open (from the previous calendar evening's 17:00 reopen; Sunday's for
    Monday), from the same contract `build_days` picks for that trade date. exit_minute is
    08:29; ATR and the previous regular close are build_days' own (SC-FUT-0012).

    context: `previous_session` (the previous NYSE session P, None for the first calendar
    day), `holiday_gap` (a non-session weekday lies between P and D: spec "missing", addendum
    1 item 1) and P's `previous_rth` = (open of its 08:30 bar, close of its last bar before the
    regular close), on D's contract, each None if missing. build_days is untouched.
    """
    nights = _overnights(frame)
    by_date = {c.trade_date: c for c in calendar}
    sessions = _sessions(frame, by_date)
    order = [c.trade_date for c in calendar]
    position = {d: i for i, d in enumerate(order)}
    schedule = selected_contracts(roll_csv, root, roll_column)
    for day in build_days(
        frame,
        mappings,
        roll_csv,
        calendar,
        root=root,
        start=start,
        end=end,
        roll_column=roll_column,
    ):
        iid = instrument_for(mappings, contract_on(schedule, day.trade_date), day.trade_date)
        bars, volumes = nights.get((iid, day.trade_date), ({}, {}))
        i = position[day.trade_date]
        previous = order[i - 1] if i else None
        prior = sessions.get((iid, previous)) if previous else None
        first = prior.minutes.get(RANGE_START) if prior else None
        context = {
            "previous_session": previous,
            "holiday_gap": previous is not None and _weekday_gap(previous, day.trade_date),
            "previous_rth": (
                None if first is None else first[0],
                None if prior is None else prior.close,
            ),
        }
        yield replace(
            day,
            bars=bars,
            volumes=volumes,
            exit_minute=OVERNIGHT_EXIT,
            stop_ticks=None,
            context=context,
        )

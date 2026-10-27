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
from dataclasses import dataclass
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
        out[(int(iid), day)] = _Session(
            high=int(group["high"].max()),
            low=int(group["low"].min()),
            close=int(regular["close"].iloc[-1]) if len(regular) else None,
            minutes=minutes,
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

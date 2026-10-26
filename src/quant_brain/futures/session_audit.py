"""Outcome-blind session eligibility and coverage audit for SC-FUT-0001.

Reads only the development-only partition. It checks which one-minute bars
exist for the D-ROLL-01 contract on each cash-open session; it never computes
ranges, breakouts, prices or P&L. Calendars come from pandas_market_calendars
(NYSE for the 08:30 CT cash open, CME_Equity for Globex closes), a versioned
secondary source, and are cross-checked against bar presence.
"""

from __future__ import annotations

import csv
import struct
from dataclasses import dataclass
from datetime import date, time, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pandas_market_calendars as pmc
import zstandard

CHICAGO = "America/Chicago"
RANGE_START = time(8, 30)
RANGE_MINUTES = 15
SIGNAL_START = time(8, 45)
NORMAL_EXIT = time(15, 7)
GLOBEX_OPEN = time(17, 0)
# pandas_market_calendars 5.5.0 gives a 12:00 CT CME_Equity close on early-close days, but
# every such dev/diagnostic session has MNQ/MES bars through 12:14 CT and CME's 2011
# holiday notice states 12:15 CT for Globex equity indexes. Pending official confirmation.
EQUITY_EARLY_CLOSE = time(12, 15)
EARLY_EXIT_LEAD = timedelta(minutes=3)
ATR_SESSIONS = 14
OHLCV_RTYPES = {0x20, 0x21, 0x22, 0x23}
# DBN OHLCV record: length, rtype, publisher_id, instrument_id, ts_event, OHLC, volume.
RECORD = np.dtype(
    [
        ("length", "u1"),
        ("rtype", "u1"),
        ("publisher_id", "<u2"),
        ("instrument_id", "<u4"),
        ("ts_event", "<u8"),
        ("ohlc", "<i8", 4),
        ("volume", "<u8"),
    ]
)


def read_bar_keys(path: Path) -> pd.DataFrame:
    """instrument_id and Chicago minute of every bar; prices are discarded unread."""
    with path.open("rb") as handle:
        raw = zstandard.ZstdDecompressor().stream_reader(handle).read()
    if raw[:3] != b"DBN":
        raise ValueError(f"{path.name}: not a DBN stream")
    (meta_len,) = struct.unpack_from("<I", raw, 4)
    body = memoryview(raw)[8 + meta_len :]
    if len(body) % RECORD.itemsize:
        raise ValueError(f"{path.name}: body is not whole {RECORD.itemsize}-byte OHLCV records")
    records = np.frombuffer(body, dtype=RECORD)
    if not set(np.unique(records["rtype"]).tolist()) <= OHLCV_RTYPES:
        raise ValueError(f"{path.name}: non-OHLCV records present")
    minute = pd.to_datetime(records["ts_event"].astype("int64"), utc=True).tz_convert(CHICAGO)
    return pd.DataFrame({"instrument_id": records["instrument_id"], "minute": minute})


def read_mappings(path: Path) -> dict[str, list[tuple[date, date, int]]]:
    """Outright raw symbol -> [(start, end_exclusive, instrument_id)] from DBN metadata."""
    import databento_dbn as dbn

    with path.open("rb") as handle:
        head = zstandard.ZstdDecompressor().stream_reader(handle).read(1 << 20)
    metadata = dbn.DBNDecoder(upgrade_policy=dbn.VersionUpgradePolicy.AS_IS).write_and_decode(head)[
        0
    ]
    return {
        symbol: [(m["start_date"], m["end_date"], int(m["symbol"])) for m in intervals]
        for symbol, intervals in metadata.mappings.items()
        if "-" not in symbol
    }


def instrument_for(mappings: dict, symbol: str, day: date) -> int | None:
    for start, end, iid in mappings.get(symbol, []):
        if start <= day < end:
            return iid
    return None


def selected_contracts(roll_csv: Path, root: str) -> list[tuple[date, str]]:
    """D-ROLL-01: [(first trade date, contract)], ordered."""
    with roll_csv.open(encoding="utf-8") as handle:
        rows = [r for r in csv.DictReader(handle) if r["root"] == root]
    rows.sort(key=lambda r: r["roll_trade_date"])
    schedule = [(date.min, rows[0]["from_contract"])]
    schedule += [(date.fromisoformat(r["roll_trade_date"]), r["to_contract"]) for r in rows]
    return schedule


def contract_on(schedule: list[tuple[date, str]], day: date) -> str:
    current = schedule[0][1]
    for start, contract in schedule:
        if start <= day:
            current = contract
    return current


@dataclass(frozen=True)
class SessionRow:
    root: str
    trade_date: str
    period: str
    contract: str
    instrument_id: int | None
    cme_close_ct: str
    exit_minute_ct: str
    expected_minutes: int
    missing_minutes: int
    missing_in_live_window: int
    range_complete: bool
    exit_bar_present: bool
    first_bar_ct: str
    last_bar_ct: str
    atr_prior_sessions_with_bars: int
    atr_eligible: bool
    flags: str


def _minutes(day: date, start: time, end_inclusive: time) -> pd.DatetimeIndex:
    lo = pd.Timestamp.combine(day, start).tz_localize(CHICAGO)
    hi = pd.Timestamp.combine(day, end_inclusive).tz_localize(CHICAGO)
    return pd.date_range(lo, hi, freq="min")


def audit_sessions(
    bars: pd.DataFrame,
    mappings: dict,
    roll_csv: Path,
    *,
    root: str,
    start: date,
    end: date,
    dev_end: date,
) -> list[SessionRow]:
    nyse = pmc.get_calendar("NYSE").schedule(start - timedelta(days=40), end, tz=CHICAGO)
    cme = pmc.get_calendar("CME_Equity").schedule(start - timedelta(days=40), end, tz=CHICAGO)
    schedule = selected_contracts(roll_csv, root)
    keyed = bars.assign(day=bars["minute"].dt.date)
    by_day = {key: set(group["minute"]) for key, group in keyed.groupby(["instrument_id", "day"])}
    sessions = [ts.date() for ts in nyse.index]
    rows = []
    for position, day in enumerate(sessions):
        if day < start:
            continue
        contract = contract_on(schedule, day)
        iid = instrument_for(mappings, contract, day)
        have = by_day.get((iid, day), set())
        flags = []
        if pd.Timestamp(day) not in cme.index:
            flags.append("nyse_open_cme_closed")
            close = pd.Timestamp.combine(day, time(15, 0)).tz_localize(CHICAGO)
        else:
            close = cme.loc[pd.Timestamp(day), "market_close"]
        early = close.time() < time(15, 10)
        if early and close.time() != EQUITY_EARLY_CLOSE:
            flags.append(f"calendar_close_{close.strftime('%H%M')}_overridden")
            close = pd.Timestamp.combine(day, EQUITY_EARLY_CLOSE).tz_localize(CHICAGO)
        exit_at = (close - EARLY_EXIT_LEAD).time() if early else NORMAL_EXIT
        window = _minutes(day, RANGE_START, exit_at)
        present = [m in have for m in window]
        live = [ok for m, ok in zip(window, present, strict=True) if m.time() >= SIGNAL_START]
        # Bars from 17:00 CT belong to the next Globex trade date.
        day_bars = sorted(m for m in have if RANGE_START <= m.time() < GLOBEX_OPEN)
        if not any(present):
            flags.append("no_bars_in_cash_window")
        if early:
            flags.append("early_close")
            after = [m for m in day_bars if m >= close]
            if after:
                flags.append(f"bars_after_calendar_close:{len(after)}")
        prior = sessions[max(0, position - ATR_SESSIONS) : position]
        with_bars = sum(
            1
            for d in prior
            if any(RANGE_START <= m.time() <= time(15, 0) for m in by_day.get((iid, d), ()))
        )
        rows.append(
            SessionRow(
                root=root,
                trade_date=day.isoformat(),
                period="development" if day <= dev_end else "diagnostics",
                contract=contract,
                instrument_id=iid,
                cme_close_ct=close.strftime("%H:%M"),
                exit_minute_ct=exit_at.strftime("%H:%M"),
                expected_minutes=len(window),
                missing_minutes=present.count(False),
                missing_in_live_window=live.count(False),
                range_complete=all(present[:RANGE_MINUTES]),
                exit_bar_present=present[-1],
                first_bar_ct=day_bars[0].strftime("%H:%M") if day_bars else "",
                last_bar_ct=day_bars[-1].strftime("%H:%M") if day_bars else "",
                atr_prior_sessions_with_bars=with_bars,
                atr_eligible=len(prior) == ATR_SESSIONS and with_bars == ATR_SESSIONS,
                flags=";".join(flags),
            )
        )
    return rows


def summarize(rows: list[SessionRow]) -> dict[str, object]:
    out: dict[str, object] = {}
    for period in ("development", "diagnostics"):
        part = [r for r in rows if r.period == period]
        if not part:
            continue
        candidate = [r for r in part if r.atr_eligible and r.range_complete]
        n = len(candidate)
        out[period] = {
            "nyse_cash_sessions": len(part),
            "atr_warmup_ineligible": sum(not r.atr_eligible for r in part),
            "range_incomplete": sum(not r.range_complete for r in part),
            "candidate_sessions_atr_and_range_ok": n,
            "candidate_with_any_missing_minute_in_live_window": sum(
                r.missing_in_live_window > 0 for r in candidate
            ),
            "candidate_share_with_missing_live_minute": (
                round(sum(r.missing_in_live_window > 0 for r in candidate) / n, 4) if n else None
            ),
            "candidate_missing_exit_bar": sum(not r.exit_bar_present for r in candidate),
            "early_close_sessions": sum("early_close" in r.flags for r in part),
            "flagged_bars_after_calendar_close": sum(
                "bars_after_calendar_close" in r.flags for r in part
            ),
            "no_bars_in_cash_window": sum("no_bars_in_cash_window" in r.flags for r in part),
        }
    return out

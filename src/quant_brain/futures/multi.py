"""Day inputs for the extra markets bought 2026-10-28 (bigger-edge plan B2).

ZN, 6E, GC, ZC outright 1-minute bars (practice 2019-05..2024-12). Gold and euro are
traded as their micros (MGC = 1/10 GC, M6E = 1/10 6E) on the full contract's prices.

- Sessions: each market's published day-session (pit) hours in CT, fixed before any
  result. MNQ keeps its own (08:30-15:00). Flat at the open of the session-close bar;
  ZC stops trading at 13:20, so it flattens at the 13:15 bar.
- Days: the frozen session calendar, minus its early-close days (holiday hours differ
  by exchange; skipping them is decided by the calendar, never by results).
- Roll: volume roll, as the independent rebuild: after a trade date on which the next
  contract out-traded the current one (whole Globex day), switch from the next session.
- prev_close: the close of the last bar before the session close on the previous
  calendar session, same contract.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from datetime import date, time
from pathlib import Path

import numpy as np
import pandas as pd
import zstandard

from quant_brain.futures.bars import read_calendar
from quant_brain.futures.orb import DayInput
from quant_brain.futures.session_audit import CHICAGO, RECORD, read_mappings

MONTH_CODES = "FGHJKMNQUVXZ"


@dataclass(frozen=True)
class Spec:
    data_root: str  # root in the Databento files
    tick_nano: int  # price grid of the data, DBN 1e-9 fixed point
    open: time
    close: time  # session close; last check is <= close - 30 min
    flat: time  # flatten at this bar's open


SPECS = {
    "ZN": Spec("ZN", 15_625_000, time(7, 20), time(14, 0), time(14, 0)),
    "M6E": Spec("6E", 50_000, time(7, 20), time(14, 0), time(14, 0)),
    "MGC": Spec("GC", 100_000_000, time(7, 20), time(12, 30), time(12, 30)),
    "ZC": Spec("ZC", 250_000_000, time(8, 30), time(13, 20), time(13, 15)),
}


def bars_file(data_dir: Path, market: str) -> Path:
    return data_dir / f"glbx-mdp3_ohlcv-1m_{SPECS[market].data_root}_20190501-20241231.dbn.zst"


def _expiry_key(symbol: str) -> tuple[int, int]:
    year = 2019 if symbol[-1] == "9" else 2020 + int(symbol[-1])
    return year, MONTH_CODES.index(symbol[-2])


def read_bars(path: Path, tick_nano: int) -> tuple[pd.DataFrame, dict[int, str]]:
    """All outright minute bars in integer ticks, CT minute and CME trade date; iid -> symbol."""
    mappings = read_mappings(path)
    symbol_of = {iid: s for s, intervals in mappings.items() for *_, iid in intervals}
    with path.open("rb") as handle:
        raw = zstandard.ZstdDecompressor().stream_reader(handle).read()
    (meta_len,) = struct.unpack_from("<I", raw, 4)
    records = np.frombuffer(memoryview(raw)[8 + meta_len :], dtype=RECORD)
    records = records[np.isin(records["instrument_id"], list(symbol_of))]
    ohlc = records["ohlc"]
    if np.any(ohlc % tick_nano):
        raise ValueError(f"{path.name}: outright prices off the tick grid")
    ticks = ohlc // tick_nano
    minute = pd.to_datetime(records["ts_event"].astype("int64"), utc=True).tz_convert(CHICAGO)
    frame = pd.DataFrame(
        {
            "iid": records["instrument_id"].astype("int64"),
            "minute": minute,
            "trade_date": (minute + pd.Timedelta(hours=7)).date,  # 17:00 CT starts the next date
            "open": ticks[:, 0],
            "high": ticks[:, 1],
            "low": ticks[:, 2],
            "close": ticks[:, 3],
            "volume": records["volume"].astype("int64"),
        }
    )
    if frame.duplicated(["iid", "minute"]).any():
        raise ValueError(f"{path.name}: duplicate minute bars for one instrument")
    return frame.sort_values(["iid", "minute"], kind="stable", ignore_index=True), symbol_of


def volume_roll(frame: pd.DataFrame, symbol_of: dict[int, str], days: list[date]) -> dict[date, int]:
    """Contract (iid) traded on each day; decisions use only completed earlier trade dates."""
    volume = frame.groupby(["iid", "trade_date"])["volume"].sum().to_dict()
    chain = sorted(symbol_of, key=lambda iid: _expiry_key(symbol_of[iid]))
    cur, out = 0, {}
    for day in days:
        out[day] = chain[cur]
        nxt = chain[cur + 1] if cur + 1 < len(chain) else None
        if nxt is not None and volume.get((nxt, day), 0) > volume.get((chain[cur], day), 0):
            cur += 1  # effective from the next session
    return out


def load_days(data_dir: Path, calendar_csv: Path, market: str, start: date, end: date) -> list[DayInput]:
    spec = SPECS[market]
    frame, symbol_of = read_bars(bars_file(data_dir, market), spec.tick_nano)
    calendar = [c for c in read_calendar(calendar_csv) if not c.early_close]
    days = [c.trade_date for c in calendar if c.trade_date <= end]
    contract = volume_roll(frame, symbol_of, days)
    local = frame["minute"].dt.time
    same_day = frame["minute"].dt.date == frame["trade_date"]
    session = frame[same_day & (local >= spec.open) & (local <= spec.flat)]
    by_key = {key: g for key, g in session.groupby(["iid", "trade_date"], sort=False)}
    out: list[DayInput] = []
    for i, day in enumerate(days):
        if day < start:
            continue
        iid = contract[day]
        today = by_key.get((iid, day))
        bars, volumes = {}, {}
        if today is not None:
            for m, o, h, lo, c, v in zip(
                today["minute"].dt.time, today["open"], today["high"], today["low"],
                today["close"], today["volume"], strict=True,
            ):
                bars[m] = (int(o), int(h), int(lo), int(c))
                volumes[m] = int(v)
        prev_close = None
        if i > 0:
            before = by_key.get((iid, days[i - 1]))
            if before is not None:
                regular = before[before["minute"].dt.time < spec.close]
                prev_close = int(regular["close"].iloc[-1]) if len(regular) else None
        out.append(
            DayInput(
                trade_date=day,
                root=market,
                bars=bars,
                exit_minute=spec.flat,
                stop_ticks=None,
                atr_tr_sum=None,
                prev_close=prev_close,
                volumes=volumes,
            )
        )
    return out

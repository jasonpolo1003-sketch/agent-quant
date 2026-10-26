"""Loader rules on a synthetic minute frame, plus a dev-data count check when present."""

from __future__ import annotations

import json
from datetime import date, time
from pathlib import Path

import pandas as pd
import pytest

from quant_brain.config import BRAIN_DIR
from quant_brain.futures.bars import CalendarDay, build_days

CT = "America/Chicago"


def _calendar(days):
    return [CalendarDay(d, time(15, 7), False) for d in days]


def _frame(days, *, evening_spike_before=None, after_close_close=None):
    rows = []
    for d in days:
        for minute in pd.date_range(f"{d} 08:30", f"{d} 15:10", freq="min", tz=CT):
            close = 1_000
            if after_close_close is not None and minute.time() == time(15, 0):
                close = after_close_close
            rows.append((7, minute, d, 1_000, 1_010, 990, close))
    if evening_spike_before is not None:
        evening = pd.Timestamp(f"{days[days.index(evening_spike_before) - 1]} 18:00", tz=CT)
        rows.append((7, evening, evening_spike_before, 1_000, 1_200, 1_000, 1_000))
    return pd.DataFrame(
        rows, columns=["instrument_id", "minute", "trade_date", "open", "high", "low", "close"]
    )


def _roll(tmp_path):
    path = tmp_path / "roll.csv"
    path.write_text(
        "root,roll_trade_date,from_contract,to_contract,from_expiration,to_instrument_id\n"
        "MNQ,2021-03-11,MNQH1,MNQM1,2021-03-19,8\n",
        encoding="utf-8",
    )
    return path


DAYS = [d.date() for d in pd.bdate_range("2021-01-04", periods=17)]
MAPPINGS = {"MNQH1": [(date(2020, 9, 1), date(2021, 3, 20), 7)]}


def test_atr_needs_fifteen_prior_sessions(tmp_path):
    days = list(
        build_days(
            _frame(DAYS),
            MAPPINGS,
            _roll(tmp_path),
            _calendar(DAYS),
            root="MNQ",
            start=DAYS[0],
            end=DAYS[-1],
        )
    )
    stops = [d.stop_ticks for d in days]
    assert stops[:15] == [None] * 15
    assert stops[15:] == [2, 2]  # TR 20 ticks -> 2.0 -> 2


def test_evening_session_counts_toward_next_trade_date(tmp_path):
    frame = _frame(DAYS, evening_spike_before=DAYS[10])
    days = list(
        build_days(
            frame,
            MAPPINGS,
            _roll(tmp_path),
            _calendar(DAYS),
            root="MNQ",
            start=DAYS[15],
            end=DAYS[15],
        )
    )
    # One session with H 1200: TR = max(210, 200, 10) = 210; (210 + 13*20) / 14 = 33.6 -> 3.36 -> 3
    assert days[0].stop_ticks == 3
    assert all(m >= time(8, 30) for m in days[0].bars)


def test_close_is_last_bar_before_regular_close(tmp_path):
    frame = _frame(DAYS, after_close_close=2_000)  # 15:00 bar must not be the close
    days = list(
        build_days(
            frame,
            MAPPINGS,
            _roll(tmp_path),
            _calendar(DAYS),
            root="MNQ",
            start=DAYS[15],
            end=DAYS[15],
        )
    )
    assert days[0].stop_ticks == 2


def test_bars_stop_at_exit_minute(tmp_path):
    days = list(
        build_days(
            _frame(DAYS),
            MAPPINGS,
            _roll(tmp_path),
            _calendar(DAYS),
            root="MNQ",
            start=DAYS[16],
            end=DAYS[16],
        )
    )
    assert max(days[0].bars) == time(15, 7) and min(days[0].bars) == time(8, 30)


DEV = Path("C:/Users/jason/OneDrive/Desktop/Quant/data/databento/dev_2019-05-01_2024-12-31")


@pytest.mark.skipif(not DEV.exists(), reason="dev partition not on this machine")
def test_loader_matches_outcome_blind_audit_counts():
    """Counts only: the loader sees exactly the minutes the audit counted."""
    from quant_brain.futures.bars import load_days

    futures = BRAIN_DIR / "_system" / "futures"
    days = load_days(
        DEV / "glbx-mdp3_ohlcv-1m_MES-MNQ-FUT_20190501-dev.dbn.zst",
        BRAIN_DIR / "sources" / "mes_mnq" / "contracts" / "roll_calendar_2019_2026.csv",
        futures / "session-calendar.v1.csv",
        root="MNQ",
        start=date(2019, 5, 1),
        end=date(2024, 12, 31),
    )
    audit = pd.read_csv(futures / "session-audit-dev.csv", keep_default_na=False)
    audit = audit[audit["root"] == "MNQ"].set_index("trade_date")
    assert len(days) == len(audit) == 1428
    for day in days:
        row = audit.loc[day.trade_date.isoformat()]
        assert row["expected_minutes"] - row["missing_minutes"] == len(day.bars)
    summary = json.loads((futures / "session-audit-dev.json").read_text(encoding="utf-8"))
    audit_ok = (
        summary["MNQ"]["development"]["nyse_cash_sessions"]
        - summary["MNQ"]["development"]["atr_warmup_ineligible"]
    )
    loader_ok = sum(d.stop_ticks is not None for d in days if d.trade_date.year < 2024)
    assert audit_ok - 2 <= loader_ok <= audit_ok  # 15 closes required vs the audit's 14 sessions

"""Synthetic tests for the outcome-blind session coverage audit."""

from __future__ import annotations

from datetime import date, time

import pandas as pd

from quant_brain.futures.session_audit import (
    audit_sessions,
    contract_on,
    instrument_for,
    selected_contracts,
    summarize,
)


def _roll_csv(tmp_path):
    path = tmp_path / "roll.csv"
    path.write_text(
        "root,roll_trade_date,from_contract,to_contract,from_expiration,to_instrument_id\n"
        "MNQ,2019-12-12,MNQZ9,MNQH0,2019-12-20,2\n",
        encoding="utf-8",
    )
    return path


def _bars(iid: int, days: list[date], *, drop: set[pd.Timestamp] = frozenset()) -> pd.DataFrame:
    minutes = []
    for day in days:
        lo = pd.Timestamp.combine(day, time(8, 0)).tz_localize("America/Chicago")
        minutes += [m for m in pd.date_range(lo, periods=8 * 60, freq="min") if m not in drop]
    return pd.DataFrame({"instrument_id": iid, "minute": minutes})


def test_roll_schedule_switches_on_roll_date(tmp_path):
    schedule = selected_contracts(_roll_csv(tmp_path), "MNQ")
    assert contract_on(schedule, date(2019, 12, 11)) == "MNQZ9"
    assert contract_on(schedule, date(2019, 12, 12)) == "MNQH0"


def test_instrument_mapping_respects_interval():
    mappings = {"MNQZ9": [(date(2019, 9, 1), date(2019, 12, 21), 1)]}
    assert instrument_for(mappings, "MNQZ9", date(2019, 12, 20)) == 1
    assert instrument_for(mappings, "MNQZ9", date(2019, 12, 21)) is None


def test_warmup_range_gap_and_early_close(tmp_path):
    days = [d.date() for d in pd.bdate_range("2019-11-01", "2019-11-29")]
    days = [d for d in days if d != date(2019, 11, 28)]  # Thanksgiving: no cash session
    gap = pd.Timestamp("2019-11-27 10:00", tz="America/Chicago")
    bars = _bars(1, days, drop={gap})
    mappings = {"MNQZ9": [(date(2019, 9, 1), date(2019, 12, 21), 1)]}
    rows = audit_sessions(
        bars,
        mappings,
        _roll_csv(tmp_path),
        root="MNQ",
        start=date(2019, 11, 1),
        end=date(2019, 11, 29),
        dev_end=date(2023, 12, 31),
    )
    by_day = {r.trade_date: r for r in rows}
    assert "2019-11-28" not in by_day
    assert not by_day["2019-11-01"].atr_eligible  # no prior bars
    assert by_day["2019-11-21"].atr_eligible  # 14 prior sessions with bars
    assert by_day["2019-11-27"].missing_in_live_window == 1
    friday = by_day["2019-11-29"]
    assert friday.exit_minute_ct == "12:12" and "early_close" in friday.flags
    assert friday.range_complete and friday.exit_bar_present
    summary = summarize(rows)["development"]
    assert summary["candidate_with_any_missing_minute_in_live_window"] == 1

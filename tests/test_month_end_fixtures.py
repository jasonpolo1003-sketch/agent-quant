"""SC-FUT-0013 hand-worked fixtures: month-end rebalancing (T1) and turn of the month (T2).

Spec v1 + addendum 1. Synthetic MES days (125 cents/tick, L3 622). Unlisted minutes are flat
at the previous bar's close (tests/futures_day_builder.make_day).
"""

from __future__ import annotations

import dataclasses
from datetime import date, time
from fractions import Fraction

import numpy as np
import pandas as pd
import pytest
from futures_day_builder import make_day, t

from quant_brain.config import PROJECT_ROOT
from quant_brain.futures import runner
from quant_brain.futures.bars import CalendarDay, read_calendar
from quant_brain.futures.orb import DayInput
from quant_brain.workbench import analysis, engine
from quant_brain.workbench.month_end import (
    MonthEnd,
    Signal,
    always_long_other,
    attach,
    chained_return,
    hit_rate_by_side,
    mes_leg,
    month_positions,
    month_signals,
    per_year,
    spec_verdict,
    zn_leg,
)
from quant_brain.workbench.strategies import DESCRIPTIONS, GRADING, REGISTRY, make

T1 = MonthEnd("T1_rebalance")
T2 = MonthEnd("T2_turn_of_month")
DAY = date(2021, 3, 29)


def calendar_sessions() -> list[date]:
    cal = read_calendar(PROJECT_ROOT / runner.CALENDAR)
    return [c.trade_date for c in cal if c.trade_date <= date(2024, 12, 31)]


def mday(
    listed=None, *, position="L", rel=Fraction(1, 100), exit_minute="15:07", missing=(), root="MES"
):
    d = make_day(listed or {}, exit_minute=exit_minute, missing=missing, root=root, stop_ticks=None)
    return dataclasses.replace(
        d, trade_date=DAY, context={"position": position, "rel": rel, "signal": None}
    )


# ---------------------------------------------------------------- month positions


def test_p1_positions_on_the_frozen_calendar():
    pos = month_positions(calendar_sessions())
    want = {
        # May 2021 ends on Memorial Day (Mon 31): L is Fri 28
        date(2021, 5, 25): "L-3",
        date(2021, 5, 26): "L-2",
        date(2021, 5, 27): "L-1",
        date(2021, 5, 28): "L",
        date(2021, 6, 1): "F1",
        date(2021, 6, 2): "F2",
        date(2021, 6, 3): "F3",
        # Nov 2019: L is the 12:15 early close of Fri 29 (Thanksgiving Thu 28 is not a session)
        date(2019, 11, 25): "L-3",
        date(2019, 11, 26): "L-2",
        date(2019, 11, 27): "L-1",
        date(2019, 11, 29): "L",
        # March 2024 ends on Good Friday (29): L is Thu 28
        date(2024, 3, 28): "L",
        date(2024, 3, 25): "L-3",
        # Jan 2020: New Year's Day is a holiday, F1 is Jan 2
        date(2020, 1, 2): "F1",
        date(2020, 1, 6): "F3",
        # first calendar month starts on its first session; last practice month is complete
        date(2019, 5, 1): "F1",
        date(2024, 12, 26): "L-3",
        date(2024, 12, 27): "L-2",
        date(2024, 12, 30): "L-1",
        date(2024, 12, 31): "L",
    }
    assert {d: pos.get(d) for d in want} == want
    assert pos.get(date(2019, 11, 22)) is None and pos.get(date(2021, 6, 4)) is None
    # Dec 2020: the 24th (early close) is L-4, so no label
    assert pos.get(date(2020, 12, 24)) is None and pos[date(2020, 12, 28)] == "L-3"
    # every month May 2019..Dec 2024 has exactly 7 labelled sessions, each once
    counts: dict[tuple[int, int], list[str]] = {}
    for d, p in pos.items():
        counts.setdefault((d.year, d.month), []).append(p)
    assert len(counts) == 68
    assert all(sorted(v) == ["F1", "F2", "F3", "L", "L-1", "L-2", "L-3"] for v in counts.values())


def test_p2_months_cut_by_the_session_list_are_not_labelled():
    # starts mid-month (weekday 1 Jun 2021 missing) and ends mid-month: neither edge labelled
    days = [d for d in calendar_sessions() if date(2021, 6, 2) <= d <= date(2021, 8, 10)]
    pos = month_positions(days)
    assert pos.get(date(2021, 6, 2)) is None and pos[date(2021, 6, 30)] == "L"
    assert pos[date(2021, 7, 1)] == "F1" and pos[date(2021, 8, 2)] == "F1"
    assert pos.get(date(2021, 8, 10)) is None
    assert not any(p.startswith("L") and d.month == 8 for d, p in pos.items())


# ---------------------------------------------------------------- the T1 signal


D = [date(2021, 3, k) for k in (1, 2, 3, 4, 5)]


def test_s1_no_roll_is_end_over_start():
    front = dict.fromkeys(D, "A")
    closes = {("A", D[0]): 4_000, ("A", D[4]): 4_100}  # middle closes are not needed
    assert chained_return(D, front, closes) == Fraction(4_100, 4_000) - 1


def test_s2_a_roll_chains_at_the_roll_days_closes():
    # roll day = first session on the new front (D[2]): old A start->D2, new B D2->end
    front = {D[0]: "A", D[1]: "A", D[2]: "B", D[3]: "B", D[4]: "B"}
    closes = {("A", D[0]): 100, ("A", D[2]): 110, ("B", D[2]): 220, ("B", D[4]): 231}
    assert chained_return(D, front, closes) == Fraction(110, 100) * Fraction(231, 220) - 1
    assert chained_return(D, front, closes) == Fraction(155, 1_000)
    # any close the formula needs missing -> no signal
    for gone in closes:
        assert chained_return(D, front, {k: v for k, v in closes.items() if k != gone}) is None
    # a roll exactly at the end: the old segment runs to the end, the new one is 1
    late = {**dict.fromkeys(D[:4], "A"), D[4]: "B"}
    assert chained_return(D, late, {("A", D[0]): 100, ("A", D[4]): 90, ("B", D[4]): 7}) == Fraction(
        -1, 10
    )
    # two rolls
    two = {D[0]: "A", D[1]: "B", D[2]: "B", D[3]: "C", D[4]: "C"}
    c2 = {
        ("A", D[0]): 10,
        ("A", D[1]): 11,
        ("B", D[1]): 20,
        ("B", D[3]): 25,
        ("C", D[3]): 5,
        ("C", D[4]): 6,
    }
    assert chained_return(D, two, c2) == Fraction(11, 10) * Fraction(25, 20) * Fraction(6, 5) - 1


def test_s3_month_signal_runs_from_last_months_l_to_l3_and_rel_is_mes_minus_zn():
    sessions = [d for d in calendar_sessions() if date(2021, 1, 1) <= d <= date(2021, 3, 31)]
    pos = month_positions(sessions)
    feb_l, mar_l3 = date(2021, 2, 26), date(2021, 3, 26)
    assert pos[feb_l] == "L" and pos[mar_l3] == "L-3"
    mes = (dict.fromkeys(sessions, "MESH1"), {("MESH1", feb_l): 15_000, ("MESH1", mar_l3): 15_300})
    zn = (dict.fromkeys(sessions, "ZNM1"), {("ZNM1", feb_l): 8_000, ("ZNM1", mar_l3): 8_040})
    sig = month_signals(sessions, pos, mes, zn)
    assert sig[(2021, 1)] is None  # December 2020 is not in the list
    s = sig[(2021, 3)]
    assert (s.start, s.end, s.mes, s.zn) == (feb_l, mar_l3, Fraction(2, 100), Fraction(5, 1_000))
    assert s.rel == Fraction(15, 1_000)
    # attach: every session of March carries March's rel; positions per session
    days = [DayInput(d, "MES", {}, time(15, 7), None) for d in sessions]
    out = {d.trade_date: d.context for d in attach(days, pos, sig)}
    assert out[date(2021, 3, 31)] == {"position": "L", "rel": s.rel, "signal": s}
    assert out[date(2021, 3, 10)]["position"] is None
    assert out[date(2021, 1, 29)]["rel"] is None  # January has no signal


def _frame_rows(rows, *, symbol_col):
    out = pd.DataFrame(rows, columns=[symbol_col, "minute", "close", "volume"])
    out["minute"] = pd.to_datetime(out["minute"]).dt.tz_localize("America/Chicago")
    out["trade_date"] = (out["minute"] + pd.Timedelta(hours=7)).dt.date
    for k in ("open", "high", "low"):
        out[k] = out["close"]
    return out.sort_values([symbol_col, "minute"], ignore_index=True)


def test_s4_zn_close_is_last_bar_before_1400_or_1215_on_early_closes_and_volume_roll():
    cal = [
        CalendarDay(date(2019, 11, 26), time(15, 7), False),
        CalendarDay(date(2019, 11, 29), time(12, 12), True),
        CalendarDay(date(2019, 12, 2), time(15, 7), False),
    ]
    rows = [
        ("ZNZ9", "2019-11-26 07:19", 1, 100),  # before 07:20: ignored
        ("ZNZ9", "2019-11-26 13:58", 500, 100),
        ("ZNZ9", "2019-11-26 13:59", 501, 100),
        ("ZNZ9", "2019-11-26 14:00", 999, 100),  # at the close: ignored
        ("ZNH0", "2019-11-26 13:59", 600, 500),  # out-trades ZNZ9 -> front from the next session
        ("ZNZ9", "2019-11-29 12:14", 502, 10),
        ("ZNH0", "2019-11-29 12:14", 601, 900),
        ("ZNH0", "2019-11-29 12:15", 777, 1),  # early close 12:15: ignored
        ("ZNH0", "2019-12-02 13:59", 605, 900),
    ]
    front, closes = zn_leg(_frame_rows(rows, symbol_col="symbol"), cal)
    assert front == {
        date(2019, 11, 26): "ZNZ9",
        date(2019, 11, 29): "ZNH0",
        date(2019, 12, 2): "ZNH0",
    }
    assert closes == {
        ("ZNZ9", date(2019, 11, 26)): 501,
        ("ZNH0", date(2019, 11, 26)): 600,
        ("ZNZ9", date(2019, 11, 29)): 502,
        ("ZNH0", date(2019, 11, 29)): 601,
        ("ZNH0", date(2019, 12, 2)): 605,
    }


def test_s5_mes_closes_follow_the_volume_roll_file(tmp_path):
    cal = [CalendarDay(date(2020, 3, k), time(15, 7), False) for k in (13, 16, 17)]
    roll = tmp_path / "roll.csv"
    roll.write_text(
        "root,from_contract,to_contract,volume_roll_date\nMES,MESH0,MESM0,2020-03-16\n"
        "MNQ,MNQH0,MNQM0,2020-03-13\n",
        encoding="utf-8",
    )
    mappings = {
        "MESH0": [(date(2019, 1, 1), date(2021, 1, 1), 11)],
        "MESM0": [(date(2019, 1, 1), date(2021, 1, 1), 12)],
        "MESH0-MESM0": [(date(2019, 1, 1), date(2021, 1, 1), 99)],
    }
    rows = [
        (11, "2020-03-13 14:59", 4_000, 1),
        (11, "2020-03-13 15:00", 4_444, 1),  # at the regular close: not the close
        (11, "2020-03-16 14:58", 3_900, 1),
        (12, "2020-03-16 14:59", 3_880, 1),
        (12, "2020-03-17 14:59", 3_960, 1),
    ]
    frame = _frame_rows(rows, symbol_col="instrument_id")
    front, closes = mes_leg(frame, mappings, roll, cal)
    assert [front[c.trade_date] for c in cal] == ["MESH0", "MESM0", "MESM0"]
    assert closes == {
        ("MESH0", date(2020, 3, 13)): 4_000,
        ("MESH0", date(2020, 3, 16)): 3_900,
        ("MESM0", date(2020, 3, 16)): 3_880,
        ("MESM0", date(2020, 3, 17)): 3_960,
    }
    window = [c.trade_date for c in cal]
    assert (
        chained_return(window, front, closes) == Fraction(3_900, 4_000) * Fraction(3_960, 3_880) - 1
    )


# ---------------------------------------------------------------- trades


def legs(r):
    return [(x.side, x.entry_minute, x.entry_ticks, x.exit_minute, x.exit_ticks) for x in r.trades]


BARS = {"08:30": (16_000, 16_004, 15_990, 16_001), "11:00": (16_010, 16_030, 15_950, 16_020)}
BARS |= {"15:00": (16_020, 16_021, 16_019, 16_020)}


def test_t1_direction_is_against_the_month_to_date_lead_on_l2_l1_l():
    for position in ("L-2", "L-1", "L"):
        short = T1.simulate(mday(BARS, position=position, rel=Fraction(1, 1_000)))
        assert legs(short) == [(-1, t("08:30"), 16_000, t("15:00"), 16_020)]
        assert (short.trades[0].gross_cents, short.net_cents) == (-20 * 125, -2_500 - 622)
        long = T1.simulate(mday(BARS, position=position, rel=Fraction(-1, 10**9)))
        assert legs(long) == [(1, t("08:30"), 16_000, t("15:00"), 16_020)]
        assert (long.trades[0].gross_cents, long.net_cents) == (2_500, 2_500 - 622)
    for rel in (Fraction(0), None):
        r = T1.simulate(mday(BARS, rel=rel))
        assert (r.status, r.trades, r.net_cents) == ("no_trade", [], 0)
    for position in ("L-3", "F1", "F2", "F3", None):
        assert T1.simulate(mday(BARS, position=position)).status == "no_trade"


def test_t2_is_long_on_l_f1_f2_f3_whatever_the_signal():
    for position in ("L", "F1", "F2", "F3"):
        for rel in (Fraction(1, 10), Fraction(-1, 10), None):
            r = T2.simulate(mday(BARS, position=position, rel=rel))
            assert legs(r) == [(1, t("08:30"), 16_000, t("15:00"), 16_020)]
    for position in ("L-3", "L-2", "L-1", None):
        assert T2.simulate(mday(BARS, position=position)).status == "no_trade"


def test_t3_early_close_exits_at_the_1200_open():
    bars = {"08:30": (16_000,) * 4, "12:00": (16_008, 16_009, 16_007, 16_008)}
    bars |= {"12:11": (16_050,) * 4}
    for s, side in ((T1, -1), (T2, 1)):
        r = s.simulate(mday(bars, exit_minute="12:12"))
        assert legs(r) == [(side, t("08:30"), 16_000, t("12:00"), 16_008)]
        assert r.trades[0].gross_cents == side * 8 * 125
    # a normal day ignores the 12:00 bar
    assert T2.simulate(mday(bars)).trades[0].exit_minute == t("15:00")


def test_t4_missing_entry_or_exit_bar_is_non_evaluable_inner_gaps_are_not():
    for gone in ("08:30", "15:00"):
        for s in (T1, T2):
            assert s.simulate(mday(BARS, missing=(gone,))).status == "non_evaluable"
    assert (
        T2.simulate(mday(BARS, missing=("12:00",), exit_minute="12:12")).status == "non_evaluable"
    )
    assert T2.simulate(mday(BARS, missing=("09:00", "14:59"))).status == "traded"
    # a non-trade session is no_trade even with no bars at all (never dropped as ineligible)
    empty = dataclasses.replace(mday(position=None), bars={})
    assert T1.simulate(empty).status == T2.simulate(empty).status == "no_trade"
    assert T2.simulate(dataclasses.replace(mday(), bars={})).status == "non_evaluable"


def test_t5_costs_l1_to_l4_per_trade_and_per_session():
    assert analysis.COSTS["L3"]["MES"] == 622 and analysis.COSTS["L3"]["MNQ"] == 322
    days = [mday(BARS, position="L")] + [mday(BARS, position=None) for _ in range(9)]
    days = [dataclasses.replace(d, trade_date=date(2021, 3, 20 + i)) for i, d in enumerate(days)]
    table = engine.simulate(T2, days, draws=20)
    v = spec_verdict(table, "MES")  # one trade day: too few to test
    assert v["outcome"] == "FAIL" and v["trade_days"] == 1 and v["sessions"] == 10
    days[1] = dataclasses.replace(days[1], context={"position": "F1", "rel": None, "signal": None})
    table = engine.simulate(T2, days, draws=20)
    v = spec_verdict(table, "MES", replicates=99)
    gross = 20 * 125
    for level, cost in (("L1", 247), ("L2", 372), ("L3", 622), ("L4", 1_122)):
        assert v["costs"][level]["per_trade"] == pytest.approx((gross - cost) / 100)
        assert v["costs"][level]["per_session"] == pytest.approx(2 * (gross - cost) / 10 / 100)


# ---------------------------------------------------------------- control and gates


def _signs(root_code, stamp, n=500):
    rng = np.random.Generator(np.random.PCG64([20261029, root_code, stamp, 13]))
    return [int(s) for s in rng.integers(0, 2, size=n) * 2 - 1]


def test_c1_control_is_the_same_bars_in_a_seeded_random_direction():
    d = mday(BARS, rel=Fraction(1, 100))  # T1 short; +20 ticks long
    r = T1.simulate(d)
    gross, taken, lows, recs = T1.matched_control(d, r, 500)
    assert gross == [s * 2_500 for s in _signs(2, 20210329)] and taken == [1] * 500
    # the 11:00 bar's range sets each side's low: long -50 ticks, short -30 ticks (both x125)
    assert {g: lo for g, lo in zip(gross, lows, strict=True)} == {2_500: -6_250, -2_500: -3_750}
    for g, rec, low in zip(gross, recs, lows, strict=True):
        assert min([0, g] + [lo for lo, _ in rec]) == low
    assert T1.matched_control(d, r, 500)[0] == gross  # deterministic
    # T2 (long) on the same day draws the same signs (one spec tag, 13)
    assert T2.matched_control(d, T2.simulate(d), 500)[0] == gross
    mnq = dataclasses.replace(d, root="MNQ")
    assert T1.matched_control(mnq, T1.simulate(mnq), 500)[0] == [
        s * 20 * 50 for s in _signs(1, 20210329)
    ]
    later = dataclasses.replace(d, trade_date=date(2021, 3, 30))
    assert T1.matched_control(later, T1.simulate(later), 500)[0] != gross
    none = mday(BARS, position="L-3")
    assert T1.matched_control(none, T1.simulate(none), 5) == ([0] * 5, [0] * 5, [0] * 5, [[]] * 5)


def _table(nets_by_day, sessions, *, market="MES"):
    """A DayTable with given gross per trade day (None: no trade) over `sessions` days."""
    k = len(sessions)
    gross = np.array([g or 0 for g in nets_by_day] + [0] * (k - len(nets_by_day)), dtype=np.int64)
    trades = np.array([int(g is not None) for g in nets_by_day] + [0] * (k - len(nets_by_day)))
    ctrl = np.zeros((k, 4), dtype=np.int64)
    ctrl_trades = np.repeat(trades[:, None], 4, axis=1)
    z = np.zeros(k, dtype=np.int64)
    return engine.DayTable(
        dates=np.array([d.isoformat() for d in sessions], dtype="<U10"),
        status=np.where(trades > 0, "traded", "no_trade").astype("<U16"),
        atr=z, orb_side=trades.copy(), orb_gross=gross, orb_low=z, orb_stress_gross=gross,
        orb_trades=trades, entry_bar_stops=z, gap_trades=z, ctrl_gross=ctrl,
        ctrl_stress_gross=ctrl, ctrl_trades=ctrl_trades, ctrl_ok=np.ones(k, dtype=bool),
        ctrl_low=ctrl,
    )  # fmt: skip


def test_g1_floor_is_per_calendar_session_over_all_sessions_and_per_trade():
    sessions = [date(2021, 1, 1) + pd.Timedelta(days=i).to_pytimedelta() for i in range(100)]
    # 14 trades at +$15 gross -> $8.78 net each; $1.2292 per session over 100 sessions
    v = spec_verdict(_table([1_500] * 14, sessions), "MES", replicates=199)
    assert v["per_trade"] == pytest.approx(8.78) and v["per_session"] == pytest.approx(
        14 * 8.78 / 100
    )
    assert v["sessions"] == 100 and v["trade_days"] == 14
    assert not any("per session" in r or "per trade" in r for r in v["reasons"])
    # same trades over 200 sessions: per trade unchanged, per session halves below $1
    more = [date(2021, 1, 1) + pd.Timedelta(days=i).to_pytimedelta() for i in range(200)]
    v = spec_verdict(_table([1_500] * 14, more), "MES", replicates=199)
    assert v["per_session"] == pytest.approx(14 * 8.78 / 200) and v["outcome"] == "FAIL"
    assert any("$1.00 per session" in r for r in v["reasons"])
    # many small trades: per session fine, per trade below $5
    v = spec_verdict(_table([1_000] * 60, sessions), "MES", replicates=199)
    assert v["per_session"] >= 1.0 and any("$5.00 per trade" in r for r in v["reasons"])


def test_g2_p_value_uses_trade_days_only_and_the_spec_bar():
    sessions = [date(2021, 1, 1) + pd.Timedelta(days=i).to_pytimedelta() for i in range(300)]
    rng = np.random.default_rng(0)
    gross = [int(x) for x in rng.integers(-3_000, 3_600, size=40)]
    v_short = spec_verdict(_table(gross, sessions[:40]), "MES", replicates=999)
    v_long = spec_verdict(_table(gross, sessions), "MES", replicates=999)
    assert v_short["p_value"] == v_long["p_value"]  # zero days do not enter the test
    assert v_short["alpha"] == pytest.approx(0.02532, abs=1e-5)


def test_g3_engine_keeps_every_session_and_diagnostics_split_by_side_and_year():
    days = []
    for i, (pos, rel) in enumerate(
        [
            ("L-2", Fraction(1)),
            ("L-1", Fraction(-1)),
            ("L", Fraction(1)),
            (None, None),
            ("F1", None),
        ]
    ):
        d = mday(BARS, position=pos, rel=rel)
        days.append(dataclasses.replace(d, trade_date=date(2020 + i // 3, 1, 10 + i)))
    days.append(dataclasses.replace(mday(position=None), trade_date=date(2021, 2, 1), bars={}))
    table = engine.simulate(T1, days, draws=10)
    assert len(table.dates) == 6 and list(table.orb_trades) == [1, 1, 1, 0, 0, 0]
    by_side = hit_rate_by_side(table)
    assert by_side["rel>0 (short)"] == {"trade_days": 2, "hit_rate": 0.0, "gross_per_trade": -25.0}
    assert by_side["rel<0 (long)"] == {"trade_days": 1, "hit_rate": 1.0, "gross_per_trade": 25.0}
    years = per_year(table, "MES")
    assert years["2020"]["trade_days"] == 3 and years["2021"]["trade_days"] == 0
    assert years["2020"]["net"] == pytest.approx((-2_500 - 2_500 + 2_500 - 3 * 622) / 100)
    assert years["2021"]["per_session"] == 0.0 and years["2021"]["sessions"] == 3
    other = always_long_other(days, 622)  # L-2/L-1/None/None sessions; one has no bars
    assert (other["sessions"], other["missing_bars"]) == (3, 1)
    assert other["per_session"] == pytest.approx((2_500 - 622) / 100)


# ---------------------------------------------------------------- registry and honesty


def test_r1_family_registered_with_a_shared_two_trial_split(tmp_path):
    assert REGISTRY["month_end"] is MonthEnd and "month_end" in DESCRIPTIONS
    assert make("month_end", {"trial": "T2_turn_of_month"}) == T2
    with pytest.raises(ValueError):
        MonthEnd("T3")
    assert analysis.FAMILY_SPLIT["month_end"] == 2
    assert analysis.honesty(tmp_path, "month_end")["alpha"] == pytest.approx(1 - 0.95**0.5)
    assert "src/quant_brain/workbench/month_end.py" in engine.CODE_FILES
    # the other families keep their frozen grading and splits
    assert GRADING["orb"]["floor_cents"] == 1_500 and GRADING["noise_area"]["sharpe_min"] == 1.0
    assert {k: analysis.FAMILY_SPLIT[k] for k in ("fade_band", "gap_fill", "evening_revert")} == {
        "fade_band": 3,
        "gap_fill": 3,
        "evening_revert": 3,
    }
    assert analysis.honesty(tmp_path, "orb")["alpha"] == pytest.approx(0.05)
    assert T1.settings() != T2.settings() and T1.session == "month_end"


def test_r2_signal_type_is_exact():
    s = Signal(date(2021, 1, 29), date(2021, 2, 23), Fraction(1, 3), Fraction(1, 3))
    assert s.rel == 0 and T1.simulate(mday(BARS, rel=s.rel)).status == "no_trade"
    assert Signal(DAY, DAY, None, Fraction(1)).rel is None

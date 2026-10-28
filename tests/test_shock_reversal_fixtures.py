"""SC-FUT-0004 hand-worked fixtures, written before the plug-in.

Synthetic days: the 08:30 bar is (105, 110, 100, 105), then flat at the previous close
unless listed. The time-of-day scale is a flat 2 ticks, so a shock is |M| >= 8 ticks.
MES: 125 cents/tick, L3 622 cents.
"""

from __future__ import annotations

import dataclasses
from datetime import date

from futures_day_builder import make_day, t

from quant_brain.workbench.strategies import ShockReversal

STRAT = ShockReversal()
FLAT_SCALE = {m: 2.0 for m in range(8 * 60 + 30, 15 * 60 + 8)}  # minute-of-day -> ticks


def day(bars=None, missing=(), scale=FLAT_SCALE, fomc=False, exit_minute="15:07"):
    d = make_day(bars, missing=missing, root="MES", exit_minute=exit_minute)
    return dataclasses.replace(d, context={"scale": scale, "fomc": fomc})


DOWN_SHOCK = {"09:40": (105, 105, 96, 97), "09:41": (97, 99, 97, 99)}  # M(09:40) = 97 - 105 = -8


def test_x1_down_shock_confirmed_long_held_60_minutes():
    r = STRAT.simulate(day({**DOWN_SHOCK, "09:50": (99, 110, 99, 110)}))
    tr = r.trades[0]
    # entry 09:42 open 99; extreme low 96 -> stop 95 (4 ticks); exit 10:42 open 110
    assert (tr.side, tr.entry_minute, tr.entry_ticks, tr.stop_level_ticks) == (
        1,
        t("09:42"),
        99,
        95,
    )
    assert (tr.exit_minute, tr.exit_ticks, r.net_cents) == (t("10:42"), 110, 11 * 125 - 622)


def test_x2_no_confirmation_no_trade():
    r = STRAT.simulate(day({"09:40": (105, 105, 96, 97)}))  # flat bars never close up
    assert (r.status, r.trades) == ("no_trade", [])


def test_x3_stop_beyond_the_extreme():
    r = STRAT.simulate(day({**DOWN_SHOCK, "09:45": (99, 99, 94, 95)}))
    assert (r.trades[0].exit_ticks, r.net_cents) == (95, -4 * 125 - 622)


def test_x4_below_threshold_no_trade():
    r = STRAT.simulate(day({"09:40": (105, 105, 97, 98), "09:41": (98, 99, 98, 99)}))  # M = -7
    assert r.trades == []


def test_x5_fomc_cutoff_1245():
    late = {"13:00": (105, 105, 96, 97), "13:01": (97, 99, 97, 99)}
    assert STRAT.simulate(day(late, fomc=True)).trades == []
    assert STRAT.simulate(day(late, fomc=False)).trades  # same shock trades on a normal day
    early = {"12:30": (105, 105, 96, 97), "12:31": (97, 99, 97, 99)}
    assert STRAT.simulate(day(early, fomc=True)).trades


def test_x6_after_the_window_no_trade():
    r = STRAT.simulate(day({"14:35": (105, 105, 96, 97), "14:36": (97, 99, 97, 99)}))
    assert r.trades == []


def test_x7_up_shock_short_mirror():
    r = STRAT.simulate(day({"09:40": (105, 114, 105, 113), "09:41": (113, 113, 111, 111)}))
    tr = r.trades[0]  # extreme high 114 -> stop 115; entry 09:42 at 111
    assert (tr.side, tr.entry_ticks, tr.stop_level_ticks) == (-1, 111, 115)


def test_x8_no_scale_yet_no_trade():
    r = STRAT.simulate(day(DOWN_SHOCK, scale={}))
    assert (r.status, r.trades) == ("no_trade", [])


def test_x9_entry_after_1430_not_taken():
    r = STRAT.simulate(day({"14:29": (105, 105, 96, 97), "14:30": (97, 99, 97, 99)}))
    assert r.trades == []  # entry would be 14:31


def test_x10_late_entry_flattens_at_1507():
    r = STRAT.simulate(day({"14:18": (105, 105, 96, 97), "14:19": (97, 99, 97, 99)}))
    assert r.trades[0].entry_minute == t("14:20") and r.trades[0].exit_minute == t("15:07")


def test_x11_missing_exit_bar_non_evaluable():
    r = STRAT.simulate(day(DOWN_SHOCK, missing=("10:42",)))
    assert r.status == "non_evaluable"


def test_x12_only_the_first_shock_counts():
    bars = {
        **DOWN_SHOCK,
        "09:50": (99, 99, 99, 99),
        "11:00": (99, 99, 80, 81),
        "11:01": (81, 90, 81, 90),
    }
    r = STRAT.simulate(day(bars))
    assert len(r.trades) == 1 and r.trades[0].entry_minute == t("09:42")


def test_x13_early_close_signals_stop_at_1130():
    late = {"11:40": (105, 105, 96, 97), "11:41": (97, 99, 97, 99)}
    assert STRAT.simulate(day(late, exit_minute="12:12")).trades == []


def test_matched_control_mirrors_the_stop():
    d = day({**DOWN_SHOCK, "09:50": (99, 110, 99, 110)})
    r = STRAT.simulate(d)
    gross, taken, lows = STRAT.matched_control(d, r, 500)
    assert set(gross) == {11 * 125, -4 * 125}  # long wins 11; mirrored short stops at 103 (-4)
    assert taken == [1] * 500 and 200 < gross.count(11 * 125) < 300
    assert STRAT.matched_control(d, r, 500) == (gross, taken, lows)


def test_scale_uses_only_previous_sessions():
    days = []
    for i in range(70):
        d = make_day({"10:00": (105, 105, 100 - (i % 3), 101 - (i % 3))}, root="MES")
        days.append(dataclasses.replace(d, trade_date=date(2020, 1, 1).fromordinal(737425 + i)))
    prepared = STRAT.prepare_all(days)
    assert prepared[30].context["scale"] == {}  # fewer than 40 prior sessions
    s60 = prepared[65].context["scale"][10 * 60]
    future_changed = [*days[:66], dataclasses.replace(days[66], bars={}), *days[67:]]
    assert STRAT.prepare_all(future_changed)[65].context["scale"][10 * 60] == s60

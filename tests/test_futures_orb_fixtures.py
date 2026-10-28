"""Hand-worked SC-FUT-0001 fixtures (brain/_system/futures/orb-fixtures.md).

Both the engine and the independent reference must reproduce every fixture.
"""

from __future__ import annotations

import pytest
from futures_day_builder import make_day, t

from quant_brain.futures import orb, orb_reference

IMPLEMENTATIONS = [orb.simulate_day, orb_reference.simulate_day]
LONG_ENTRY = {
    "08:50": (105, 112, 105, 111),
    "08:51": (111, 113, 111, 112),
    "08:52": (112, 130, 112, 130),
}


@pytest.fixture(params=IMPLEMENTATIONS, ids=["engine", "reference"])
def simulate(request):
    return request.param


def summary(result):
    return (
        result.status,
        result.net_cents,
        [
            (tr.side, tr.entry_minute, tr.entry_ticks, tr.exit_minute, tr.exit_ticks, tr.net_cents)
            for tr in result.trades
        ],
    )


def test_f1_long_winner(simulate):
    r = simulate(make_day(LONG_ENTRY))
    assert summary(r) == ("traded", 628, [(1, t("08:51"), 111, t("15:07"), 130, 628)])


def test_f2_short_winner(simulate):
    r = simulate(
        make_day(
            {"08:50": (105, 105, 98, 99), "08:51": (99, 99, 95, 96), "08:52": (96, 96, 80, 80)}
        )
    )
    assert summary(r) == ("traded", 628, [(-1, t("08:51"), 99, t("15:07"), 80, 628)])


def test_f3_no_breakout(simulate):
    r = simulate(make_day())
    assert (r.status, r.net_cents, r.trades) == ("no_trade", 0, [])


def test_f4_void_range(simulate):
    r = simulate(make_day({"08:50": (105, 112, 105, 111)}, missing=("08:40",)))
    assert (r.status, r.net_cents, r.trades) == ("void_range", 0, [])


F5 = {"08:50": (105, 112, 105, 111), "08:51": (111, 112, 111, 112), "08:55": (108, 108, 106, 106)}


def test_f5_long_stopped_then_short(simulate):
    r = simulate(make_day({**F5, "09:00": (106, 106, 99, 99)}))
    assert summary(r) == (
        "traded",
        -844,
        [(1, t("08:51"), 111, t("08:55"), 107, -522), (-1, t("09:01"), 99, t("15:07"), 99, -322)],
    )


def test_f6_stop_on_entry_bar(simulate):
    r = simulate(make_day({"08:50": (105, 112, 105, 111), "08:51": (111, 111, 106, 108)}))
    assert summary(r) == ("traded", -522, [(1, t("08:51"), 111, t("08:51"), 107, -522)])
    assert r.trades[0].entry_bar_stop


def test_f7_gap_through_stop(simulate):
    bars = {
        "08:50": (105, 112, 105, 111),
        "08:51": (111, 112, 111, 112),
        "08:52": (105, 106, 104, 105),
    }
    r = simulate(make_day(bars))
    assert summary(r) == ("traded", -622, [(1, t("08:51"), 111, t("08:52"), 105, -622)])


def test_f8_missing_entry_minute_consumes_side(simulate):
    bars = {
        "08:50": (105, 112, 105, 111),
        "08:52": (106, 106, 105, 105),
        "08:55": (105, 112, 105, 112),
    }
    r = simulate(make_day(bars, missing=("08:51",)))
    assert (r.status, r.net_cents, r.trades) == ("no_trade", 0, [])
    assert ("entry_missing", t("08:51")) in r.events


def test_f9_gap_while_stop_live(simulate):
    bars = {
        "08:50": (105, 112, 105, 111),
        "08:51": (111, 112, 111, 112),
        "09:01": (112, 112, 108, 110),
    }
    r = simulate(make_day(bars, missing=("09:00",)))
    assert summary(r) == ("traded", -372, [(1, t("08:51"), 111, t("15:07"), 110, -372)])
    assert r.trades[0].gap_affected and r.trades[0].stress_exit_ticks == 107
    assert r.stress_net_cents == -522


def test_f10_missing_flatten_is_non_evaluable(simulate):
    r = simulate(make_day(LONG_ENTRY, missing=("15:07",)))
    assert r.status == "non_evaluable"


def test_f11_early_close(simulate):
    r = simulate(make_day(LONG_ENTRY, exit_minute="12:12"))
    assert summary(r) == ("traded", 628, [(1, t("08:51"), 111, t("12:12"), 130, 628)])


def test_f12a_entry_at_cutoff(simulate):
    r = simulate(make_day({"14:29": (105, 112, 105, 111)}))
    assert summary(r) == ("traded", -322, [(1, t("14:30"), 111, t("15:07"), 111, -322)])


def test_f12b_signal_after_cutoff(simulate):
    r = simulate(make_day({"14:30": (105, 112, 105, 111)}))
    assert (r.status, r.net_cents, r.trades) == ("no_trade", 0, [])


def test_f13_exit_bar_cannot_signal(simulate):
    bars = {
        "08:50": (105, 112, 105, 111),
        "08:51": (111, 112, 111, 112),
        "08:55": (108, 108, 98, 99),
    }
    r = simulate(make_day(bars))
    assert summary(r) == (
        "traded",
        -844,
        [(1, t("08:51"), 111, t("08:55"), 107, -522), (-1, t("08:57"), 99, t("15:07"), 99, -322)],
    )


def test_f14_one_entry_per_side(simulate):
    r = simulate(make_day({**F5, "09:10": (106, 112, 106, 112)}))
    assert summary(r) == ("traded", -522, [(1, t("08:51"), 111, t("08:55"), 107, -522)])


def test_f15_mes_costs(simulate):
    r = simulate(make_day(LONG_ENTRY, root="MES"))
    assert r.net_cents == 19 * 125 - 622


def test_f16_ineligible_without_atr(simulate):
    assert simulate(make_day(LONG_ENTRY, stop_ticks=None)).status == "ineligible"


@pytest.mark.parametrize(
    "stop_distance", [orb.stop_distance_ticks, orb_reference.stop_distance_ticks]
)
@pytest.mark.parametrize(
    ("session", "expected"),
    [((110, 100, 105), 1), ((125, 100, 110), 3), ((124, 100, 110), 2), ((103, 100, 101), 1)],
    ids=["A1", "A2-half-up", "A3", "A4-minimum"],
)
def test_atr_stop_distance(stop_distance, session, expected):
    assert stop_distance([session] * 15) == expected


@pytest.mark.parametrize(
    "stop_distance", [orb.stop_distance_ticks, orb_reference.stop_distance_ticks]
)
def test_atr_a5_gap_uses_prior_close_and_a6_missing(stop_distance):
    # 14 TRs: one gap session (H-L 10, but |H - prior close| = 320) and thirteen of TR 10.
    # Mean (320 + 130) / 14 = 32.14 -> 3.2 -> 3 ticks; ignoring the prior close would give 1.
    sessions = [(110, 100, 100), *[(420, 410, 415)] * 14]
    assert stop_distance(sessions) == 3
    assert stop_distance([*sessions[:7], None, *sessions[8:]]) is None
    assert stop_distance(sessions[:14]) is None


def test_f17_gap_running_to_flatten_is_non_evaluable(simulate):
    gone = tuple(f"{h:02d}:{m:02d}" for h in range(9, 16) for m in range(60) if (h, m) < (15, 7))
    r = simulate(make_day(LONG_ENTRY, missing=gone))
    assert r.status == "non_evaluable"


def test_f18_no_bars_in_cash_window_is_ineligible(simulate):
    day = make_day()
    empty = type(day)(day.trade_date, day.root, {}, day.exit_minute, day.stop_ticks)
    assert simulate(empty).status == "ineligible"


def test_f19_stress_bound_never_kinder_than_primary(simulate):
    bars = {
        "08:50": (105, 112, 105, 111),
        "08:51": (111, 112, 111, 112),
        "09:01": (112, 112, 108, 110),
        "09:30": (100, 101, 99, 100),
    }
    r = simulate(make_day(bars, missing=("09:00",)))
    trade = r.trades[0]
    assert (trade.exit_reason, trade.exit_ticks) == ("gap_stop", 100)
    assert trade.stress_exit_ticks == 100 and r.stress_net_cents == r.net_cents == -872


def test_general_stop_formula_matches_frozen_ten_percent_rule():
    for total in range(0, 20_000):
        assert orb.stop_from_sum(total) == max(1, (2 * total + 140) // 280), total

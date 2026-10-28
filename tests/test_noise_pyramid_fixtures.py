"""SC-FUT-0007 hand-worked fixtures, written before the plug-in.

Same synthetic MNQ days as SC-FUT-0005 (50 cents/tick, L3 322, open 105, sigma 2%,
bands 107.1 / 102.9). The pyramid step is ceil(0.02 x 105) = 3 ticks, so a long
entered at 108 adds at 111, 114 and 117; a short at 102 adds at 99, 96 and 93.
"""

from __future__ import annotations

from datetime import time

from futures_day_builder import t
from test_noise_area_fixtures import BREAKOUT, day

from quant_brain.futures.orb import Trade
from quant_brain.prop import paths
from quant_brain.workbench.noise import NoiseAreaPyramid

STRAT = NoiseAreaPyramid()


def units(r):
    return [(x.side, x.entry_minute, x.entry_ticks, x.exit_minute, x.exit_ticks) for x in r.trades]


def test_p1_three_adds_in_one_bar_fill_at_their_triggers():
    r = STRAT.simulate(day({**BREAKOUT, "10:10": (108, 120, 108, 120)}))
    assert units(r) == [
        (1, t("09:00"), 108, t("15:00"), 120),
        (1, t("10:10"), 111, t("15:00"), 120),
        (1, t("10:10"), 114, t("15:00"), 120),
        (1, t("10:10"), 117, t("15:00"), 120),
    ]
    assert r.net_cents == (12 + 9 + 6 + 3) * 50 - 4 * 322


def test_p2_a_gap_through_the_trigger_fills_at_the_open():
    r = STRAT.simulate(day({**BREAKOUT, "10:10": (115, 116, 115, 116)}))
    assert [(u[1], u[2]) for u in units(r)] == [(t("09:00"), 108), (t("10:10"), 115), (t("10:10"), 115)]
    assert r.net_cents == (8 + 1 + 1) * 50 - 3 * 322  # 117 never reached


def test_p3_no_add_inside_the_entry_minute():
    r = STRAT.simulate(day({**BREAKOUT, "09:00": (108, 112, 108, 108)}))
    assert len(r.trades) == 1


def test_p4_all_units_exit_together_and_a_reversal_restarts_at_one():
    r = STRAT.simulate(
        day({**BREAKOUT, "09:10": (108, 111, 108, 111), "10:29": (111, 111, 102, 102)})
    )
    assert units(r) == [
        (1, t("09:00"), 108, t("10:30"), 102),
        (1, t("09:10"), 111, t("10:30"), 102),
        (-1, t("10:30"), 102, t("15:00"), 102),
    ]
    assert r.net_cents == (-6 - 9) * 50 - 3 * 322


def test_p5_short_adds_below():
    r = STRAT.simulate(day({"08:59": (105, 105, 102, 102), "09:15": (102, 102, 98, 98)}))
    assert units(r) == [
        (-1, t("09:00"), 102, t("15:00"), 98),
        (-1, t("09:15"), 99, t("15:00"), 98),
    ]


def test_p6_concurrent_units_share_the_minute_path():
    bars = {
        time(10, 0): (100, 100, 100, 100),
        time(10, 1): (100, 104, 98, 103),
        time(10, 2): (103, 106, 95, 96),
        time(10, 3): (96, 96, 96, 96),
    }

    def unit(entry_at, entry):
        return Trade(1, entry_at, entry_at, entry, entry, time(10, 3), 96, "close",
                     (96 - entry) * 50, (96 - entry) * 50, False, False, None, 0)

    trades = [unit(time(10, 0), 100), unit(time(10, 1), 103)]
    # 10:01: A -2/+4, B -5/+1 -> (-7, 5). 10:02: A -5/+6, B -8/+3 -> (-13, 9). Exit -11.
    assert paths.book_records(bars, trades, 50) == [(-350, 250), (-650, 450)]
    assert paths.book_path(bars, trades, 50) == (-650, -550)


def test_p7_luck_pyramids_on_its_own_open_profit():
    d = STRAT.prepare(day({**BREAKOUT, "10:10": (108, 120, 108, 120)}))
    r = STRAT.simulate(d)
    gross, taken, _lows, _recs = STRAT.matched_control(d, r, 50)
    for g, k in zip(gross, taken, strict=True):
        # long: 4 units, +30 ticks; short at 108: no adds (price never drops), -12 ticks
        assert (g, k) in {(30 * 50, 4), (-12 * 50, 1)}
    assert {k for k in taken} == {1, 4}

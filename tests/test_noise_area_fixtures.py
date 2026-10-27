"""SC-FUT-0005 hand-worked fixtures, written before the plug-in.

Synthetic MNQ days (50 cents/tick, L3 322): the 08:30 bar is (105, 110, 100, 105), then flat
at the previous close unless listed. sigma = 2% at every check, so with the previous close
105 the bands are upper 107.1 and lower 102.9. Volume is 1 per bar unless given.
"""

from __future__ import annotations

import dataclasses
from datetime import date, time

from futures_day_builder import make_day, t

from quant_brain.workbench.noise import NoiseArea

STRAT = NoiseArea()
CHECKS = [h * 60 + m for h in range(9, 15) for m in (0, 30)]
SIGMA = {c: 0.02 for c in CHECKS}


def day(bars=None, missing=(), prev_close=105, sigma=SIGMA, volumes=None, exit_minute="15:07"):
    d = make_day(bars, missing=missing, root="MNQ", exit_minute=exit_minute)
    vol = {m: 1 for m in d.bars} | {t(k): v for k, v in (volumes or {}).items()}
    return dataclasses.replace(d, prev_close=prev_close, volumes=vol, context={"sigma": sigma})


def legs(r):
    return [(x.side, x.entry_minute, x.entry_ticks, x.exit_minute, x.exit_ticks) for x in r.trades]


BREAKOUT = {"08:59": (105, 108, 105, 108)}  # close 108 > 107.1 at the 09:00 check


def test_n1_long_on_breakout_held_to_the_close():
    r = STRAT.simulate(day({**BREAKOUT, "10:10": (108, 120, 108, 120)}))
    assert legs(r) == [(1, t("09:00"), 108, t("15:00"), 120)]
    assert r.net_cents == 12 * 50 - 322


def test_n2_exit_when_back_inside_the_band():
    r = STRAT.simulate(day({**BREAKOUT, "10:29": (108, 108, 106, 106)}))
    assert legs(r) == [(1, t("09:00"), 108, t("10:30"), 106)]  # 106 < max(107.1, VWAP)


def test_n3_reverse_when_the_opposite_band_breaks():
    r = STRAT.simulate(day({**BREAKOUT, "10:29": (108, 108, 102, 102)}))
    assert legs(r) == [
        (1, t("09:00"), 108, t("10:30"), 102),
        (-1, t("10:30"), 102, t("15:00"), 102),
    ]
    assert r.net_cents == -6 * 50 - 2 * 322


def test_n4_nothing_happens_between_checks():
    r = STRAT.simulate(day({"09:10": (105, 109, 105, 109), "09:20": (109, 109, 105, 105)}))
    assert r.trades == [] and r.status == "no_trade"


def test_n5_gap_widens_the_far_band():
    r = STRAT.simulate(day(BREAKOUT, prev_close=110))  # upper = 110 * 1.02 = 112.2
    assert r.trades == []


def test_n6_vwap_tightens_the_stop():
    bars = {**BREAKOUT, "09:05": (108, 115, 108, 115), "10:29": (115, 115, 112, 112)}
    heavy = {f"09:{m:02d}": 1_000 for m in range(5, 60)}
    r = STRAT.simulate(day(bars, volumes=heavy))  # VWAP ~115 > upper 107.1
    # Spec: after a VWAP exit only a reversal may happen at that check; a same-direction re-entry
    # comes at the next check while price is still above the band, then the VWAP stop exits again.
    # (Corrected from the first draft of this fixture to match the frozen spec, before any result.)
    entries = ["09:00", "11:00", "12:00", "13:00", "14:00"]
    exits = ["10:30", "11:30", "12:30", "13:30", "14:30"]
    expected = [
        (1, t(a), 108 if a == "09:00" else 112, t(b), 112)
        for a, b in zip(entries, exits, strict=True)
    ]
    assert legs(r) == expected


def test_n7_no_sigma_no_action():
    assert STRAT.simulate(day(BREAKOUT, sigma={})).trades == []


def test_n8_missing_check_bar_skips_that_check():
    r = STRAT.simulate(day(BREAKOUT, missing=("09:00",)))
    assert legs(r)[0][1] == t("09:30")  # still above the band at the next check


def test_n9_early_close_checks_to_1130_and_flat_at_1200():
    r = STRAT.simulate(day(BREAKOUT, exit_minute="12:12"))
    assert legs(r) == [(1, t("09:00"), 108, t("12:00"), 108)]
    late = STRAT.simulate(day({"11:59": (105, 108, 105, 108)}, exit_minute="12:12"))
    assert late.trades == []


def test_n10_missing_flatten_bar_is_non_evaluable():
    assert STRAT.simulate(day(BREAKOUT, missing=("15:00",))).status == "non_evaluable"


def test_n11_short_mirror():
    r = STRAT.simulate(day({"08:59": (105, 105, 102, 102), "10:10": (102, 102, 90, 90)}))
    assert legs(r) == [(-1, t("09:00"), 102, t("15:00"), 90)]
    assert r.net_cents == 12 * 50 - 322


def test_matched_control_randomises_each_trade_direction():
    d = day({**BREAKOUT, "10:29": (108, 108, 102, 102)})
    r = STRAT.simulate(d)
    gross, taken, lows = STRAT.matched_control(d, r, 500)
    assert taken == [2] * 500
    assert set(gross) <= {-300, 300}  # long -6 / short 0 ticks, each leg's sign random
    assert STRAT.matched_control(d, r, 500) == (gross, taken, lows)


def test_sigma_uses_only_previous_sessions():
    days = []
    for i in range(30):
        d = make_day({"08:59": (105, 105, 100 + i % 4, 100 + i % 4)}, root="MNQ")
        days.append(dataclasses.replace(d, trade_date=date.fromordinal(737425 + i), prev_close=105))
    prepared = STRAT.prepare_all(days)
    assert prepared[5].context["sigma"] == {}  # fewer than 10 prior sessions
    s = prepared[20].context["sigma"][9 * 60]
    changed = [*days[:21], dataclasses.replace(days[21], bars={}), *days[22:]]
    assert STRAT.prepare_all(changed)[20].context["sigma"][9 * 60] == s
    assert time(9, 0) == time(9, 0)

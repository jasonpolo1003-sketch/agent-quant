"""SC-FUT-0009 / 0010 / 0011 hand-worked fixtures (bracket trades: target + stop + flatten).

Synthetic MNQ days (50 cents/tick, L3 322). Unlisted minutes are flat at the previous bar's
close. Shared fills (spec `fills`): decision on the close of the bar ending at the check, entry
at the check bar's open; target needs a later bar trading through it by >= 1 tick; stop at the
stop or the gap open; stop first when one bar reaches both; flatten at the flatten bar's open.
"""

from __future__ import annotations

import dataclasses
from datetime import date, datetime, time, timedelta

import pandas as pd
import pytest
from futures_day_builder import make_day, t

from quant_brain.futures.bars import CalendarDay, build_days, build_evenings
from quant_brain.futures.orb import DayInput
from quant_brain.prop import paths
from quant_brain.workbench import engine
from quant_brain.workbench.bracket import (
    EveningRevert,
    FadeBand,
    GapFill,
    control_trade,
    run_bracket,
    to_tick,
)
from quant_brain.workbench.strategies import DESCRIPTIONS, GRADING, REGISTRY, make


def legs(r):
    return [
        (x.side, x.entry_minute, x.entry_ticks, x.exit_minute, x.exit_ticks, x.exit_reason)
        for x in r.trades
    ]


# ---------------------------------------------------------------- shared fill rules


def _bars(listed, start="09:00", end="15:00", flat=107):
    out, prev = {}, flat
    m = datetime.combine(date(2020, 1, 2), t(start))
    while m.time() <= t(end):
        bar = listed.get(m.strftime("%H:%M"), (prev,) * 4)
        out[m.time()] = bar
        prev = bar[3]
        m += timedelta(minutes=1)
    return out


def _short(bars, target=105, stop=108):
    return run_bracket(
        bars,
        root="MNQ",
        side=-1,
        entry_at=t("09:00"),
        target=target,
        stop=stop,
        flatten_at=t("15:00"),
    )


def test_target_needs_a_one_tick_trade_through():
    hit = _short(_bars({"09:10": (107, 107, 104, 104)}))
    assert (hit.exit_minute, hit.exit_ticks, hit.exit_reason) == (t("09:10"), 105, "target")
    touch = _short(_bars({"09:10": (107, 107, 105, 105)}))  # touches 105 only
    assert (touch.exit_minute, touch.exit_ticks, touch.exit_reason) == (t("15:00"), 105, "flatten")


def test_target_never_fills_on_the_entry_bar_and_a_gap_beyond_it_fills_at_the_target():
    r = _short(_bars({"09:00": (107, 107, 104, 104)}))  # entry bar trades through: ignored
    assert (r.exit_minute, r.exit_ticks, r.exit_reason) == (t("09:01"), 105, "target")
    gap = _short(_bars({"09:10": (100, 101, 99, 100)}))  # opens 5 ticks through: still 105
    assert (gap.exit_ticks, gap.exit_reason) == (105, "target")


def test_stop_touch_fills_at_the_stop_and_a_gap_fills_at_the_open():
    touch = _short(_bars({"09:10": (107, 108, 107, 108)}))
    assert (touch.exit_ticks, touch.exit_reason, touch.gross_cents) == (108, "stop", -50)
    gap = _short(_bars({"09:10": (110, 111, 109, 110)}))
    assert (gap.exit_ticks, gap.exit_reason, gap.gross_cents) == (110, "gap_stop", -150)


def test_stop_first_when_one_bar_reaches_both():
    r = _short(_bars({"09:10": (107, 108, 104, 104)}))
    assert (r.exit_ticks, r.exit_reason) == (108, "stop")


def test_stop_counts_on_the_entry_bar():
    r = _short(_bars({"09:00": (107, 108, 104, 104)}))
    assert (r.exit_minute, r.exit_ticks, r.exit_reason, r.entry_bar_stop) == (
        t("09:00"),
        108,
        "stop",
        True,
    )


def test_entry_already_beyond_target_or_stop_exits_at_the_entry_open():
    beyond_target = _short(_bars({}, flat=104))  # short at 104, buy-limit at 105 is marketable
    assert (beyond_target.exit_reason, beyond_target.gross_cents) == ("gap_target", 0)
    assert beyond_target.net_cents == -322
    beyond_stop = _short(_bars({}, flat=109))
    assert (beyond_stop.exit_reason, beyond_stop.gross_cents) == ("gap_stop", 0)


def test_missing_flatten_bar_returns_none_and_missing_minutes_fill_nothing():
    bars = _bars({})
    del bars[t("15:00")]
    assert _short(bars) is None
    gappy = _bars({"09:20": (107, 107, 104, 104)})
    del gappy[t("09:10")]
    assert _short(gappy).exit_minute == t("09:20")


def test_rounding_targets_toward_entry_stops_away():
    assert to_tick(107.1, -1) == 108 and to_tick(102.9, 1) == 102  # stops away from entry
    assert to_tick(105 * 1.02, -1) == 108  # 107.10000000000001
    assert to_tick(1000 * 1.02, -1) == 1020 and to_tick(1000 * 0.98, 1) == 980  # float noise
    assert to_tick(104.6, 1) == 104 and to_tick(104.6, -1) == 105  # targets toward entry


def test_target_exit_bar_counts_its_adverse_extreme_in_the_equity_path():
    r = _short(_bars({"09:10": (107, 107, 104, 104)}))
    long_r = run_bracket(
        _bars({"09:10": (107, 110, 104, 110)}),
        root="MNQ",
        side=1,
        entry_at=t("09:00"),
        target=109,
        stop=103,
        flatten_at=t("15:00"),
    )
    assert long_r.exit_reason == "target"
    assert paths.trade_extremes(_bars({"09:10": (107, 110, 104, 110)}), long_r, 50) == (-150, 100)
    assert paths.trade_extremes(_bars({"09:10": (107, 107, 104, 104)}), r, 50) == (0, 100)


# ---------------------------------------------------------------- SC-FUT-0009 fade_band
# 08:30 bar (105, 110, 100, 105): open 105; prev close 105; sigma 2% -> upper 107.1, lower 102.9.
# Short zone: 106.05 <= price < 107.1 (price 107); long zone: 102.9 < price <= 103.95 (103).

FADE = FadeBand()
CHECKS = [h * 60 + m for h in range(9, 15) for m in (0, 30)]
SIGMA = {c: 0.02 for c in CHECKS}
UP = {"08:59": (105, 107, 105, 107)}  # price 107 at the 09:00 check


def fday(bars=None, missing=(), prev_close=105, sigma=SIGMA, exit_minute="15:07"):
    d = make_day(bars, missing=missing, root="MNQ", exit_minute=exit_minute)
    return dataclasses.replace(d, prev_close=prev_close, context={"sigma": sigma, "skip": False})


def test_f1_short_fade_hits_the_open():
    r = FADE.simulate(fday({**UP, "09:10": (107, 107, 104, 104)}))
    assert legs(r)[0] == (-1, t("09:00"), 107, t("09:10"), 105, "target")
    assert r.trades[0].stop_level_ticks == 108  # 107.1 rounded away from the entry
    assert r.net_cents == 2 * 50 - 322


def test_f2_long_mirror():
    r = FADE.simulate(fday({"08:59": (105, 105, 103, 103), "09:10": (103, 106, 103, 106)}))
    assert legs(r)[0] == (1, t("09:00"), 103, t("09:10"), 105, "target")
    assert r.trades[0].stop_level_ticks == 102


def test_f3_stop_at_the_band_edge_and_no_entry_beyond_it():
    r = FADE.simulate(fday({**UP, "09:10": (107, 108, 107, 108)}))
    assert legs(r) == [(-1, t("09:00"), 107, t("09:10"), 108, "stop")]  # 108 > upper: no re-entry


def test_f4_no_entry_short_of_half_way_or_past_the_edge():
    assert FADE.simulate(fday({"08:59": (105, 106, 105, 106)})).trades == []  # 106 < 106.05
    assert FADE.simulate(fday({"08:59": (105, 108, 105, 108)})).trades == []  # 108 >= 107.1


def test_f5_new_entry_only_at_a_later_check_after_the_exit():
    # stopped inside the 09:30 bar: the 09:30 check still saw an open position
    r = FADE.simulate(fday({**UP, "09:30": (107, 108, 107, 107)}))
    assert legs(r) == [
        (-1, t("09:00"), 107, t("09:30"), 108, "stop"),
        (-1, t("10:00"), 107, t("15:00"), 107, "flatten"),
    ]


def test_f6_at_most_three_entries():
    bars = {**UP}
    for check in ("09:00", "09:30", "10:00", "10:30"):
        h, m = map(int, check.split(":"))
        bars[f"{h:02d}:{m + 10:02d}"] = (107, 107, 104, 104)  # target 10 minutes later
        before = h * 60 + m + 29
        bars[f"{before // 60:02d}:{before % 60:02d}"] = (104, 107, 104, 107)  # back up
    r = FADE.simulate(fday(bars))
    assert [x[1] for x in legs(r)] == [t("09:00"), t("09:30"), t("10:00")]
    assert all(x[5] == "target" for x in legs(r))


def test_f7_early_close_checks_to_1130_flat_at_1200():
    r = FADE.simulate(fday({"11:29": (105, 107, 105, 107)}, exit_minute="12:12"))
    assert legs(r) == [(-1, t("11:30"), 107, t("12:00"), 107, "flatten")]
    late = FADE.simulate(fday({"11:59": (105, 107, 105, 107)}, exit_minute="12:12"))
    assert late.trades == []


def test_f8_missing_flatten_bar_is_non_evaluable_and_no_sigma_no_trade():
    assert FADE.simulate(fday(UP, missing=("15:00",))).status == "non_evaluable"
    assert FADE.simulate(fday(UP, sigma={})).status == "no_trade"
    assert FADE.simulate(fday(UP, prev_close=None)).status == "no_trade"


def test_f9_prev_close_above_open_widens_the_upper_band():
    # prev close 106: upper = 106 * 1.02 = 108.12; half-way = 106.56 -> price 107 qualifies
    r = FADE.simulate(fday({**UP, "09:10": (107, 108, 107, 108)}, prev_close=106))
    assert r.trades[0].stop_level_ticks == 109 and r.trades[0].exit_reason == "flatten"


def test_f10_decision_uses_only_the_bar_before_the_check():
    # the 09:00 bar itself jumps into the zone; the 09:00 check must not see it
    r = FADE.simulate(fday({"09:00": (105, 107, 105, 107)}))
    assert legs(r)[0][1] == t("09:30")


def test_fade_band_sigma_is_exactly_sc_fut_0005():
    days = []
    for i in range(30):
        d = make_day({"08:59": (105, 105, 100 + i % 4, 100 + i % 4)}, root="MNQ")
        days.append(dataclasses.replace(d, trade_date=date.fromordinal(737425 + i), prev_close=105))
    from quant_brain.workbench.noise import NoiseArea

    ours, theirs = FADE.prepare_all(days), NoiseArea().prepare_all(days)
    assert [d.context["sigma"] for d in ours] == [d.context["sigma"] for d in theirs]


# ---------------------------------------------------------------- SC-FUT-0010 gap_fill
# ATR = 280 / 14 = 20 ticks: trade gaps of 4..20 ticks. 08:30 bar (105, 106, 103, 104).

GAP = GapFill()
OPEN_BAR = {"08:30": (105, 106, 103, 104)}


def gday(bars=None, prev_close=95, atr=280, missing=(), exit_minute="15:07"):
    d = make_day({**OPEN_BAR, **(bars or {})}, missing=missing, exit_minute=exit_minute)
    return dataclasses.replace(d, prev_close=prev_close, atr_tr_sum=atr)


def test_g1_gap_up_short_fills_at_the_previous_close():
    r = GAP.simulate(gday({"09:00": (104, 104, 94, 94)}))
    assert legs(r) == [(-1, t("08:31"), 104, t("09:00"), 95, "target")]
    assert r.trades[0].stop_level_ticks == 114  # entry + |gap| 10
    assert r.net_cents == 9 * 50 - 322


def test_g2_gap_limits_are_inclusive():
    assert GAP.simulate(gday(prev_close=101)).trades  # gap 4 = 0.2 ATR
    assert not GAP.simulate(gday(prev_close=102)).trades  # gap 3
    low_ok = {"08:30": (105, 106, 90, 104)}
    assert GAP.simulate(gday(low_ok, prev_close=85)).trades  # gap 20 = 1.0 ATR
    assert not GAP.simulate(gday(low_ok, prev_close=84)).trades  # gap 21


def test_g3_any_touch_of_the_previous_close_in_the_first_bar_counts_as_filled():
    filled = gday({"08:30": (105, 106, 101, 104)}, prev_close=101)
    assert GAP.simulate(filled).trades == []
    open_ = gday({"08:30": (105, 106, 102, 104)}, prev_close=101)
    assert legs(GAP.simulate(open_))[0][:3] == (-1, t("08:31"), 104)


def test_g4_stop_one_gap_away_and_flatten_at_1100():
    stop = GAP.simulate(gday({"09:00": (104, 114, 104, 114)}))
    assert legs(stop) == [(-1, t("08:31"), 104, t("09:00"), 114, "stop")]
    flat = GAP.simulate(gday())
    assert legs(flat) == [(-1, t("08:31"), 104, t("11:00"), 104, "flatten")]
    early = GAP.simulate(gday(exit_minute="12:12"))
    assert legs(early)[0][3] == t("11:00")


def test_g5_gap_down_long_mirror():
    r = GAP.simulate(gday({"08:30": (105, 110, 104, 106)}, prev_close=115))
    assert legs(r)[0][:3] == (1, t("08:31"), 106)
    assert r.trades[0].stop_level_ticks == 96


def test_g6_entry_already_through_the_close_exits_at_the_open():
    r = GAP.simulate(gday({"08:31": (94, 94, 94, 94)}))
    assert legs(r) == [(-1, t("08:31"), 94, t("08:31"), 94, "gap_target")]
    assert r.net_cents == -322


def test_g7_missing_inputs_no_trade():
    assert GAP.simulate(gday(atr=None)).trades == []
    assert GAP.simulate(gday(prev_close=None)).trades == []
    assert GAP.simulate(gday(missing=("08:31",))).trades == []
    assert GAP.simulate(gday(missing=("11:00",))).status == "non_evaluable"


# ---------------------------------------------------------------- SC-FUT-0011 evening_revert
# Evening bars 17:00..20:30, P0 = 1000, sigma 1% at every check: trade beyond +/-10 ticks;
# stop P0 x (1 +/- 0.02) = 1020 / 980.

EVE = EveningRevert()
ECHECKS = list(range(17 * 60 + 30, 20 * 60 + 1, 15))
ESIGMA = {c: 0.01 for c in ECHECKS}


def eday(listed=None, missing=(), sigma=ESIGMA, p0=1000, trade_date=date(2020, 1, 6)):
    listed = listed or {}
    bars, prev = {}, p0
    m = datetime.combine(date(2020, 1, 5), t("17:00"))
    while m.time() <= t("20:30"):
        key = m.strftime("%H:%M")
        bar = listed.get(key, (prev,) * 4)
        if key not in missing:
            bars[m.time()] = bar
        prev = bar[3]
        m += timedelta(minutes=1)
    return DayInput(trade_date, "MNQ", bars, t("20:30"), None, None, None, {"sigma": sigma}, None)


def test_e1_short_back_to_the_reopen():
    r = EVE.simulate(eday({"17:29": (1000, 1011, 1000, 1011), "18:00": (1011, 1011, 999, 999)}))
    assert legs(r) == [(-1, t("17:30"), 1011, t("18:00"), 1000, "target")]
    assert r.trades[0].stop_level_ticks == 1020


def test_e2_threshold_is_strict():
    assert EVE.simulate(eday({"17:29": (1000, 1010, 1000, 1010)})).trades == []  # exactly 1%


def test_e3_long_mirror_and_stop():
    r = EVE.simulate(eday({"17:29": (1000, 1000, 989, 989), "18:00": (989, 990, 980, 985)}))
    assert legs(r)[0] == (1, t("17:30"), 989, t("18:00"), 980, "stop")


def test_e4_addendum_1_no_entry_at_or_beyond_two_sigma():
    assert EVE.simulate(eday({"17:29": (1000, 1025, 1000, 1025)})).trades == []
    assert EVE.simulate(eday({"17:29": (1000, 1020, 1000, 1020)})).trades == []  # exactly 2 sigma
    r = EVE.simulate(eday({"17:29": (1000, 1019, 1000, 1019)}))
    assert legs(r)[0][:3] == (-1, t("17:30"), 1019)


def test_e4b_max_two_entries():
    r = EVE.simulate(
        eday(
            {
                "17:29": (1000, 1015, 1000, 1015),
                "17:31": (1015, 1020, 1015, 1020),  # stopped at 1020
                "17:44": (1020, 1020, 1015, 1015),
                "17:46": (1015, 1021, 1015, 1021),  # second stop
                "17:59": (1021, 1021, 1015, 1015),
            }
        )
    )
    assert [x[5] for x in legs(r)] == ["stop", "stop"]
    assert len(r.trades) == 2


def test_e5_flatten_at_2030_and_last_check_2000():
    r = EVE.simulate(eday({"19:59": (1000, 1011, 1000, 1011)}))
    assert legs(r) == [(-1, t("20:00"), 1011, t("20:30"), 1011, "flatten")]
    assert EVE.simulate(eday({"20:14": (1000, 1011, 1000, 1011)})).trades == []


def test_e6_skip_rules():
    signal = {"17:29": (1000, 1011, 1000, 1011)}
    assert EVE.simulate(eday(signal, missing=("17:00",))).status == "no_trade"
    # missing bars count point in time: 31 missing before 18:15 stops new entries from then on
    gone = (*(f"17:{m:02d}" for m in range(31, 60)), "18:00", "18:01")  # 31 bars
    late = {"18:14": (1000, 1011, 1000, 1011)}
    assert EVE.simulate(eday(late, missing=gone)).trades == []
    assert EVE.simulate(eday(late, missing=gone[:-1])).trades  # 30 missing: still trades
    assert EVE.simulate(eday(signal, missing=("20:30",))).status == "non_evaluable"


def test_e7_sigma_from_previous_usable_evenings_only():
    days = [
        eday(
            {"17:29": (1000, 1000 + i, 1000, 1000 + i)},
            sigma=None,
            trade_date=date(2020, 1, 6) + timedelta(days=i),
        )
        for i in range(1, 16)
    ]
    prepared = EVE.prepare_all(days)
    assert prepared[9].context["sigma"] == {}  # 9 prior evenings
    assert prepared[10].context["sigma"][17 * 60 + 30] == pytest.approx(0.0055)  # 1..10 ticks
    # today's own bars never feed today's sigma; an evening with > 30 missing bars is skipped
    changed = [
        *days[:10],
        eday(sigma=None, missing=tuple(f"19:{m:02d}" for m in range(31))),
        *days[11:],
    ]
    again = EVE.prepare_all(changed)
    assert again[10].context == prepared[10].context
    assert again[11].context["sigma"][17 * 60 + 30] == pytest.approx(0.0055)  # day 10 not used
    assert prepared[11].context["sigma"][17 * 60 + 30] == pytest.approx(0.006)  # 1..11 ticks


# ---------------------------------------------------------------- matched luck control


@pytest.mark.parametrize(
    ("strategy", "day"),
    [
        (FADE, fday({**UP, "09:10": (107, 107, 104, 104), "09:59": (104, 107, 104, 107)})),
        (GAP, gday({"09:00": (104, 104, 94, 94)})),
        (EVE, eday({"17:29": (1000, 1011, 1000, 1011), "18:00": (1011, 1011, 999, 999)})),
    ],
)
def test_control_unflipped_leg_reproduces_the_strategy(strategy, day):
    r = strategy.simulate(day)
    assert r.status == "traded"
    _, trades, plan, _ = strategy._plan(day)
    for leg, trade in zip(plan, trades, strict=True):
        assert control_trade(day, leg, leg["side"]) == trade
    gross, taken, lows, recs = strategy.matched_control(day, r, 200)
    assert taken == [len(trades)] * 200
    assert strategy.matched_control(day, r, 200) == (gross, taken, lows, recs)
    same = sum(x.gross_cents for x in trades)
    assert same in gross  # some draw keeps every direction
    assert all(min([0] + [lo for lo, _ in rec]) == low for rec, low in zip(recs, lows, strict=True))


def test_control_flipped_leg_mirrors_the_bracket_distances():
    d = fday({**UP, "09:10": (107, 107, 104, 104)})
    _, _, plan, _ = FADE._plan(d)
    flip = control_trade(d, plan[0], 1)  # long at 107: target 109, stop 106
    assert (flip.stop_level_ticks, flip.exit_ticks, flip.exit_reason) == (106, 106, "stop")
    gross, *_ = FADE.matched_control(d, FADE.simulate(d), 500)
    assert set(gross) == {100, -50}


def test_control_seeds_are_per_root_and_date():
    d = fday({**UP, "09:10": (107, 107, 104, 104)})
    r = FADE.simulate(d)
    a = FADE.matched_control(d, r, 64)[0]
    b = FADE.matched_control(dataclasses.replace(d, trade_date=date(2020, 1, 3)), r, 64)[0]
    assert a != b
    assert FADE.matched_control(d, dataclasses.replace(r, status="no_trade"), 3) == (
        [0] * 3,
        [0] * 3,
        [0] * 3,
        [[]] * 3,
    )


# ---------------------------------------------------------------- registry and engine


def test_registered_with_fixed_settings_and_noise_area_grading():
    for family, cls in (
        ("fade_band", FadeBand),
        ("gap_fill", GapFill),
        ("evening_revert", EveningRevert),
    ):
        assert REGISTRY[family] is cls and make(family).family == family
        assert GRADING[family] == GRADING["noise_area"] and GRADING[family]["floor_cents"] == 500
        assert DESCRIPTIONS[family]
        with pytest.raises(TypeError):
            make(family, {"max_entries": 5})  # no free parameters
    assert make("evening_revert").session == "evening"
    assert getattr(make("fade_band"), "session", "rth") == "rth"
    assert "src/quant_brain/workbench/bracket.py" in engine.CODE_FILES


def test_the_three_cards_share_one_sidak_split_of_the_honesty_bar(tmp_path):
    """Spec gates.beats_luck: alpha = 1 - 0.95^(1/3) = 0.0170 each for the first trial (QA fix)."""
    import json

    from quant_brain.workbench import analysis

    ledger = tmp_path / engine.LEDGER
    ledger.parent.mkdir(parents=True)
    rows = [
        {"family": f, "settings": make(f).settings(), "market": "MNQ", "roll": "volume"}
        for f in ("fade_band", "gap_fill", "evening_revert", "noise_area")
    ]
    ledger.write_text("".join(json.dumps(r, default=str) + "\n" for r in rows), encoding="utf-8")
    for family in ("fade_band", "gap_fill", "evening_revert"):
        bar = analysis.honesty(tmp_path, family)
        assert bar["trials"] == 1 and round(bar["alpha"], 4) == 0.0170
    assert analysis.honesty(tmp_path, "noise_area")["alpha"] == pytest.approx(0.05)  # unchanged
    with ledger.open("a", encoding="utf-8") as handle:  # a second distinct trial tightens it
        handle.write(json.dumps({**rows[1], "market": "MES"}) + "\n")
    assert analysis.honesty(tmp_path, "gap_fill")["alpha"] == pytest.approx(1 - 0.95 ** (1 / 6))


def test_engine_runs_each_family_on_synthetic_days():
    fade = [fday({**UP, "09:10": (107, 107, 104, 104)}), fday(), fday(UP, missing=("15:00",))]
    gap = [gday({"09:00": (104, 104, 94, 94)}), gday(prev_close=None)]
    eve = [eday({"17:29": (1000, 1011, 1000, 1011)}), eday()]
    for strategy, days in ((FADE, fade), (GAP, gap), (EVE, eve)):
        strategy = type(strategy)()
        # skip prepare_all (it would recompute sigma); the fixtures carry their own context
        table = engine.simulate(_NoPrepare(strategy), days, draws=16)
        assert table.ctrl_gross.shape == (len(days), 16)
        assert table.status[0] == "traded"
        assert table.orb_trades[0] >= 1


class _NoPrepare:
    def __init__(self, inner):
        self._inner = inner

    def __getattr__(self, name):
        if name == "prepare_all":
            raise AttributeError(name)
        return getattr(self._inner, name)


# ---------------------------------------------------------------- evening day builder
CT = "America/Chicago"
DAYS = [d.date() for d in pd.bdate_range("2021-01-04", periods=17)]
MAPPINGS = {"MNQH1": [(date(2020, 9, 1), date(2021, 3, 20), 7)]}


def _frame():
    rows = []
    for d in DAYS:
        for minute in pd.date_range(f"{d} 08:30", f"{d} 15:10", freq="min", tz=CT):
            rows.append((7, minute, d, 1_000, 1_010, 990, 1_000))
    for d in DAYS[1:]:
        before = d - timedelta(days=1)  # the calendar evening before: Sunday for Monday
        for minute in pd.date_range(f"{before} 16:59", f"{before} 21:00", freq="min", tz=CT):
            price = 2_000 + minute.minute
            rows.append(
                (7, minute, (minute + pd.Timedelta(hours=7)).date(), price, price, price, price)
            )
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


def test_build_evenings_gives_the_previous_evening_and_leaves_build_days_alone(tmp_path):
    calendar = [CalendarDay(d, time(15, 7), False) for d in DAYS]
    frame = _frame()
    kw = {"root": "MNQ", "start": DAYS[0], "end": DAYS[-1]}
    rth = list(build_days(frame, MAPPINGS, _roll(tmp_path), calendar, **kw))
    eve = list(build_evenings(frame, MAPPINGS, _roll(tmp_path), calendar, **kw))
    assert [d.trade_date for d in eve] == [d.trade_date for d in rth]
    assert [d.atr_tr_sum for d in eve] == [d.atr_tr_sum for d in rth]
    assert all(min(d.bars) >= time(8, 30) and max(d.bars) <= time(15, 7) for d in rth)
    assert eve[0].bars == {}  # no evening before the first day in the frame
    monday = next(d for d in eve if d.trade_date == date(2021, 1, 11))
    assert min(monday.bars) == time(17, 0) and max(monday.bars) == time(20, 30)
    assert len(monday.bars) == 211 and monday.exit_minute == time(20, 30)
    assert monday.bars[time(17, 5)] == (2_005,) * 4
    # the evening bars do not change what build_days returns for RTH
    plain = _frame()
    plain = plain[plain["minute"].dt.hour.between(8, 15)]
    again = list(build_days(plain, MAPPINGS, _roll(tmp_path), calendar, **kw))
    assert [(d.bars, d.prev_close) for d in again] == [(d.bars, d.prev_close) for d in rth]


# ---------------------------------------------------------------- no look-ahead (random days)


def _walk(rng, start, end, p=10_000):
    bars, m = {}, datetime.combine(date(2020, 1, 2), t(start))
    while m.time() <= t(end):
        o = p + rng.randint(-2, 2)
        c = o + rng.randint(-6, 6)
        bars[m.time()] = (o, max(o, c) + rng.randint(0, 3), min(o, c) - rng.randint(0, 3), c)
        p = c
        m += timedelta(minutes=1)
    return bars


def _future_scrambled(day, after, rng):
    """Same bars up to and including `after`'s open; everything later redrawn."""
    out = {}
    for m, bar in day.bars.items():
        if m < after:
            out[m] = bar
        elif m == after:
            out[m] = (bar[0], bar[0] + 50, bar[0] - 50, bar[0] + rng.randint(-40, 40))
        else:
            p = bar[0] + rng.randint(-80, 80)
            out[m] = (p, p + 5, p - 5, p)
    return dataclasses.replace(day, bars=out)


@pytest.mark.parametrize("seed", range(40))
def test_entries_never_depend_on_later_bars(seed):
    import random

    rng = random.Random(seed)
    cases = [
        (
            FADE,
            dataclasses.replace(
                make_day(),
                bars=_walk(rng, "08:30", "15:07"),
                prev_close=10_000 + rng.randint(-60, 60),
                context={"sigma": {c: 0.002 for c in CHECKS}, "skip": False},
            ),
        ),
        (
            GAP,
            dataclasses.replace(
                make_day(),
                bars=_walk(rng, "08:30", "15:07"),
                prev_close=10_000 + rng.randint(-60, 60),
                atr_tr_sum=14 * 80,
            ),
        ),
        (
            EVE,
            dataclasses.replace(
                eday(),
                bars=_walk(rng, "17:00", "20:30"),
                context={"sigma": {c: 0.002 for c in ECHECKS}},
            ),
        ),
    ]
    keys = ("side", "entry_at", "target", "stop")
    for strategy, day in cases:
        _, trades, plan, _ = strategy._plan(day)
        TRADED[strategy.family] += len(trades)
        for k, trade in enumerate(trades):
            # legs up to k decided (and earlier ones exited) before trade k's entry minute
            _, _, plan2, _ = strategy._plan(_future_scrambled(day, trade.entry_minute, rng))
            assert [[leg[x] for x in keys] for leg in plan2[: k + 1]] == [
                [leg[x] for x in keys] for leg in plan[: k + 1]
            ]


TRADED = {"fade_band": 0, "gap_fill": 0, "evening_revert": 0}


def test_zz_the_look_ahead_check_saw_trades_in_every_family():
    assert all(n > 0 for n in TRADED.values()), TRADED

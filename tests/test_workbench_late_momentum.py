"""SC-FUT-0002 late-day momentum plug-in: hand-worked days, matched control, grading."""

from __future__ import annotations

import dataclasses
import json
from datetime import date, time

import numpy as np
from futures_day_builder import make_day

from quant_brain.workbench import analysis, engine
from quant_brain.workbench.strategies import LateDayMomentum

STRAT = LateDayMomentum()


def day(bars=None, missing=(), prev_close=100, root="MES", exit_minute="15:07"):
    d = make_day(bars, missing=missing, root=root, exit_minute=exit_minute)
    return dataclasses.replace(d, prev_close=prev_close)


def test_up_day_goes_long_for_the_last_half_hour():
    r = STRAT.simulate(
        day(
            {
                "14:29": (104, 106, 104, 105),
                "14:30": (106, 106, 106, 106),
                "15:00": (110, 110, 110, 110),
            }
        )
    )
    t = r.trades[0]
    assert (r.status, t.side, t.entry_minute, t.entry_ticks, t.exit_minute, t.exit_ticks) == (
        "traded",
        1,
        time(14, 30),
        106,
        time(15, 0),
        110,
    )
    assert r.net_cents == 4 * 125 - 622


def test_down_day_goes_short():
    r = STRAT.simulate(
        day(
            {"14:29": (96, 96, 94, 95), "14:30": (95, 95, 95, 95), "15:00": (90, 90, 90, 90)},
            prev_close=100,
            root="MNQ",
        )
    )
    assert (r.trades[0].side, r.net_cents) == (-1, 5 * 50 - 322)


def test_flat_signal_early_close_and_missing_bars():
    assert STRAT.simulate(day(prev_close=105)).status == "no_trade"  # flat at 105 all day
    assert (
        STRAT.simulate(day({"14:29": (105, 106, 104, 106)}, exit_minute="12:12")).events[0][0]
        == "early_close_skip"
    )
    assert STRAT.simulate(day(missing=("14:29",))).events == [("signal_missing", time(14, 29))]
    r = STRAT.simulate(day({"14:29": (104, 106, 104, 106)}, missing=("14:30",)))
    assert (r.status, r.events) == ("no_trade", [("entry_missing", time(14, 30))])
    assert (
        STRAT.simulate(day({"14:29": (104, 106, 104, 106)}, missing=("15:00",))).status
        == "non_evaluable"
    )
    assert STRAT.simulate(day(prev_close=None)).status == "no_trade"  # spec: $0, not dropped
    empty = dataclasses.replace(day(), bars={})
    assert STRAT.simulate(empty).status == "ineligible"


def test_window_setting_moves_entry():
    r = LateDayMomentum(window_minutes=60).simulate(day({"13:59": (104, 106, 104, 106)}))
    assert r.trades[0].entry_minute == time(14, 0)


def test_matched_control_is_random_direction_on_the_same_trade():
    d = day(
        {
            "14:29": (104, 106, 104, 105),
            "14:30": (106, 106, 106, 106),
            "15:00": (110, 110, 110, 110),
        }
    )
    r = STRAT.simulate(d)
    gross, taken, lows = STRAT.matched_control(d, r, 500)
    assert set(gross) == {500, -500} and taken == [1] * 500
    # same direction never went underwater; flipped, its worst is minus the original best
    assert {(g, lo) for g, lo in zip(gross, lows, strict=True)} == {(500, 0), (-500, -500)}
    assert 200 < gross.count(500) < 300
    assert STRAT.matched_control(d, r, 500) == (gross, taken, lows)
    assert (
        STRAT.matched_control(dataclasses.replace(d, trade_date=date(2020, 1, 3)), r, 500)[0]
        != gross
    )
    assert STRAT.matched_control(d, dataclasses.replace(r, status="no_trade", trades=[]), 500) == (
        [0] * 500,
        [0] * 500,
        [0] * 500,
    )


def _table(orb_net_cents, rng):
    n = len(orb_net_cents)
    gross = np.asarray(orb_net_cents) + 622
    ctrl = rng.choice([-1, 1], size=(n, 500)) * np.abs(gross)[:, None]
    return engine.DayTable(
        dates=np.array(["2020-01-02"] * n),
        status=np.array(["traded"] * n),
        atr=np.zeros(n, int),
        orb_side=np.ones(n, int),
        orb_gross=gross,
        orb_low=np.minimum(gross, 0),
        orb_stress_gross=gross,
        orb_trades=np.ones(n, int),
        entry_bar_stops=np.zeros(n, int),
        gap_trades=np.zeros(n, int),
        ctrl_gross=ctrl,
        ctrl_stress_gross=ctrl,
        ctrl_trades=np.ones((n, 500), int),
        ctrl_ok=np.ones(n, bool),
        ctrl_low=np.minimum(ctrl, 0),
    )


def test_grading_scale_and_sharpe_requirement():
    rng = np.random.default_rng(1)
    steady = _table(rng.normal(1_200, 800, 1_200).round(), rng)  # ~$12/day, Sharpe ~24
    v = analysis.verdict(steady, "MES", 0.05, "late_momentum", replicates=999)
    assert v["outcome"] == "pass_to_execution_calibration" and v["grade"] == "good"
    erratic = _table(rng.normal(1_200, 40_000, 1_200).round(), rng)  # ~$12/day but Sharpe ~0.5
    v = analysis.verdict(erratic, "MES", 0.05, "late_momentum", replicates=999)
    assert v["grade"] == "fail" and any("Sharpe" in r for r in v["reasons"])
    assert analysis.grade(499, [(500, "small edge"), (1000, "good")]) == "fail"
    assert analysis.grade(1500, [(500, "small edge"), (1000, "good"), (1500, "strong")]) == "strong"


def test_honesty_counts_variations_not_code_versions(tmp_path):
    ledger = tmp_path / engine.LEDGER
    ledger.parent.mkdir(parents=True)
    rows = [
        {
            "fingerprint": "a",
            "family": "late_momentum",
            "settings": {"window_minutes": 30},
            "market": "MES",
            "roll": "fixed",
        },
        {
            "fingerprint": "b",
            "family": "late_momentum",
            "settings": {"window_minutes": 30},
            "market": "MES",
            "roll": "fixed",
        },
        {
            "fingerprint": "c",
            "family": "late_momentum",
            "settings": {"window_minutes": 30},
            "market": "MNQ",
            "roll": "fixed",
        },
    ]
    ledger.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    assert analysis.honesty(tmp_path, "late_momentum")["trials"] == 2

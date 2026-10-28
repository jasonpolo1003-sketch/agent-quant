"""Prop simulator Phase 2: account-aware sizing policies (Q6-Q7)."""

from __future__ import annotations

import dataclasses

import numpy as np
import pytest
from test_prop_simulator import _table

from quant_brain.config import BRAIN_DIR
from quant_brain.prop import replay
from quant_brain.prop.account import Rules
from quant_brain.prop.funded import XfaRules
from quant_brain.prop.policy import Days, Policy, evaluate_policy, load_policies, run_policy

PROP = BRAIN_DIR / "_system" / "prop"


def test_frozen_menu_loads_five_policies():
    ps = {p.name: p for p in load_policies(PROP / "sizing-policies.v1.json")}
    assert list(ps) == [
        "P1_fixed_2",
        "P2_fixed_3",
        "P3_cushion",
        "P4_cushion_dll",
        "P5_cushion_dll_stop",
    ]
    assert (ps["P2_fixed_3"].fixed, ps["P3_cushion"].fixed) == (3, None)
    assert ps["P5_cushion_dll_stop"].profit_stop == 1_500 and ps["P5_cushion_dll_stop"].dll


def test_cushion_size_fits_the_worst_day_in_the_cushion():
    p = Policy("c", None, False, None)
    assert [p.size(c) for c in (2_000, 1_886, 1_257, 300, 9_999)] == [3, 2, 1, 1, 5]


def test_fixed_policy_reproduces_the_cash_simulator_exactly():
    t = _table(edge=2_000)
    kw = (Rules(), XfaRules(), 42, 50)
    a_s, a_l = replay.cash_bootstrap(t, "MNQ", 2, *kw, np.random.default_rng(7))
    b_s, b_l = run_policy(
        Days(t, "MNQ"), Policy("f", 2, False, None), *kw, np.random.default_rng(7)
    )
    for x, y in zip(a_s + a_l, b_s + b_l, strict=True):
        assert x.net == pytest.approx(y.net) and x.first_payout_day == y.first_payout_day


def _one_day(records, gross, low):
    t = _table(n=1)
    return dataclasses.replace(
        t,
        orb_gross=np.array([gross]),
        orb_low=np.array([low]),
        orb_trades=np.array([1]),
        orb_rec=np.array(records, dtype=np.int64).reshape(-1, 2),
        orb_rec_off=np.array([0, len(records)]),
    )


COST = 3.22  # MNQ L3 per contract


def test_profit_stop_takes_the_target_when_it_comes_first():
    days = Days(
        _one_day([(-5_000, 0), (-5_000, 60_000), (-90_000, 60_000)], -80_000, -90_000), "MNQ"
    )
    close, low = days.outcome(0, None, 3, None, 1_500)
    assert close == pytest.approx(1_500 - 3 * 2 * 0.5)  # out at +$1,500 less 2 ticks
    assert low == pytest.approx(3 * (-50 - COST))
    assert days.outcome(0, None, 3, None, None)[0] == pytest.approx(3 * (-800 - COST))


def test_dll_first_beats_a_later_profit_stop():
    days = Days(_one_day([(-40_000, 0), (-40_000, 60_000)], 50_000, -40_000), "MNQ")
    close, _ = days.outcome(0, None, 3, 1_000, 1_500)  # 3 x -$400 = -$1,200 hits the DLL
    assert close == pytest.approx(-1_003)


def test_minute_touching_both_counts_as_adverse():
    days = Days(_one_day([(-40_000, 60_000)], 50_000, -40_000), "MNQ")
    assert days.outcome(0, None, 3, 1_000, 1_500)[0] == pytest.approx(-1_003)


def test_strong_edge_policy_beats_luck_and_no_edge_does_not():
    combine = Rules.from_json(PROP / "topstep_50k.json")
    p = Policy("c", None, True, None)
    kw = dict(n_paths=200, outer=10, inner=80)
    strong = evaluate_policy(_table(edge=6_000), "MNQ", p, combine, XfaRules(), **kw)
    assert strong["eligible"] and strong["net_cash_minus_luck_90ci"][0] > 0
    none = evaluate_policy(_table(edge=0), "MNQ", p, combine, XfaRules(), **kw)
    assert not none["eligible"]

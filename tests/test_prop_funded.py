"""Prop simulator Phase 2: funded account (XFA), payouts, daily loss limit, lifecycle."""

from __future__ import annotations

import dataclasses

import numpy as np
from test_prop_simulator import _table

from quant_brain.config import BRAIN_DIR
from quant_brain.prop import funded, replay
from quant_brain.prop.account import Rules
from quant_brain.prop.funded import XfaRules, apply_dll, lifecycle, xfa

PROP = BRAIN_DIR / "_system" / "prop"
STD = XfaRules()  # standard path, $2,000 cap, $149 activation
CON = dataclasses.replace(STD, path="consistency", cap=3_000)


def run(closes, lows=None, r=STD, horizon=None):
    lows = lows if lows is not None else [min(0.0, c) for c in closes]
    return xfa(closes, lows, r, horizon or len(closes))


# --- Q1: rules files ----------------------------------------------------------------------


def test_rules_files_load_with_sourced_values():
    r = XfaRules.from_json(PROP / "topstep_50k_xfa.json", "standard", dll=False, activation=149)
    assert (r.cap, r.winning_days, r.winning_day_min, r.split) == (2_000, 5, 150, 0.9)
    r = XfaRules.from_json(PROP / "topstep_50k_xfa.json", "consistency", dll=True, activation=0)
    assert (r.cap, r.trading_days, r.largest_day_share) == (6_000, 3, 0.40)
    combine, activation = funded.plan_rules(PROP / "topstep_50k.json", "no_activation_fee")
    assert (combine.subscription, combine.reset, activation) == (95, 95, 0)
    assert combine.lock_at_start  # the Combine limit locks at the start balance (2026-09-18)


# --- Q3: XFA state machine ------------------------------------------------------------------


def test_standard_payout_after_five_winning_days():
    o = run([200.0] * 5)
    assert o.paid == (500.0,) and o.payout_days == (5,)  # 50% of a $1,000 balance


def test_days_under_150_are_not_winning_days():
    assert run([149.0] * 10).paid == ()


def test_payout_is_capped():
    o = run([2_500.0] * 5)  # balance 12,500: 50% is 6,250, capped at 2,000
    assert o.paid == (2_000.0,)


def test_payout_below_the_minimum_is_not_paid():
    o = run([150.0] * 5 + [-700.0], horizon=5)  # sanity: 5 wins pay 375
    assert o.paid == (375.0,)
    o = run([-700.0] + [150.0] * 5)  # balance 50: 25 < 125
    assert o.paid == ()


def test_second_standard_payout_needs_profit_since_the_first():
    days = [1_000.0] * 5 + [-800.0] + [150.0] * 5  # since payout: 750 - 800 = -50
    o = run(days, [0.0] * 5 + [-800.0] + [0.0] * 5, horizon=11)
    assert o.paid == (2_000.0,)  # no second payout; balance 3,000 - 800 + 750 = 2,950
    assert not o.closed


def test_consistency_path_needs_largest_day_at_most_40_percent():
    assert run([300.0, 300.0, 300.0], r=CON).paid == (450.0,)
    assert run([600.0, 200.0, 100.0], r=CON).paid == ()  # 600 > 40% of 900
    o = run([600.0, 200.0, 100.0, 400.0, 300.0], r=CON)  # 600 <= 40% of 1,600 on day 5
    assert o.payout_days == (5,)


def test_floor_trails_then_locks_at_zero_before_any_payout():
    assert run([1_000.0, 0.0], [0.0, -2_000.0], r=CON).closed  # floor -1,000
    o = run([2_500.0, 0.0], [0.0, -2_400.0], r=CON)  # floor locks at 0, not 500
    assert not o.closed


def test_floor_is_zero_after_a_payout():
    o = run([200.0] * 5 + [0.0], [0.0] * 5 + [-500.0])  # balance 500 after the payout
    assert o.paid == (500.0,) and o.closed and o.days == 6


def test_breach_ends_the_account_before_a_same_day_payout():
    o = run([200.0] * 4 + [300.0], [0.0] * 4 + [-2_800.0])
    assert o.closed and o.paid == ()


# --- Q2: daily loss limit -------------------------------------------------------------------


def test_dll_caps_the_day_at_the_limit_plus_slippage():
    close, low = apply_dll(np.array([500.0, -300.0]), np.array([-1_200.0, -400.0]), 1_000, 4)
    assert close.tolist() == [-1_004.0, -300.0] and low.tolist() == [-1_200.0, -400.0]


# --- Q4: lifecycle --------------------------------------------------------------------------


def test_lifecycle_counts_combine_activation_and_trader_share():
    days = [1_500.0, 1_500.0] + [200.0] * 5
    o = lifecycle(days, [0.0] * 7, Rules(), STD, 7)
    assert o.combines_passed == 1 and o.first_payout_day == 7
    assert o.payouts == 450.0 and o.fees == 49 + 149 and o.net == 450.0 - 198


def test_lifecycle_restarts_a_combine_after_the_xfa_closes():
    days = [1_500.0, 1_500.0, 0.0, 1_500.0, 1_500.0]
    lows = [0.0, 0.0, -2_000.0, 0.0, 0.0]
    o = lifecycle(days, lows, Rules(), STD, 5)
    assert (o.combines_passed, o.xfas_closed) == (2, 1)
    assert o.fees == 2 * (49 + 149)


def test_no_trading_costs_only_the_subscription():
    o = lifecycle([0.0] * 42, [0.0] * 42, Rules(), STD, 42)
    assert o.net == -98 and o.first_payout_day is None  # months starting on day 1 and day 22


# --- Q7 shape: gate against luck --------------------------------------------------------------


def test_strong_edge_makes_cash_and_no_edge_does_not():
    combine = Rules.from_json(PROP / "topstep_50k.json")
    # 1 contract at this edge cannot reach the $3,000 target in 42 days; 5 can
    kw = dict(frozen_size=5, horizon=42, n_paths=300, outer=15, inner=100)
    strong = replay.evaluate_cash(_table(edge=6_000), "MNQ", combine, STD, **kw)
    assert strong["phase2_gate"] == "pass"
    none = replay.evaluate_cash(_table(edge=0), "MNQ", combine, STD, **kw)
    assert none["phase2_gate"] == "fail"
    # Losses stop at fees while payouts are uncapped below the cap, so even no-edge trading
    # can average positive cash at a large size: only the comparison with luck is evidence.
    assert none["by_size"]["1"]["strategy"]["mean_net_cash"] < 0


def test_dll_is_applied_to_luck_draws_too():
    t = _table(edge=0)
    _, _, c_close, _ = replay.cash_dollars(t, "MNQ", 5, dll=1_000)
    assert c_close.min() >= -(1_000 + 5 * replay.DLL_SLIP_TICKS * 0.5)

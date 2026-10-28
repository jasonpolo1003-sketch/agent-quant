"""Multi-firm prop simulator (plan E1). Hand-worked fixtures, written before the code.

Small round numbers, start balance $0, so every floor can be checked by hand:
max loss $500, so the first floor is -$500.
"""

from __future__ import annotations

import dataclasses
import json

import numpy as np
import pytest

from quant_brain.config import BRAIN_DIR
from quant_brain.prop import firm_sim, firms
from quant_brain.prop.account import Rules
from quant_brain.prop.firm_sim import evaluation, funded_account, lifecycle_arrays
from quant_brain.prop.firms import EvalRules, Fees, Firm, FundedRules
from quant_brain.prop.funded import XfaRules, lifecycle

PROP = BRAIN_DIR / "_system" / "prop"

EV = EvalRules(target=10_000, max_loss=500)  # target out of reach unless a test lowers it
# Funded: the floor locks at the start (0) and moves there after a payout (Topstep-like).
FU = FundedRules(
    max_loss=500,
    payout_share=0.5,
    cap=None,
    min_payout=100,
    split=0.8,
    lock=0.0,
    floor_after_payout=0.0,
)
FEES = Fees(billing="monthly", price=100, reset=50)


def firm(ev=EV, fu=FU, fees=FEES, **kw) -> Firm:
    return Firm("test", ev, fu, fees, **kw)


def ev_run(closes, lows, highs=None, ev=EV, fees=FEES, horizon=None, drawdowns=None):
    f = firm(ev=ev, fees=fees)
    fn = firm_sim.array_days(f, closes, lows, highs, drawdowns)
    return evaluation(f, fn, len(closes), horizon or len(closes))


def fu_run(closes, lows=None, highs=None, fu=FU):
    lows = lows if lows is not None else [min(0.0, c) for c in closes]
    f = firm(fu=fu)
    return funded_account(f, firm_sim.array_days(f, closes, lows, highs), len(closes), len(closes))


# --- EOD vs intraday trailing ---------------------------------------------------------------


def test_eod_floor_ignores_the_intraday_high_but_intraday_floor_follows_it():
    # Day 1 runs up to +600 and gives back to +300.
    #   EOD:      floor = 300 - 500 = -200.  Intraday: floor = 600 - 500 = +100.
    # Day 2 dips 250 from the open: equity low 50.  EOD survives (50 > -200); intraday breaches.
    # Give-backs from the running high are given (300 on day 1, 250 on day 2), as the minute
    # records would; without them the array path assumes the high came before the low.
    closes, lows, highs, dds = [300.0, 0.0], [0.0, -250.0], [600.0, 0.0], [300.0, 250.0]
    assert ev_run(closes, lows, highs, drawdowns=dds).resets == 0
    intra = dataclasses.replace(EV, drawdown="intraday_trailing")
    o = ev_run(closes, lows, highs, ev=intra, drawdowns=dds)
    assert (o.resets, o.days) == (1, 2)
    o = ev_run(closes, lows, highs, ev=intra)  # high-before-low: 600 give-back on day 1
    assert o.resets == 1


def test_intraday_trailing_breaches_inside_one_green_day():
    # +700 then back to +100: a 700 give-back from the day's high >= 500 (high taken before
    # the low: the conservative order). EOD never sees it: the day closes green.
    closes, lows, highs = [100.0], [0.0], [700.0]
    assert ev_run(closes, lows, highs).resets == 0
    intra = dataclasses.replace(EV, drawdown="intraday_trailing")
    assert ev_run(closes, lows, highs, ev=intra).resets == 1


def test_static_floor_never_moves():
    # +1,000 then -1,400 from the open: equity -400 > static floor -500.
    static = dataclasses.replace(EV, drawdown="static")
    assert ev_run([1_000.0, 0.0], [0.0, -1_400.0], ev=static).resets == 0
    assert ev_run([1_000.0, 0.0], [0.0, -1_400.0]).resets == 1  # EOD floor +500


def test_intraday_trailing_needs_highs_on_the_array_path():
    intra = dataclasses.replace(EV, drawdown="intraday_trailing")
    with pytest.raises(ValueError, match="high"):
        ev_run([100.0], [0.0], None, ev=intra)


# --- lock --------------------------------------------------------------------------------


def test_eod_lock_stops_the_floor_at_the_lock_level():
    # Day 1 +800: floor would be +300; locked at start + 0 = 0. Day 2 -700: equity +100.
    locked = dataclasses.replace(EV, lock=0.0)
    assert ev_run([800.0, 0.0], [0.0, -700.0], ev=locked).resets == 0
    assert ev_run([800.0, 0.0], [0.0, -700.0]).resets == 1  # floor 300 >= 100


def test_intraday_lock_caps_the_intraday_floor_too():
    # Day 1 +300 flat (floor -200). Day 2 runs +500 (equity 800), then back to +100 at the
    # close; the day's low is the open. Give-back 500 >= 500: unlocked, the floor reached
    # 800 - 500 = 300 and the open (300) touches it. Locked at 0: floor 0 < 300, survives.
    intra = dataclasses.replace(EV, drawdown="intraday_trailing")
    closes, lows, highs = [300.0, 100.0], [0.0, 0.0], [300.0, 500.0]
    assert ev_run(closes, lows, highs, ev=intra).resets == 1
    locked = dataclasses.replace(intra, lock=0.0)
    assert ev_run(closes, lows, highs, ev=locked).resets == 0


# --- soft vs hard daily loss ------------------------------------------------------------


def test_soft_daily_loss_flattens_the_day_and_hard_daily_loss_fails_the_account():
    # A -400 dip that recovers to -100, daily limit 300.
    soft = dataclasses.replace(EV, daily_loss=300, daily_loss_kind="soft_pause", target=200)
    hard = dataclasses.replace(soft, daily_loss_kind="hard_fail")
    closes, lows = [-100.0, 400.0], [-400.0, 0.0]
    o = ev_run(closes, lows, ev=soft)  # day 1 flattened at -300; day 2 +400 -> +100 < 200
    assert (o.resets, o.passed) == (0, False)
    o = ev_run(closes, lows, ev=hard)  # day 1 fails (reset, $50); day 2 +400 >= 200 passes
    assert (o.resets, o.passed, o.days, o.fees) == (1, True, 2, 150)


# --- eval consistency and minimum days -----------------------------------------------------


def test_eval_consistency_raises_the_target_and_min_days_delay_the_pass():
    ev = dataclasses.replace(EV, target=1_000, consistency=0.5)
    # Day 1 +900: best day 900 > 50% of 900, target rises to 1,800. Day 2 +900: passes.
    o = ev_run([900.0, 900.0], [0.0, 0.0], ev=ev)
    assert (o.passed, o.days) == (True, 2)
    three = dataclasses.replace(EV, target=1_000, min_days=3)
    o = ev_run([1_200.0, 10.0, -10.0], [0.0, 0.0, -10.0], ev=three)
    assert (o.passed, o.days) == (True, 3)  # the target was met on day 1; needs 3 trading days
    assert not ev_run([1_200.0, 0.0, 0.0], [0.0] * 3, ev=three).passed  # flat days do not count
    o = ev_run([1_200.0, 0.0, 0.0], [0.0, -1.0, -1.0], ev=three)
    assert o.passed and o.days == 3  # a day that only dipped still counts as traded


# --- fees --------------------------------------------------------------------------------


def test_monthly_vs_one_time_fees_and_resets():
    zeros = [0.0] * 42
    assert ev_run(zeros, zeros).fees == 200  # months start on days 1 and 22
    once = dataclasses.replace(FEES, billing="one_time")
    assert ev_run(zeros, zeros, fees=once).fees == 100
    # A failure with no reset product buys a new account at the full price.
    no_reset = dataclasses.replace(once, reset=None)
    assert ev_run([0.0, 0.0], [-500.0, 0.0], fees=no_reset).fees == 200
    # Monthly with no reset product: the new account starts its own month clock.
    m = dataclasses.replace(FEES, reset=None)
    o = ev_run([0.0] * 30, [-500.0] + [0.0] * 29, fees=m)  # fail day 1, new account day 2
    assert o.fees == 100 + 100 + 100  # first month, new account, its second month on day 23


def test_platform_fee_counts_every_month_the_bot_runs_and_activation_once():
    fees = dataclasses.replace(FEES, platform_per_month=30, activation=70)
    f = firm(fees=fees)
    o = lifecycle_arrays(f, [0.0] * 42, [0.0] * 42, horizon=42)
    assert o.fees == 200 + 2 * 30  # 2 months of eval and platform, no activation
    o = lifecycle_arrays(f, [0.0] * 43, [0.0] * 43, horizon=43)
    assert o.fees == 300 + 3 * 30
    ev = dataclasses.replace(EV, target=500)
    o = lifecycle_arrays(firm(ev=ev, fees=fees), [600.0] + [0.0] * 9, [0.0] * 10, horizon=10)
    assert (o.combines_passed, o.fees) == (1, 100 + 70 + 30)


# --- funded: payouts, consistency, after a payout -----------------------------------------


def test_funded_consistency_blocks_the_payout_until_satisfied():
    fu = dataclasses.replace(FU, consistency=0.4, trading_days=3)
    o = fu_run([600.0, 200.0, 100.0, 400.0, 300.0], fu=fu)
    # day 3: 600 > 40% of 900; day 4: 600 > 40% of 1,300; day 5: 600 <= 40% of 1,600
    assert o.paid == (800.0,) and o.payout_days == (5,)
    assert fu_run([600.0, 200.0, 100.0], fu=fu).paid == ()


def test_winning_days_buffer_cap_and_minimum():
    fu = dataclasses.replace(FU, winning_days=3, winning_day_min=200)
    assert fu_run([199.0] * 6, fu=fu).paid == ()
    assert fu_run([200.0] * 3, fu=fu).paid == (300.0,)  # 50% of 600
    buf = dataclasses.replace(fu, buffer=400)
    assert fu_run([200.0] * 3, fu=buf).paid == (100.0,)  # 50% of (600 - 400)
    assert fu_run([200.0] * 3, fu=dataclasses.replace(buf, min_payout=101)).paid == ()
    assert fu_run([2_000.0] * 3, fu=dataclasses.replace(fu, cap=1_000)).paid == (1_000.0,)


def test_after_a_payout_the_floor_moves_and_stops_trailing():
    # 3 x 200: floor -300, -100, then locked at 0. Payout 300 on day 3, balance 300; floor 0.
    fu = dataclasses.replace(FU, winning_days=3, winning_day_min=200)
    o = fu_run([200.0] * 3 + [0.0], [0.0] * 3 + [-300.0], fu=fu)
    assert o.paid == (300.0,) and o.closed and o.days == 4
    # No lock, no floor-after rule: the floor stays where it trailed to (600 - 500 = 100) and
    # keeps trailing from the lower balance: -200 -> equity 100, closed; -199 -> 101 survives.
    keep = dataclasses.replace(fu, lock=None, floor_after_payout=None)
    assert fu_run([200.0] * 3 + [0.0], [0.0] * 3 + [-199.0], fu=keep).closed is False
    assert fu_run([200.0] * 3 + [0.0], [0.0] * 3 + [-200.0], fu=keep).closed


def test_a_payout_never_leaves_the_balance_on_the_floor():
    # Floor after a payout = start + 300. 3 x 200 -> balance 600; all of it above the buffer
    # 0 at share 1.0 would leave 0 <= 300: no payout. Share 0.5 leaves 300 <= 300: none.
    fu = dataclasses.replace(FU, winning_days=3, winning_day_min=200, floor_after_payout=300.0)
    assert fu_run([200.0] * 3, fu=dataclasses.replace(fu, payout_share=1.0)).paid == ()
    assert fu_run([200.0] * 3, fu=fu).paid == ()
    assert fu_run([200.0] * 4, fu=fu).paid == (400.0,)  # balance 800: pays 400, leaves 400


def test_max_payouts_ends_the_funded_account_without_closing_it():
    fu = dataclasses.replace(FU, winning_days=1, winning_day_min=100, max_payouts=1)
    o = fu_run([400.0, 400.0], fu=fu)
    assert (o.paid, o.days, o.closed) == ((200.0,), 1, False)


def test_funded_hard_daily_loss_closes_and_soft_does_not():
    hard = dataclasses.replace(FU, daily_loss=300, daily_loss_kind="hard_fail")
    assert fu_run([-100.0, 0.0], [-350.0, 0.0], fu=hard).closed
    soft = dataclasses.replace(hard, daily_loss_kind="soft_pause")
    assert not fu_run([-100.0, 0.0], [-350.0, 0.0], fu=soft).closed


# --- Topstep reproduction (old path == generic path) ---------------------------------------


def _random_days(rng, n):
    closes = rng.normal(150, 700, n).round(2)
    lows = np.minimum(closes, 0) - np.abs(rng.normal(0, 400, n)).round(2)
    return closes, lows


@pytest.mark.parametrize("plan", ["standard", "no_activation_fee"])
@pytest.mark.parametrize("path", ["standard", "consistency"])
@pytest.mark.parametrize("dll", [False, True])
def test_topstep_adapter_reproduces_the_old_lifecycle_exactly(plan, path, dll):
    from quant_brain.prop import funded

    combine, activation = funded.plan_rules(PROP / "topstep_50k.json", plan)
    xr = XfaRules.from_json(PROP / "topstep_50k_xfa.json", path, dll=dll, activation=activation)
    f = firms.topstep(PROP / "topstep_50k.json", PROP / "topstep_50k_xfa.json")[f"{plan}/{path}"]
    f = f.with_optional_daily_loss(dll)
    rng = np.random.default_rng(11)
    for _ in range(400):
        c, lo = _random_days(rng, 60)
        # The old path's caller applies the DLL to the arrays (here with zero slippage); the
        # generic array path flattens soft-limit days itself, the same way.
        c_old, lo_old = funded.apply_dll(c, lo, 1_000) if dll else (c, lo)
        assert lifecycle_arrays(f, c, lo, horizon=42) == lifecycle(c_old, lo_old, combine, xr, 42)


@pytest.mark.parametrize(
    "rules",
    [Rules(), Rules(lock_at_start=False), Rules(trailing=False), Rules(consistency=None)],
)
def test_legacy_rules_reproduce_the_old_lifecycle_exactly(rules):
    con = dataclasses.replace(XfaRules(), path="consistency", cap=3_000)
    for xr in (XfaRules(), con):
        f = firms.from_legacy(rules, xr)
        rng = np.random.default_rng(12)
        for _ in range(300):
            c, lo = _random_days(rng, 50)
            assert lifecycle_arrays(f, c, lo, horizon=42) == lifecycle(c, lo, rules, xr, 42)


# --- schema loader -----------------------------------------------------------------------


def _draft(**over):
    d = {
        "firm": "Example",
        "account": "50K",
        "automation_allowed_eval": True,
        "automation_allowed_funded": True,
        "start_balance_usd": 50_000,
        "price_usd": {"value": 99, "source": "pricing page"},
        "billing": "one_time",
        "reset_usd": 79,
        "activation_usd": 0,
        "platform_fees_usd_per_month": 0,
        "target_usd": 3_000,
        "max_loss_usd": 2_500,
        "drawdown_mode": "intraday_trailing",
        "drawdown_lock_usd": 100,
        "daily_loss_usd": None,
        "daily_loss_kind": None,
        "eval_consistency_share": None,
        "min_days": 7,
        "max_micros": 40,
        "funded": {
            "max_loss_usd": 2_500,
            "drawdown_mode": "eod_trailing",
            "drawdown_lock_usd": 100,
            "daily_loss_usd": 1_000,
            "daily_loss_kind": "hard_fail",
            "consistency_share": 0.3,
            "payout_min_winning_days": 5,
            "payout_winning_day_usd": 50,
            "payout_buffer_usd": 100,
            "payout_share": 1.0,
            "payout_cap_usd": 2_000,
            "min_payout_usd": 500,
            "profit_split": 0.9,
        },
    }
    d.update(over)
    return d


def test_loader_maps_the_research_names(tmp_path):
    p = tmp_path / "example.json"
    p.write_text(json.dumps(_draft()), encoding="utf-8")
    ((name, f),) = firms.load_firm(p).items()
    assert name == "default" and f.name == "example"
    assert f.fees == Fees(billing="one_time", price=99, reset=79)
    assert f.evaluation.drawdown == "intraday_trailing" and f.evaluation.lock == 100
    assert (f.evaluation.min_days, f.evaluation.start, f.max_micros) == (7, 50_000, 40)
    fu = f.funded
    assert (fu.daily_loss, fu.daily_loss_kind, fu.consistency, fu.buffer) == (
        1_000,
        "hard_fail",
        0.3,
        100,
    )
    assert (fu.winning_days, fu.winning_day_min, fu.cap, fu.split) == (5, 50, 2_000, 0.9)
    assert f.automation_allowed


def test_loader_fails_loudly(tmp_path):
    p = tmp_path / "bad.json"
    d = _draft()
    del d["target_usd"]
    p.write_text(json.dumps(d), encoding="utf-8")
    with pytest.raises(ValueError, match="target"):
        firms.load_firm(p)
    p.write_text(json.dumps(_draft(drawdown_mode="sometimes")), encoding="utf-8")
    with pytest.raises(ValueError, match="drawdown"):
        firms.load_firm(p)
    p.write_text(json.dumps(_draft(daily_loss_usd=500)), encoding="utf-8")  # kind missing
    with pytest.raises(ValueError, match="daily_loss_kind"):
        firms.load_firm(p)
    d = _draft()
    del d["drawdown_lock_usd"]
    p.write_text(json.dumps(d), encoding="utf-8")
    with pytest.raises(ValueError, match="lock"):
        firms.load_firm(p)


def test_loader_expands_plans_and_payout_paths(tmp_path):
    d = _draft(
        plans={"cheap": {"price_usd": 49, "activation_usd": 130}, "pro": {"price_usd": 149}},
        payout_paths={"a": {}, "b": {"consistency_share": None, "payout_cap_usd": None}},
    )
    p = tmp_path / "x.json"
    p.write_text(json.dumps(d), encoding="utf-8")
    v = firms.load_firm(p)
    assert sorted(v) == ["cheap/a", "cheap/b", "pro/a", "pro/b"]
    assert (v["cheap/a"].fees.price, v["cheap/a"].fees.activation) == (49, 130)
    assert v["pro/b"].funded.consistency is None and v["pro/b"].funded.cap is None


def test_topstep_adapter_matches_the_legacy_objects():
    from quant_brain.prop import funded

    v = firms.topstep(PROP / "topstep_50k.json", PROP / "topstep_50k_xfa.json")
    assert sorted(v) == [
        "no_activation_fee/consistency",
        "no_activation_fee/standard",
        "standard/consistency",
        "standard/standard",
    ]
    f = v["standard/standard"]
    assert f.fees == Fees("monthly", 49, 49, activation=149)
    assert (f.evaluation.lock, f.evaluation.consistency, f.funded.floor_after_payout) == (
        0,
        0.55,
        0,
    )
    assert (f.max_micros, f.funded_max_micros) == (50, 20)
    on = f.with_optional_daily_loss(True)
    assert (on.funded.cap, on.evaluation.daily_loss, on.evaluation.daily_loss_kind) == (
        4_000,
        1_000,
        "soft_pause",
    )
    combine, act = funded.plan_rules(PROP / "topstep_50k.json", "standard")
    xr = XfaRules.from_json(PROP / "topstep_50k_xfa.json", "standard", dll=False, activation=act)
    legacy = firms.from_legacy(combine, xr)
    assert (legacy.evaluation, legacy.funded, legacy.fees) == (f.evaluation, f.funded, f.fees)


# --- direct-to-funded, payout schedules, consistency scopes, close-only breach -----------------


def test_direct_account_buys_the_funded_account_each_time():
    # No evaluation: $300 per funded account. Day 1 +400 pays 200 (1 winning day >= 100);
    # day 2 dips 200: equity 0 touches the floor (0 after the payout), closed; a new account
    # is bought on day 3. Net = 0.8 x 200 - 2 x 300.
    fu = dataclasses.replace(FU, winning_days=1, winning_day_min=100)
    f = firm(ev=None, fu=fu, fees=Fees("one_time", 300, None))
    o = lifecycle_arrays(f, [400.0, 0.0, 0.0, 0.0], [0.0, -200.0, 0.0, 0.0], horizon=4)
    assert (o.combines_passed, o.xfas_closed, o.first_payout_day) == (2, 1, 1)
    assert (o.fees, o.payouts, o.net) == (600, 160, -440)
    with pytest.raises(ValueError, match="one_time"):
        firm(ev=None, fu=fu)  # monthly billing without an evaluation is not defined


def test_payout_cap_and_profit_goal_schedules_by_payout_number():
    # caps 100 then 150 (repeats); profit goals 300 then 500 (repeats); 50% of the balance.
    fu = dataclasses.replace(
        FU,
        winning_days=1,
        winning_day_min=100,
        cap_schedule=(100, 150),
        min_profit_schedule=(300, 500),
    )
    o = fu_run([400.0, 400.0, 600.0, 600.0], fu=fu)
    # day 1: 400 >= 300, pays min(200, 100); day 2: 400 < 500; day 3: 1,000 >= 500, pays
    # min(650, 150); day 4: 600 >= 500, pays min(875, 150)
    assert o.paid == (100.0, 150.0, 150.0) and o.payout_days == (1, 3, 4)


@pytest.mark.parametrize(
    ("scope", "days"), [("cycle", (2, 4)), ("best_ever", (2, 5)), ("total", (2, 3, 4, 5))]
)
def test_consistency_scope(scope, days):
    # Largest day <= 50%. Days 300, 300 | 200, 200, 200. All scopes pay on day 2 (300 <= 300).
    # cycle: day 4 (200 <= 50% of 400). best_ever: the 300 day counts until the cycle makes
    # 600 (day 5). total: 300 <= 50% of every day's sum from day 3 on: pays daily.
    fu = dataclasses.replace(FU, consistency=0.5, consistency_scope=scope)
    assert fu_run([300.0, 300.0, 200.0, 200.0, 200.0], fu=fu).payout_days == days


def test_close_only_breach_ignores_the_intraday_low():
    close_only = dataclasses.replace(EV, breach_intraday=False)
    assert ev_run([-100.0], [-600.0], ev=close_only).resets == 0
    assert ev_run([-100.0], [-600.0]).resets == 1
    assert ev_run([-500.0], [-500.0], ev=close_only).resets == 1


# --- flat research layout ---------------------------------------------------------------------


def _flat(**over):
    """A flat draft in the research layout (Topstep 50K standard numbers)."""
    d = {
        "firm": "Topstep",
        "account_size_usd": 50_000,
        "has_evaluation": True,
        "price_usd": 49,
        "billing": "monthly",
        "reset_usd": 49,
        "activation_usd": 149,
        "platform_fees_usd_per_month": 0,
        "api_fee_usd_per_month": 29,
        "target_usd": 3_000,
        "max_loss_usd": 2_000,
        "drawdown_mode": "eod_trailing",
        "drawdown_breach_intraday": True,
        "drawdown_lock": "text is ignored",
        "drawdown_lock_level_rel_start_usd": 0,
        "drawdown_lock_trigger_rel_start_usd": 2_000,
        "daily_loss_usd": 1_000,
        "daily_loss_kind": "soft_pause",
        "daily_loss_optional": True,
        "eval_consistency_share": 0.55,
        "min_days": 2,
        "max_micros": 50,
        "funded_start_balance_usd": 0,
        "funded_max_loss_usd": 2_000,
        "funded_drawdown_mode": "eod_trailing",
        "funded_lock_level_rel_start_usd": 0,
        "funded_lock_trigger_rel_start_usd": 2_000,
        "funded_daily_loss_usd": 1_000,
        "funded_daily_loss_kind": "soft_pause",
        "funded_consistency_share": 0.4,
        "funded_max_micros": 20,
        "payout_min_winning_days": 5,
        "payout_winning_day_min_usd": 150,
        "payout_min_cycle_profit_usd": None,
        "payout_buffer_rel_start_usd": None,
        "payout_share_of_profit": None,
        "payout_share_of_balance": 0.5,
        "payout_cap_usd": 2_000,
        "payout_cap_schedule_usd": None,
        "payout_min_usd": 125,
        "profit_split_trader": 0.9,
        "max_payouts": None,
        "automation_allowed_eval": True,
        "automation_allowed_funded": True,
        "payout_paths": ["standard", "consistency"],
        "payout_consistency_path_min_days": 3,
        "payout_consistency_path_share": 0.4,
        "payout_cap_consistency_path_usd": 3_000,
        "payout_cap_with_dll_usd": 4_000,
        "payout_cap_consistency_path_with_dll_usd": 6_000,
    }
    d.update(over)
    return d


def _load(tmp_path, d, name="flat"):
    p = tmp_path / f"{name}.json"
    p.write_text(json.dumps(d), encoding="utf-8")
    return firms.load_firm(p)


def test_flat_layout_with_topstep_payout_paths(tmp_path):
    v = _load(tmp_path, _flat())
    std, con = v["standard"], v["consistency"]
    assert std.fees == Fees("monthly", 49, 49, activation=149, platform_per_month=29)
    assert (std.evaluation.lock, std.evaluation.min_days, std.evaluation.daily_loss) == (0, 2, None)
    assert (std.optional_daily_loss, std.max_micros, std.funded_max_micros) == (1_000, 50, 20)
    s = std.funded
    got = (s.consistency, s.winning_days, s.needs_profit, s.cap, s.floor_after_payout)
    assert got == (None, 5, "after_first", 2_000, 0)
    assert std.with_optional_daily_loss(True).funded.cap == 4_000
    c = con.funded
    got = (c.consistency, c.winning_days, c.trading_days, c.needs_profit, c.cap)
    assert got == (0.4, 0, 3, "always", 3_000)
    assert con.with_optional_daily_loss(True).funded.cap == 6_000
    # The research Topstep numbers equal the verified adapter (bar min days and the API fee).
    adapter = firms.topstep(PROP / "topstep_50k.json", PROP / "topstep_50k_xfa.json")
    for path in ("standard", "consistency"):
        a = adapter[f"standard/{path}"]
        assert dataclasses.replace(v[path].evaluation, min_days=0) == a.evaluation
        assert v[path].funded == a.funded


def test_flat_layout_rules(tmp_path):
    with pytest.raises(ValueError, match="disagree"):
        _load(tmp_path, _flat(drawdown_lock_trigger_rel_start_usd=2_100))
    with pytest.raises(ValueError, match="payout_paths"):
        _load(tmp_path, _flat(payout_paths=["a", "b"]))
    one = _flat(payout_paths=None, funded_consistency_share=0.2)
    f = _load(tmp_path, one)["default"]
    assert f.funded.consistency == 0.2 and f.evaluation is not None
    # No share but a buffer: everything above the buffer; neither: refuse.
    nb = _flat(payout_paths=None, payout_share_of_balance=None, payout_buffer_rel_start_usd=2_100)
    assert _load(tmp_path, nb)["default"].funded.payout_share == 1.0
    with pytest.raises(ValueError, match="payout_share"):
        _load(tmp_path, _flat(payout_paths=None, payout_share_of_balance=None))
    with pytest.raises(ValueError, match="conflicting"):
        _load(tmp_path, _flat(payout_paths=None, payout_share_of_profit=0.4))
    direct = _flat(
        payout_paths=None,
        has_evaluation=False,
        billing="one_time",
        target_usd=None,
        max_loss_usd=None,
    )
    assert _load(tmp_path, direct)["default"].evaluation is None
    sched = _flat(payout_paths=None, payout_cap_schedule_usd=[1_500, 2_000], payout_cap_usd=None)
    assert _load(tmp_path, sched)["default"].funded.cap_at(5) == 2_000
    with pytest.raises(ValueError, match="price"):
        _load(tmp_path, _flat(price_usd=None))


def test_research_drafts_load_or_fail_loudly():
    drafts = sorted((PROP / "firms").glob("*.json"))
    if not drafts:
        pytest.skip("no research drafts yet")
    for p in drafts:
        try:
            firms.load_firm(p)
        except ValueError:
            pass  # a loud, named refusal is fine; anything else is a loader bug


# --- QA 2026-10-28: payout semantics read from the official pages ---------------------------


def test_min_balance_gates_the_request_but_is_not_a_buffer():
    # Tradeify Growth: request needs balance >= start + 3,000; the request is capped, not
    # limited to the excess over 3,000 (official example: 53,000 -> request 1,500 -> 51,500).
    fu = dataclasses.replace(
        FU,
        max_loss=2_000,
        payout_share=1.0,
        lock=100.0,
        floor_after_payout=100.0,
        winning_days=1,
        winning_day_min=150,
        min_balance=3_000,
        cap_schedule=(1_500.0, 3_000.0),
        min_payout=500,
    )
    assert fu_run([1_000.0, 1_000.0], fu=fu).paid == ()  # balance 2,000 < 3,000
    o = fu_run([1_000.0, 1_000.0, 1_000.0], fu=fu)
    assert o.paid == (1_500.0,) and o.payout_days == (3,)  # leaves 1,500 above start
    # Second request: cap 3,000 at balance 3,000 would leave 0 <= floor 100: clipped to 2,899.
    o = fu_run([1_000.0] * 3 + [1_500.0], fu=fu)
    assert o.paid == (1_500.0, 2_899.0)


def test_cycle_payout_base_pays_a_share_of_profit_since_the_last_payout():
    # FundedNext Flex: "up to 50% of your profit per cycle".
    fu = dataclasses.replace(FU, winning_days=1, winning_day_min=100, payout_base="cycle")
    o = fu_run([1_000.0, 200.0], fu=fu)
    assert o.paid == (500.0, 100.0)  # 50% of 200, not 50% of the 700 balance
    total = dataclasses.replace(fu, payout_base="balance")
    assert fu_run([1_000.0, 200.0], fu=total).paid == (500.0, 350.0)


def test_max_cycle_multiple_limits_the_request():
    # Tradeify Select Daily: "up to 2x the profit earned between each payout request".
    fu = dataclasses.replace(
        FU,
        payout_share=1.0,
        cap=300.0,
        min_payout=10,
        winning_days=0,
        max_cycle_multiple=2,
    )
    o = fu_run([1_000.0, 50.0], fu=fu)
    assert o.paid == (300.0, 100.0)  # without the rule the second request would be 300
    assert fu_run([1_000.0, 50.0], fu=dataclasses.replace(fu, max_cycle_multiple=None)).paid == (
        300.0,
        300.0,
    )


def test_qa_corrected_research_values():
    def fund(name):
        return firms.load_firm(PROP / "firms" / f"{name}.json")["default"].funded

    g = fund("tradeify_growth_50k")
    assert (g.buffer, g.payout_share, g.min_balance) == (0.0, 1.0, 3_000)
    assert fund("tradeify_select_daily_50k").max_cycle_multiple == 2
    assert fund("fundednext_flex_50k").payout_base == "cycle"
    assert fund("fundednext_direct_50k").consistency_scope == "best_ever"

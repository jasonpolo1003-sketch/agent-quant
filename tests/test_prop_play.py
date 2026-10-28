"""Phase-aware account play (plan E1): per-phase size and profit stop, stop at target, soft
and hard daily losses, the same play for luck. Hand-worked fixtures, written before the code.
"""

from __future__ import annotations

import dataclasses
import itertools
import json

import numpy as np
import pytest
from test_prop_simulator import _table

from quant_brain.prop import firms, play
from quant_brain.prop.account import Rules
from quant_brain.prop.firm_sim import DayContext
from quant_brain.prop.firms import EvalRules, Fees, Firm, FundedRules
from quant_brain.prop.funded import XfaRules
from quant_brain.prop.play import Play
from quant_brain.prop.policy import Days, Policy, run_policy

COST = 3.22  # MNQ L3 per contract round trip


def _one_day(records, gross, low):
    t = _table(n=1)
    return dataclasses.replace(
        t,
        orb_gross=np.array([gross]),
        orb_low=np.array([low]),
        orb_trades=np.array([1]),
        orb_rec=np.array(records, dtype=np.int64).reshape(-1, 2),
        orb_rec_off=np.array([0, len(records)]),
        ctrl_rec=np.array(records, dtype=np.int64).reshape(-1, 2),
        ctrl_rec_off=np.array([0, len(records)]),
        ctrl_rec_idx=np.zeros((1, t.ctrl_gross.shape[1]), np.int64),
    )


def rec_table(n=400, edge=0.0, seed=3, draws=50):
    """Synthetic days with minute records: the high (gross + 10%) first, then the low."""
    rng = np.random.default_rng(seed)
    gross = rng.normal(edge, 15_000, n).round().astype(np.int64)
    low = np.minimum(gross, 0) - np.abs(rng.normal(0, 3_000, n)).round().astype(np.int64)
    high = np.maximum(gross, 0) + 100
    sign = rng.choice([-1, 1], size=(n, draws))
    ctrl = sign * np.abs(gross)[:, None]
    recs, off = [], [0]
    for i in range(n):
        recs += [(0, high[i]), (low[i], high[i])]
        off.append(len(recs))
    c_recs, c_off = [], [0]
    for i in range(n):  # path 2i: control long (= the strategy's shape), 2i + 1: short
        g = abs(int(gross[i]))
        for s in (1, -1):
            c_hi = max(s * g, 0) + 100
            c_recs += [(0, c_hi), (min(s * g, 0), c_hi)]
            c_off.append(len(c_recs))
    idx = 2 * np.arange(n)[:, None] + (sign < 0)
    base = _table(n=n, seed=seed)
    return dataclasses.replace(
        base,
        orb_gross=gross,
        orb_low=low,
        orb_stress_gross=gross,
        ctrl_gross=ctrl,
        ctrl_stress_gross=ctrl,
        ctrl_trades=np.ones((n, draws), int),
        ctrl_low=np.minimum(ctrl, 0),
        orb_rec=np.array(recs, np.int64),
        orb_rec_off=np.array(off, np.int64),
        ctrl_rec=np.array(c_recs, np.int64),
        ctrl_rec_off=np.array(c_off, np.int64),
        ctrl_rec_idx=idx.astype(np.int64),
    )


# One day, per contract (cents): +$200 high, -$50 low; then +$600; then -$100; closes -$80.
DAY = _one_day([(-5_000, 20_000), (10_000, 60_000), (-10_000, 0)], -8_000, -10_000)


# --- day extremes from the minute records ---------------------------------------------------


def test_extremes_follow_the_minute_records():
    d = Days(DAY, "MNQ")
    # Costs come off the start: high 600 - 3.22; the give-back is 600 -> -100 = 700.
    high, give, stop_low = d.extremes(0, None, 1, None, None)
    assert (high, give, stop_low) == pytest.approx((596.78, 700.0, -103.22))
    # DLL 50 in the first minute (-53.22): out at -51 (2 ticks). That minute's high counts first.
    assert d.outcome(0, None, 1, 50, None) == pytest.approx((-51.0, -103.22))  # old low kept
    high, give, stop_low = d.extremes(0, None, 1, 50, None)
    assert (high, give, stop_low) == pytest.approx((196.78, 250.0, -51.0))
    # Profit stop 400 in minute 2: out at 399; the high is the stop, not the minute's 596.78.
    assert d.outcome(0, None, 1, None, 400)[0] == pytest.approx(399.0)
    high, give, stop_low = d.extremes(0, None, 1, None, 400)
    assert (high, give, stop_low) == pytest.approx((400.0, 250.0, -53.22))
    # Two contracts double everything (slippage 2 x 2 ticks).
    assert d.extremes(0, None, 2, None, None) == pytest.approx((1_193.56, 1_400.0, -206.44))


# --- per-phase size, profit stop, stop at target ---------------------------------------------

FIRM = Firm(
    "t",
    EvalRules(target=3_000, max_loss=2_000, consistency=0.5),
    FundedRules(
        max_loss=2_000, payout_share=0.5, cap=None, min_payout=0, split=0.9, consistency=0.4
    ),
    Fees("monthly", 100, 100),
    max_micros=10,
    funded_max_micros=4,
)


def ctx(phase, to_target=None):
    return DayContext(phase, 0, 1_000.0, to_target)


def test_named_stops_and_size_caps_resolve_per_firm():
    p = Play("p", 12, 6, "consistency_safe", "funded_consistency_safe")
    r = play.resolve(p, FIRM)
    assert (r.eval.size, r.funded.size) == (10, 4)  # cut to the firm's max micros
    assert r.eval.stop == pytest.approx(0.9 * 0.5 * 3_000)  # 1,350
    assert r.funded.stop == pytest.approx(0.9 * 0.4 * 3_000)  # no funded profit rule: target
    fu = dataclasses.replace(FIRM.funded, min_profit=1_000)
    r = play.resolve(p, dataclasses.replace(FIRM, funded=fu))
    assert r.funded.stop == pytest.approx(360)
    bare = dataclasses.replace(
        FIRM,
        evaluation=dataclasses.replace(FIRM.evaluation, consistency=None),
        funded=dataclasses.replace(FIRM.funded, consistency=None),
    )
    r = play.resolve(p, bare)
    assert (r.eval.stop, r.funded.stop) == (None, None)


def test_profit_stop_differs_by_phase():
    fn = play.day_fn(
        Days(DAY, "MNQ"), play.resolve(Play("p", 1, 1, 400, None, stop_at_target=False), FIRM), [0]
    )
    assert fn(ctx("eval")).close == pytest.approx(399.0)
    assert fn(ctx("funded")).close == pytest.approx(-83.22)


def test_stop_at_target_flattens_once_the_target_is_in():
    # $200 still needed: stop at 200 + 1 (slippage) + 0.01, out at 200.01 -> the attempt passes.
    r = play.resolve(Play("p", 1, 1, 400, None, stop_at_target=True), FIRM)
    fn = play.day_fn(Days(DAY, "MNQ"), r, [0])
    assert fn(ctx("eval", to_target=200.0)).close == pytest.approx(200.01)
    # Out of reach today (the day never makes $1,000): the day plays out with the 400 stop.
    assert fn(ctx("eval", to_target=1_000.0)).close == pytest.approx(399.0)
    off = play.day_fn(
        Days(DAY, "MNQ"), play.resolve(Play("p", 1, 1, None, None, stop_at_target=False), FIRM), [0]
    )
    assert off(ctx("eval", to_target=200.0)).close == pytest.approx(-83.22)


def test_daily_loss_soft_firm_limit_own_stop_and_hard_limit():
    d = Days(DAY, "MNQ")
    soft = dataclasses.replace(
        FIRM,
        evaluation=dataclasses.replace(
            FIRM.evaluation, daily_loss=50, daily_loss_kind="soft_pause"
        ),
    )
    fn = play.day_fn(d, play.resolve(Play("p", 1, 1, stop_at_target=False), soft), [0])
    p = fn(ctx("eval"))
    # flattened by the firm at -50; the floor sees the low until the exit (QA 2026-10-28)
    assert (p.close, p.low) == pytest.approx((-51.0, -51.0))
    assert fn(ctx("funded")).close == pytest.approx(-83.22)  # funded has no daily loss
    hard = dataclasses.replace(
        FIRM,
        evaluation=dataclasses.replace(FIRM.evaluation, daily_loss=60, daily_loss_kind="hard_fail"),
    )
    own = Play("p", 1, 1, stop_at_target=False, daily_loss_stop=50)
    p = play.day_fn(d, play.resolve(own, hard), [0])(ctx("eval"))
    # The bot's own stop at -50 exits at -51: the hard limit (-60) and the floor are judged on
    # the low until the exit, not on the later -103.22 (kept only with post_exit_lows=True).
    assert (p.close, p.low, p.stop_low) == pytest.approx((-51.0, -51.0, -51.0))
    opt = dataclasses.replace(FIRM, optional_daily_loss=50.0, cap_with_optional_daily_loss=9_999)
    r = play.resolve(Play("p", 1, 1, stop_at_target=False, optional_daily_loss=True), opt)
    assert (r.eval.dll, r.funded.dll, r.firm.funded.cap) == (50.0, 50.0, 9_999)
    r = play.resolve(Play("p", 1, 1, stop_at_target=False, optional_daily_loss=False), opt)
    assert (r.eval.dll, r.funded.dll, r.firm.funded.cap) == (None, None, None)


# --- the same play for luck; reproduction of the old policy path ------------------------------


def test_luck_plays_by_the_same_rules():
    # Every control draw copies the strategy's long shape: luck must equal the strategy.
    t = rec_table(n=200, edge=1_000, seed=4)
    t = dataclasses.replace(
        t,
        ctrl_gross=np.repeat(t.orb_gross[:, None], 50, 1),
        ctrl_low=np.repeat(t.orb_low[:, None], 50, 1),
        ctrl_rec_idx=np.repeat((2 * np.arange(200))[:, None], 50, 1),
    )
    # Long control records use the strategy's high but a low of min(gross, 0): give them the
    # strategy's records directly.
    t = dataclasses.replace(t, ctrl_rec=t.orb_rec, ctrl_rec_off=_pairs(t.orb_rec_off))
    f = firms.from_legacy(Rules(), XfaRules(), 1_000)
    p = Play("p", 3, 2, 1_200, 800, daily_loss_stop=700, optional_daily_loss=True)
    s, lk = play.run_play(Days(t, "MNQ"), p, f, 42, 60, np.random.default_rng(1))
    assert s == lk


def _pairs(off):
    """Offsets for a control store where path 2i is day i's strategy records and 2i+1 empty."""
    out = [0]
    for a, b in itertools.pairwise(off):
        out.append(out[-1] + (b - a))
        out.append(out[-1])
    return np.array(out, np.int64)


@pytest.mark.parametrize(
    ("dll", "stop"), [(False, None), (True, None), (True, 450.0), (False, 450.0)]
)
def test_fixed_play_reproduces_the_old_policy_path_exactly(dll, stop):
    # Thresholds small enough that the $300 DLL and the $450 stop fire on many days at 3 lots.
    t = rec_table(n=300, edge=2_000, seed=5)
    days = Days(t, "MNQ")
    closes = [days.outcome(i, None, 3, 300 if dll else None, stop)[0] for i in range(300)]
    if dll:
        assert sum(c == pytest.approx(-303) for c in closes) > 20
    if stop:
        assert sum(c == pytest.approx(447) for c in closes) > 20
    old_s, old_l = run_policy(
        days, Policy("f", 3, dll, stop), Rules(), XfaRules(), 42, 80, np.random.default_rng(7), 300
    )
    f = firms.from_legacy(Rules(), XfaRules(), 300)
    p = Play("f", 3, 3, stop, None, stop_at_target=False, optional_daily_loss=dll)
    new_s, new_l = play.run_play(
        Days(t, "MNQ"), p, f, 42, 80, np.random.default_rng(7), post_exit_lows=True
    )
    assert sum(o.combines_passed for o in old_s + old_l) > 10
    assert new_s == old_s and new_l == old_l


def test_strong_edge_passes_the_gate_and_no_edge_does_not():
    f = firms.from_legacy(Rules(), XfaRules(), 1_000)
    p = Play("p", 5, 3, "consistency_safe", None)
    kw = dict(n_paths=200, outer=10, inner=60)
    strong = play.evaluate_play(rec_table(edge=6_000), "MNQ", p, f, **kw)
    assert strong["gate"] == "pass", strong["net_cash_90ci"]
    assert strong["net_cash_90ci"][0] > 0 and strong["net_cash_minus_luck_90ci"][0] > 0
    none = play.evaluate_play(rec_table(edge=0), "MNQ", p, f, **kw)
    assert none["gate"] == "fail"
    assert {"chance_any_payout", "net_cash_5th_percentile"} <= set(none["strategy"])
    assert none["resolved"]["eval"]["stop"] == pytest.approx(0.9 * 0.55 * 3_000)


# --- menu ---------------------------------------------------------------------------------------


def test_menu_loads_named_stops_and_refuses_unknown_keys(tmp_path):
    menu = {
        "policies": {
            "P1": {
                "combine_size": 2,
                "funded_size": 2,
                "combine_profit_stop": "consistency_safe",
                "funded_profit_stop": None,
            },
            "P2": {
                "combine_size": 6,
                "funded_size": 2,
                "combine_profit_stop": 1_000,
                "funded_profit_stop": "funded_consistency_safe",
            },
        },
        "grid": {"horizon_days": 42, "cost_level": "L3"},
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(menu), encoding="utf-8")
    plays = play.load_plays(p)
    assert [x.name for x in plays] == ["P1", "P2"]
    assert plays[0] == Play(
        "P1", 2, 2, "consistency_safe", None, stop_at_target=True, optional_daily_loss=True
    )
    assert plays[1].combine_profit_stop == 1_000
    menu["policies"]["P1"]["combine_profit_stop"] = "whatever"
    p.write_text(json.dumps(menu), encoding="utf-8")
    with pytest.raises(ValueError, match="whatever"):
        play.load_plays(p)
    menu["policies"]["P1"] = {"combine_size": 2, "funded_size": 2, "colour": "red"}
    p.write_text(json.dumps(menu), encoding="utf-8")
    with pytest.raises(ValueError, match="colour"):
        play.load_plays(p)


def test_lows_after_a_dll_exit_do_not_breach_the_floor():
    # QA 2026-10-28. One day: DLL 50 fires in minute 1 (out at -51); the market later falls to
    # -103.22. With a floor $80 below the open, the old path breaches; the trader was flat.
    d = Days(DAY, "MNQ")
    f = Firm(
        "t",
        EvalRules(target=3_000, max_loss=80),
        FundedRules(max_loss=80, payout_share=0.5, cap=None, min_payout=0, split=0.9),
        Fees("monthly", 100, 100),
    )
    p = Play("p", 1, 1, None, None, daily_loss_stop=50, stop_at_target=False)
    r = play.resolve(p, f)
    new = play.day_fn(d, r, [0])(ctx("eval"))
    old = play.day_fn(d, r, [0], post_exit_lows=True)(ctx("eval"))
    assert new.close == old.close == pytest.approx(-51.0)
    assert new.low == pytest.approx(-51.0) and old.low == pytest.approx(-103.22)
    from quant_brain.prop import firm_sim

    assert firm_sim.evaluation(f, lambda c: new, 1, 1).resets == 0
    assert firm_sim.evaluation(f, lambda c: old, 1, 1).resets == 1


# --- state-dependent sizing (PROP-STATE-SIZING-v1) -------------------------------------------------


def test_a_sizer_returning_the_phase_size_changes_nothing():
    t = rec_table(n=300, edge=2_000, seed=5)
    f = firms.from_legacy(Rules(), XfaRules(), 1_000)
    p = Play("p", 4, 2, 1_200, None)
    a = play.run_play(Days(t, "MNQ"), p, f, 42, 60, np.random.default_rng(3))
    b = play.run_play(
        Days(t, "MNQ"), p, f, 42, 60, np.random.default_rng(3), sizer=lambda c, ph: ph.size
    )
    assert a == b
    kw = dict(n_paths=60, outer=4, inner=30)
    x = play.evaluate_play(t, "MNQ", p, f, **kw)
    y = play.evaluate_play(t, "MNQ", p, f, subset=np.arange(300), **kw)
    assert x == y
    assert x["luck_net_cash_90ci"][0] <= x["luck_net_cash_90ci"][1]


def test_the_sizer_sees_the_account_state_and_sets_the_size():
    t = rec_table(n=300, edge=2_000, seed=5)
    f = firms.from_legacy(Rules(), XfaRules(), 1_000)
    seen = []

    def sizer(c, ph):
        seen.append((c.phase, c.cushion))
        return max(1, int(c.cushion // 500))

    s, _ = play.run_play(
        Days(t, "MNQ"), Play("p", 1, 1), f, 42, 40, np.random.default_rng(2), sizer=sizer
    )
    assert {ph for ph, _ in seen} == {"eval", "funded"}
    assert len({cu for _, cu in seen}) > 10  # the cushion moves with the account
    one, _ = play.run_play(Days(t, "MNQ"), Play("p", 1, 1), f, 42, 40, np.random.default_rng(2))
    assert s != one


def test_a_subset_only_resamples_its_own_days():
    t = rec_table(n=300, edge=2_000, seed=5)
    days = Days(t, "MNQ")
    losers = np.flatnonzero(days.s_net < 0)
    f = firms.from_legacy(Rules(), XfaRules(), 1_000)
    r = play.evaluate_play(
        t, "MNQ", Play("p", 3, 2), f, n_paths=40, outer=3, inner=20, subset=losers
    )
    assert r["strategy"]["chance_any_payout"] == 0

"""Prop-evaluation simulator, Phase 1: intraday path, account rules, replays."""

from __future__ import annotations

import dataclasses

import numpy as np
from futures_day_builder import make_day

from quant_brain.config import BRAIN_DIR
from quant_brain.futures.orb import simulate_day
from quant_brain.prop import paths, replay
from quant_brain.prop.account import Rules, attempt

TICK = 50  # MNQ cents per tick
LONG = {"08:50": (105, 112, 105, 111), "08:51": (111, 112, 111, 112)}


def low_close(bars, missing=()):
    r = simulate_day(make_day(bars, missing=missing))
    return paths.day_path(make_day(bars, missing=missing).bars, r.trades, TICK)


# --- P2: intraday path ------------------------------------------------------------------


def test_stop_bar_low_beyond_the_stop_is_not_suffered():
    low, close = low_close({**LONG, "08:55": (108, 108, 98, 99)})  # stop 107 hit; low 98
    assert (low, close) == (-4 * TICK, -4 * TICK)


def test_flatten_bar_low_after_the_exit_open_is_not_suffered():
    bars = {**LONG, "08:52": (112, 130, 112, 130), "15:07": (130, 130, 100, 100)}
    low, close = low_close(bars)
    assert close == 19 * TICK and low == 0  # never below entry before the 15:07 open


def test_gap_stop_counts_the_gap_fill():
    low, close = low_close({**LONG, "08:52": (105, 106, 104, 105)})
    assert low == close == -6 * TICK


def test_two_trades_carry_realised_pnl_into_the_second():
    bars = {
        **LONG,
        "08:55": (108, 108, 106, 106),
        "09:00": (106, 106, 99, 99),
        "09:05": (99, 101, 99, 100),
    }
    low, close = low_close(bars)
    # long stopped at 107 (-4); short from 99: worst open is 101 high (-2) => -6 ticks
    assert (low, close) == (-6 * TICK, -5 * TICK)


def test_flipped_trade_worst_is_minus_the_best():
    assert paths.flipped_path(worst=-100, best=400, gross=300) == (-400, -300)


# --- P3: account rules (Topstep 50K shape) --------------------------------------------

R = Rules()


def test_intraday_breach_fails_even_on_a_green_close():
    o = attempt([500.0], [-2_000.0], R, 1)
    assert (o.passed, o.resets) == (False, 1)


def test_floor_trails_end_of_day_balance():
    o = attempt([1_000.0, 0.0], [0.0, -2_000.0], R, 2)  # floor 49,000 after day 1
    assert o.resets == 1
    fixed = dataclasses.replace(R, trailing=False)
    assert attempt([1_000.0, 0.0], [0.0, -2_000.0], fixed, 2).resets == 0


def test_floor_locks_at_start_balance():
    closes = [1_200.0, 1_200.0, 0.0]  # profits 2,400 (best day 50%, ok); floor would be 50,400
    o = attempt(closes, [0.0, 0.0, -2_300.0], R, 3)
    assert o.resets == 0  # lock: floor stays 50,000, so -2,300 from 52,400 survives


def test_failure_wins_a_day_that_touches_both():
    o = attempt([3_500.0], [-2_000.0], dataclasses.replace(R, consistency=None), 1)
    assert not o.passed and o.resets == 1


def test_consistency_raises_the_target():
    o = attempt([2_000.0, 1_000.0, 700.0], [0.0, 0.0, 0.0], R, 3)
    assert o.passed and o.days == 3  # 3,000 not enough while best day is 2,000 (> 55%)


def test_timeout_censoring_and_fees():
    o = attempt([0.0] * 50, [0.0] * 50, R, 126)
    assert not o.passed and o.censored and o.days == 50
    o = attempt([0.0] * 126, [0.0] * 126, R, 126)
    assert not o.censored and o.fees == 49 * 6


def test_gamblers_ruin_with_a_fixed_floor():
    fixed = dataclasses.replace(R, trailing=False, consistency=None)
    rng = np.random.default_rng(0)
    passes = 0
    for _ in range(4_000):
        steps = rng.choice([-100.0, 100.0], size=4_000)
        o = attempt(steps, np.minimum(steps, 0), fixed, 4_000)
        passes += o.passed and o.resets == 0
    assert abs(passes / 4_000 - 0.4) < 0.03


def test_bigger_size_never_breaches_later_with_target_and_lock_off():
    loose = dataclasses.replace(R, target=1e12, lock_at_start=False, consistency=None)
    rng = np.random.default_rng(1)
    for _ in range(200):
        c = rng.normal(0, 150, 126)
        lo = np.minimum(c, 0) - np.abs(rng.normal(0, 80, 126))

        def first_breach(scale):
            for d in range(1, 127):
                if attempt(c[:d] * scale, lo[:d] * scale, loose, d).resets:
                    return d
            return 999

        assert first_breach(3) <= first_breach(1)


# --- P4: replays --------------------------------------------------------------------


def test_block_paths_never_wrap_the_end_onto_the_start():
    idx = replay.block_paths(100, 500, 20, np.random.default_rng(2))
    steps = np.diff(idx, axis=1)
    jumps = steps != 1
    assert not ((idx[:, :-1] == 99) & (idx[:, 1:] == 0) & ~jumps).any()
    assert idx.min() >= 0 and idx.max() < 100


def _table(n=400, edge=0.0, seed=3):
    from quant_brain.workbench.engine import DayTable

    rng = np.random.default_rng(seed)
    side = np.ones(n, int)
    gross = rng.normal(edge, 15_000, n).round().astype(int)
    ctrl = rng.choice([-1, 1], size=(n, 500)) * np.abs(gross)[:, None]
    return DayTable(
        dates=np.array(["2020-01-02"] * n),
        status=np.array(["traded"] * n),
        atr=np.zeros(n, int),
        orb_side=side,
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


def test_strong_edge_passes_the_gate_and_no_edge_does_not():
    rules = Rules.from_json(BRAIN_DIR / "_system" / "prop" / "topstep_50k.json")
    strong = replay.evaluate(
        _table(edge=6_000), "MNQ", rules, frozen_size=1, n_paths=300, outer=15, inner=100
    )
    assert strong["phase1_gate"] == "pass"
    none = replay.evaluate(
        _table(edge=0), "MNQ", rules, frozen_size=1, n_paths=300, outer=15, inner=100
    )
    assert none["phase1_gate"] == "fail"
    assert none["by_size"]["1"]["luck"]["first_account_pass_rate"] is not None


def test_zero_variance_baseline_does_not_collapse():
    t = _table()
    t = dataclasses.replace(
        t,
        ctrl_gross=np.zeros_like(t.ctrl_gross),
        ctrl_low=np.zeros_like(t.ctrl_low),
        ctrl_stress_gross=np.zeros_like(t.ctrl_gross),
        ctrl_trades=np.zeros_like(t.ctrl_trades),
    )
    out = replay.evaluate(t, "MNQ", Rules(), frozen_size=1, n_paths=100, outer=5, inner=50)
    assert (
        out["by_size"]["1"]["luck"]["first_account_pass_rate"] == 0.0
    )  # flat luck never passes, and nothing crashes


def test_resets_let_random_trading_buy_a_pass_but_not_a_first_account_pass():
    out = replay.evaluate(
        _table(edge=0), "MNQ", Rules(), frozen_size=5, n_paths=300, outer=5, inner=50
    )
    luck = out["by_size"]["5"]["luck"]
    assert luck["pass_rate_with_resets"] > 0.8 > luck["first_account_pass_rate"]


def _slow_day_low(day, trades, tick):
    """Independent minute-by-minute equity replay (reference for paths.day_path)."""
    from quant_brain.futures.orb import minute_span

    by_entry = {t.entry_minute: t for t in trades}
    realised, low, open_trade = 0, 0, None
    for minute in minute_span(min(day.bars), day.exit_minute):
        if open_trade is None and minute in by_entry:
            open_trade = by_entry[minute]
        if open_trade is None:
            continue
        t, bar = open_trade, day.bars.get(minute)
        if minute == t.exit_minute:
            worst_price = t.exit_ticks
        elif bar is None:
            continue
        else:
            worst_price = bar[2] if t.side > 0 else bar[1]
        low = min(low, realised + t.side * (worst_price - t.entry_ticks) * tick)
        if minute == t.exit_minute:
            realised += t.gross_cents
            open_trade = None
    return min(low, realised)


def test_fast_day_path_matches_slow_minute_replay_on_random_days():
    import random

    from futures_day_builder import random_day

    from quant_brain.futures.orb import TICK_CENTS

    rng = random.Random(5)
    checked = 0
    for _ in range(3_000):
        day = random_day(rng)
        r = simulate_day(day)
        if r.status != "traded":
            continue
        tick = TICK_CENTS[day.root]
        assert paths.day_path(day.bars, r.trades, tick)[0] == _slow_day_low(day, r.trades, tick)
        checked += 1
    assert checked > 1_000


def test_day_records_low_matches_day_path_and_keep_time_order():
    bars = {
        **LONG,
        "08:52": (112, 115, 112, 114),
        "08:53": (114, 114, 108, 109),
        "08:54": (109, 118, 109, 117),
        "15:07": (117, 117, 117, 117),
    }
    d = make_day(bars)
    r = simulate_day(d)
    recs = paths.day_records(d.bars, r.trades, TICK)
    low, _ = paths.day_path(d.bars, r.trades, TICK)
    assert min(lo for lo, _ in recs) == low
    run_lo = run_hi = 0
    for lo, hi in recs:  # every record sets a new day low or a new day high
        assert lo <= hi and (lo < run_lo or hi > run_hi)
        run_lo, run_hi = min(run_lo, lo), max(run_hi, hi)
    assert len(recs) >= 2  # the 08:53 dip comes after the 08:52 high, then a new high

"""Synthetic checks of the frozen SC-FUT-0001 inference (no market data)."""

from __future__ import annotations

import numpy as np
import pytest

from quant_brain.futures.inference import (
    DayRecord,
    paired_test,
    politis_white_block_length,
    power_check,
    stationary_indices,
    verdict,
)

N_DAYS = 1_150
FAST = 999  # resamples for tests; the frozen run uses 9,999


def records(orb_mean: float, control_mean: float = 0.0, *, sd: float = 10_000, seed: int = 0, **kw):
    rng = np.random.default_rng(seed)
    orb = rng.normal(orb_mean, sd, N_DAYS).round().astype(int)
    control = rng.normal(control_mean, sd / 4, N_DAYS)
    return [
        DayRecord(int(o), int(o), float(c), float(c), "traded", trades=1, **kw)
        for o, c in zip(orb, control, strict=True)
    ]


def test_indices_are_seeded_and_mostly_contiguous():
    a = stationary_indices(50, 20, mean_block=5, seed=1)
    assert (a == stationary_indices(50, 20, mean_block=5, seed=1)).all()
    steps = (np.diff(a, axis=1) % 50 == 1).mean()
    assert 0.75 < steps < 0.85  # continuation probability 1 - 1/5


def test_null_does_not_pass():
    assert verdict(records(0.0), replicates=FAST).outcome == "not_demonstrated"


def test_planted_25_dollar_edge_passes():
    v = verdict(records(2_500.0), replicates=FAST)
    assert v.outcome == "pass_to_execution_calibration" and v.p_value < 0.01


def test_significant_but_below_floor_is_not_demonstrated():
    v = verdict(records(1_000.0, sd=3_000), replicates=FAST)
    assert v.p_value < 0.05 and v.outcome == "not_demonstrated"
    assert "floor" in v.reasons[-1]


def test_missing_minute_alarm_makes_pass_inconclusive():
    recs = records(2_500.0)
    recs[:20] = [
        DayRecord(r.orb_cents, r.orb_cents, r.control_cents, r.control_cents, "traded", 1, 1)
        for r in recs[:20]
    ]
    v = verdict(recs, replicates=FAST)
    assert v.outcome == "inconclusive" and v.missing_session_share > 0.01


def test_stress_flip_makes_inconclusive():
    recs = [
        DayRecord(r.orb_cents, r.orb_cents - 2_500, r.control_cents, r.control_cents, "traded", 1)
        for r in records(2_500.0)
    ]
    v = verdict(recs, replicates=FAST)
    assert v.outcome == "inconclusive" and v.stress_outcome == "not_demonstrated"


def test_non_evaluable_days_are_excluded_and_counted():
    recs = records(2_500.0)
    recs[0] = DayRecord(999_999, 999_999, 0.0, 0.0, "non_evaluable", 1)
    v = verdict(recs, replicates=FAST)
    assert v.non_evaluable_days == 1 and v.evaluable_days == N_DAYS - 1


def test_zero_trades_is_not_estimable():
    recs = [DayRecord(0, 0, 0.0, 0.0, "no_trade") for _ in range(100)]
    assert verdict(recs, replicates=FAST).outcome == "inconclusive"


def test_ambiguity_alarm_requests_review():
    recs = [
        DayRecord(r.orb_cents, r.orb_cents, r.control_cents, r.control_cents, "traded", 1, 0, 1)
        for r in records(0.0)
    ]
    assert verdict(recs, replicates=FAST).review_required


def test_p_value_formula_bounds():
    test = paired_test([1.0, -1.0] * 50, [0.0] * 100, replicates=FAST)
    assert 1 / (FAST + 1) <= test["p_value"] <= 1


def test_block_length_grows_with_dependence():
    rng = np.random.default_rng(3)
    iid = rng.normal(size=2_000)
    ar = np.zeros(2_000)
    for i in range(1, 2_000):
        ar[i] = 0.7 * ar[i - 1] + rng.normal()
    assert politis_white_block_length(iid) < 3 < politis_white_block_length(ar)


def test_power_is_high_at_20_with_100_dollar_daily_sd():
    orb = np.random.default_rng(4).normal(0, 10_000, N_DAYS)
    power = power_check(orb, np.zeros(N_DAYS), replicates=FAST)
    assert power["paired_power"] > 0.8 and power["joint_power"] == pytest.approx(
        min(power["paired_power"], power["absolute_power"]), abs=0.1
    )


def test_dsr_variance_uses_zero_controls_on_no_trade_days():
    from quant_brain.futures.inference import dsr_diagnostic

    rng = np.random.default_rng(5)
    recs = [
        DayRecord(
            int(rng.normal(0, 1000)),
            0,
            0.0,
            0.0,
            "traded",
            1,
            control_draw_cents=tuple(rng.normal(0, 1000, 500).astype(int)),
        )
        for _ in range(50)
    ]
    recs.append(DayRecord(0, 0, 0.0, 0.0, "no_trade"))
    dsr = dsr_diagnostic(recs)
    assert dsr["N=25"]["variance"] > 0 and dsr["N=25"]["sr_star"] > dsr["N=1"]["sr_star"]

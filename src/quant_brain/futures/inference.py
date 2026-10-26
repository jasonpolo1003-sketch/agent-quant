"""SC-FUT-0001 frozen inference: paired stationary bootstrap, floor, alarms, verdict.

Implements `inference`, `ambiguity` and the missing-minute alarm of the frozen
spec. Inputs are per-day records in integer cents; non-evaluable days are
counted and excluded, never imputed.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np

from quant_brain.backtest.stats import deflated_sharpe_n, sharpe_per_period
from quant_brain.futures.controls import ControlResult
from quant_brain.futures.orb import DayResult

BOOTSTRAP_DRAWS = 9_999
BOOTSTRAP_SEED = 20261027
MEAN_BLOCK = 5
ALPHA = 0.05
FLOOR_CENTS = 1_500
POWER_EFFECT_CENTS = 2_000
POWER_TARGET = 0.80
MISSING_ALARM_SHARE = 0.01
AMBIGUITY_ALARM_SHARE = 0.10
DSR_TRIALS = (1, 25)
EVALUABLE = {"traded", "no_trade", "void_range"}


@dataclass(frozen=True)
class DayRecord:
    orb_cents: int
    orb_stress_cents: int
    control_cents: float
    control_stress_cents: float
    status: str
    trades: int = 0
    gap_trades: int = 0
    entry_bar_stops: int = 0
    control_draw_cents: tuple[int, ...] = ()


def day_record(result: DayResult, control: ControlResult) -> DayRecord:
    evaluable = result.status in EVALUABLE and (control.k == 0 or control.evaluable_draws > 0)
    return DayRecord(
        orb_cents=result.net_cents,
        orb_stress_cents=result.stress_net_cents,
        control_cents=control.mean_cents,
        control_stress_cents=control.stress_mean_cents,
        status=result.status if evaluable else "non_evaluable",
        trades=len(result.trades),
        gap_trades=sum(t.gap_affected for t in result.trades),
        entry_bar_stops=sum(t.entry_bar_stop for t in result.trades),
        control_draw_cents=tuple(d.net_cents for d in control.draws),
    )


def stationary_indices(n: int, replicates: int, *, mean_block: int, seed: int) -> np.ndarray:
    """Politis-Romano circular stationary bootstrap index matrix (replicates x n)."""
    rng = np.random.Generator(np.random.PCG64(seed))
    starts = rng.integers(0, n, size=(replicates, n))
    restart = rng.random((replicates, n)) < 1 / mean_block
    restart[:, 0] = True
    index = np.empty((replicates, n), dtype=np.int64)
    index[:, 0] = starts[:, 0]
    for j in range(1, n):
        index[:, j] = np.where(restart[:, j], starts[:, j], (index[:, j - 1] + 1) % n)
    return index


def paired_test(
    orb: Sequence[float],
    control: Sequence[float],
    *,
    replicates: int = BOOTSTRAP_DRAWS,
    seed: int = BOOTSTRAP_SEED,
    mean_block: int = MEAN_BLOCK,
) -> dict[str, float]:
    """One-sided H1: mean(orb - control) > 0, resampling null-centred differences."""
    d = np.asarray(orb, dtype=float) - np.asarray(control, dtype=float)
    if len(d) < 2 or not np.all(np.isfinite(d)):
        raise ValueError("need >= 2 finite paired days")
    observed = float(d.mean())
    index = stationary_indices(len(d), replicates, mean_block=mean_block, seed=seed)
    means = (d - observed)[index].mean(axis=1)
    exceed = int(np.sum(means >= observed - 1e-9))
    return {"observed_cents": observed, "p_value": (exceed + 1) / (replicates + 1)}


def politis_white_block_length(x: Sequence[float]) -> float:
    """Stationary-bootstrap optimal mean block (Politis-White 2004; Patton et al. 2009)."""
    eps = np.asarray(x, dtype=float)
    eps = eps - eps.mean()
    n = len(eps)
    kn = max(5, int(math.sqrt(math.log10(n))))
    m_max = math.ceil(math.sqrt(n)) + kn
    b_max = math.ceil(min(3 * math.sqrt(n), n / 3))
    critical = 2 * math.sqrt(math.log10(n) / n)
    acv = np.array([eps[k:] @ eps[: n - k] / n for k in range(m_max + 1)])
    if acv[0] == 0:
        return 1.0
    acf = np.abs(acv / acv[0])
    m_hat = None
    for k in range(1, m_max - kn + 2):
        if np.all(acf[k : k + kn] < critical):
            m_hat = k - 1
            break
    m = min(2 * max(m_hat, 1), m_max) if m_hat is not None else m_max
    g = 0.0
    long_run = acv[0]
    for k in range(1, m + 1):
        weight = 1.0 if k / m <= 0.5 else 2 * (1 - k / m)
        g += 2 * weight * k * acv[k]
        long_run += 2 * weight * acv[k]
    if g == 0 or long_run <= 0:
        return 1.0
    d_sb = 2 * long_run**2
    return float(min(max(((2 * g**2) / d_sb) ** (1 / 3) * n ** (1 / 3), 1.0), b_max))


def power_check(
    orb: Sequence[float],
    control: Sequence[float],
    *,
    effect: float = POWER_EFFECT_CENTS,
    replicates: int = BOOTSTRAP_DRAWS,
    seed: int = BOOTSTRAP_SEED + 1,
) -> dict[str, float]:
    """Power at a true +$20/day using the observed variance and dependence.

    The paired and absolute series are centred, shifted to the effect and resampled
    with common day indices; the paired critical value is the null 95th percentile.
    """
    a = np.asarray(orb, dtype=float)
    d = a - np.asarray(control, dtype=float)
    index = stationary_indices(len(d), replicates, mean_block=MEAN_BLOCK, seed=seed)
    null_means = (d - d.mean())[index].mean(axis=1)
    critical = float(np.quantile(null_means, 1 - ALPHA))
    paired = null_means + effect > critical
    absolute = (a - a.mean())[index].mean(axis=1) + effect >= FLOOR_CENTS
    return {
        "paired_power": float(paired.mean()),
        "absolute_power": float(absolute.mean()),
        "joint_power": float((paired & absolute).mean()),
        "paired_se_cents": float(null_means.std(ddof=1)),
    }


def dsr_diagnostic(records: Sequence[DayRecord]) -> dict[str, dict]:
    orb = [r.orb_cents for r in records]
    draws = np.array([r.control_draw_cents for r in records if r.control_draw_cents])
    variance = 0.0
    if draws.size and draws.shape[0] == len(records):
        variance = float(np.var([sharpe_per_period(col) for col in draws.T], ddof=1))
    return {f"N={n}": deflated_sharpe_n(orb, n, variance) for n in DSR_TRIALS}


@dataclass(frozen=True)
class Verdict:
    outcome: str  # pass_to_execution_calibration | not_demonstrated | inconclusive
    reasons: list[str]
    evaluable_days: int
    non_evaluable_days: int
    trades: int
    observed_paired_cents: float | None
    absolute_mean_cents: float | None
    p_value: float | None
    stress_outcome: str | None
    missing_session_share: float
    missing_trade_share: float | None
    ambiguity_share: float | None
    review_required: bool
    extras: dict = field(default_factory=dict)


def _decide(orb: Sequence[float], control: Sequence[float], replicates: int) -> tuple[bool, dict]:
    test = paired_test(orb, control, replicates=replicates)
    absolute = float(np.mean(orb))
    passed = test["p_value"] < ALPHA and absolute >= FLOOR_CENTS
    return passed, {**test, "absolute_mean_cents": absolute}


def verdict(records: Sequence[DayRecord], *, replicates: int = BOOTSTRAP_DRAWS) -> Verdict:
    good = [r for r in records if r.status in EVALUABLE]
    bad = len(records) - len(good)
    trades = sum(r.trades for r in good)
    affected_sessions = sum(r.gap_trades > 0 for r in good) + bad
    missing_session_share = affected_sessions / len(records) if records else 0.0
    missing_trade_share = sum(r.gap_trades for r in good) / trades if trades else None
    ambiguity = sum(r.entry_bar_stops for r in good) / trades if trades else None
    reasons: list[str] = []

    def result(outcome, **kw) -> Verdict:
        return Verdict(
            outcome=outcome,
            reasons=reasons,
            evaluable_days=len(good),
            non_evaluable_days=bad,
            trades=trades,
            missing_session_share=missing_session_share,
            missing_trade_share=missing_trade_share,
            ambiguity_share=ambiguity,
            review_required=ambiguity is not None and ambiguity > AMBIGUITY_ALARM_SHARE,
            **{
                "observed_paired_cents": None,
                "absolute_mean_cents": None,
                "p_value": None,
                "stress_outcome": None,
                **kw,
            },
        )

    if trades == 0 or len(good) < 2:
        reasons.append("not_estimable: no executed trades or too few evaluable days")
        return result("inconclusive")
    passed, stats = _decide(
        [r.orb_cents for r in good], [r.control_cents for r in good], replicates
    )
    stress_passed, _ = _decide(
        [r.orb_stress_cents for r in good], [r.control_stress_cents for r in good], replicates
    )
    outcome = "pass_to_execution_calibration" if passed else "not_demonstrated"
    stress_outcome = "pass_to_execution_calibration" if stress_passed else "not_demonstrated"
    if missing_session_share > MISSING_ALARM_SHARE or (
        missing_trade_share is not None and missing_trade_share > MISSING_ALARM_SHARE
    ):
        reasons.append("missing-minute alarm above 1%")
        outcome = "inconclusive"
    if passed != stress_passed:
        reasons.append("verdict flips under the missing-minute stress bound")
        outcome = "inconclusive"
    if outcome == "not_demonstrated":
        reasons.append(
            "p >= 0.05" if stats["p_value"] >= ALPHA else "absolute mean below $15/day floor"
        )
    return result(
        outcome,
        observed_paired_cents=stats["observed_cents"],
        absolute_mean_cents=stats["absolute_mean_cents"],
        p_value=stats["p_value"],
        stress_outcome=stress_outcome,
    )

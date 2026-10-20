"""Statistics and the random-entry benchmark, exactly as SC-0002 pins them."""

import math
from itertools import pairwise
from statistics import NormalDist

import numpy as np
import pandas as pd
import pytest
from scipy import stats as sps

from quant_brain.backtest import benchmarks as bm
from quant_brain.backtest import stats as st


def test_sharpe_is_mean_over_sample_std_and_annualises_by_root_252():
    r = pd.Series([0.01, -0.01, 0.02, 0.0])

    per = st.sharpe_per_period(r)

    assert per == pytest.approx(r.mean() / r.std(ddof=1))
    assert st.annualised_sharpe(r) == pytest.approx(per * math.sqrt(252))
    assert st.sharpe_per_period(pd.Series([0.0, 0.0, 0.0])) == 0.0


def test_max_drawdown_is_the_worst_peak_to_trough():
    assert st.max_drawdown(pd.Series([1.0, 1.2, 0.9, 1.3, 1.1])) == pytest.approx(0.9 / 1.2 - 1)


def test_cagr_uses_252_trading_days_per_year():
    equity = pd.Series([1.0] * 251 + [1.1])
    assert st.cagr(equity) == pytest.approx(1.1 ** (252 / 252) - 1)


def _dsr_by_hand(returns, trial_srs):
    x = np.asarray(returns, dtype=float)
    sr = x.mean() / x.std(ddof=1)
    variance = np.var(trial_srs, ddof=1)
    g = 0.5772156649
    n = len(trial_srs)
    nd = NormalDist()
    sr_star = 0.0 if variance == 0 else math.sqrt(variance) * (
        (1 - g) * nd.inv_cdf(1 - 1 / n) + g * nd.inv_cdf(1 - 1 / (n * math.e)))
    skew = sps.skew(x, bias=True)
    kurt = sps.kurtosis(x, bias=True, fisher=False)
    t = len(x)
    return nd.cdf((sr - sr_star) * math.sqrt(t - 1) / math.sqrt(1 - skew * sr + (kurt - 1) / 4 * sr**2))


def test_deflated_sharpe_matches_an_independent_computation_of_the_card_formula():
    rng = np.random.default_rng(7)
    returns = rng.normal(0.0004, 0.01, 2700)
    trials = [0.04, 0.02, 0.015]

    result = st.deflated_sharpe(returns, trials)

    assert result["dsr"] == pytest.approx(_dsr_by_hand(returns, trials), abs=1e-12)
    assert result["n_trials"] == 3 and result["t"] == 2700


def test_deflated_sharpe_with_zero_cross_trial_variance_uses_a_zero_benchmark():
    rng = np.random.default_rng(8)
    returns = rng.normal(0.0002, 0.01, 1000)

    result = st.deflated_sharpe(returns, [0.03, 0.03, 0.03])

    assert result["sr_star"] == 0.0
    assert result["dsr"] == pytest.approx(_dsr_by_hand(returns, [0.03, 0.03, 0.03]), abs=1e-12)


def test_percentile_counts_strictly_below_only():
    assert st.percentile_strictly_below([0.1, 0.2, 0.2, 0.3], 0.2) == 25.0
    assert st.percentile_strictly_below([], 0.2) is None


# --- random entry ---------------------------------------------------------------------


OPENS = np.linspace(100, 130, 60)
ELIGIBLE = np.ones(60, dtype=bool)  # filter true everywhere


def runs(**overrides):
    kwargs = dict(opens=OPENS, filter_ok=ELIGIBLE, holding_times=[3, 5, 2], cost=0.0005,
                  p0=5, p1=50, runs=40, seed_start=20260929)
    kwargs.update(overrides)
    return bm.random_entry(**kwargs)


def test_random_entry_is_reproducible_from_its_seeds():
    first, second = runs(), runs()

    assert first.average_returns == second.average_returns
    assert first.completed == 40 and first.discarded == 0
    assert runs(seed_start=1).average_returns != first.average_returns


def test_random_trades_fit_the_period_never_overlap_and_skip_the_first_day():
    result = runs(record_trades=True)

    for trades in result.trades:
        assert sorted(h for _, _, h in trades) == [2, 3, 5]
        spans = sorted((d, d + h) for d, _, h in trades)
        for (d, e), (d2, _) in pairwise(spans):
            assert d2 >= e + 1  # entry at least one day after the previous exit
        for d, ret, h in trades:
            assert 5 < d and d + h <= 50
            assert ret == pytest.approx(0.9995 * OPENS[d + h] / OPENS[d] * 0.9995 - 1)


def test_random_entries_respect_the_filter_at_the_prior_close():
    filter_ok = np.zeros(60, dtype=bool)
    filter_ok[[10, 20, 30]] = True  # fills may only happen on 11, 21, 31

    result = runs(filter_ok=filter_ok, holding_times=[2], record_trades=True)

    assert {d for trades in result.trades for d, _, _ in trades} <= {11, 21, 31}


def test_a_run_that_cannot_place_every_trade_is_discarded_and_counted():
    result = runs(holding_times=[40, 40], retry_limit=50)

    assert result.completed == 0 and result.discarded == 40
    assert result.average_returns == []


def test_max_drawdown_counts_a_first_day_loss_from_the_starting_equity():
    assert st.max_drawdown(pd.Series([0.9, 0.95, 1.0])) == pytest.approx(-0.1)

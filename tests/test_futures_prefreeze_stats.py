"""Synthetic-only pre-freeze inference checks; no licensed market inputs."""

from itertools import pairwise

from quant_brain.futures.prefreeze_stats import paired_one_sided_bootstrap, stationary_indices


def test_stationary_resampling_is_seeded_and_keeps_requested_length():
    first = stationary_indices(20, 100, mean_block=5, seed=71)
    assert first == stationary_indices(20, 100, mean_block=5, seed=71)
    assert len(first) == 100
    assert all(0 <= i < 20 for i in first)
    assert any(b == (a + 1) % 20 for a, b in pairwise(first))


def test_known_null_does_not_reject():
    # Equal strategy and controls: centered paired difference is exactly zero.
    result = paired_one_sided_bootstrap([0.0] * 100, [0.0] * 100, seed=8, replicates=999)
    assert result["observed_difference"] == 0.0
    assert result["p_value"] == 1.0
    assert result["reject_at_005"] is False


def test_planted_fifteen_dollar_daily_edge_is_detected():
    # Synthetic test of the *paired contrast*, not a claim about MNQ.
    controls = [(-20.0 if i % 2 else 20.0) for i in range(100)]
    strategy = [c + 15.0 for c in controls]
    result = paired_one_sided_bootstrap(strategy, controls, seed=9, replicates=999)
    assert result["observed_difference"] == 15.0
    assert result["p_value"] < 0.05
    assert result["reject_at_005"] is True


def test_invalid_pairs_fail_closed():
    import pytest

    with pytest.raises(ValueError):
        paired_one_sided_bootstrap([1.0], [], seed=1, replicates=20)
    with pytest.raises(ValueError):
        paired_one_sided_bootstrap([float("nan")], [0.0], seed=1, replicates=20)

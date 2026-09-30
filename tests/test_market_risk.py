"""Risk Center math, checked against hand-worked numbers."""

import pandas as pd
import pytest

from quant_brain.market import risk


def test_position_size_risks_the_chosen_percent():
    out = risk.position_size(10_000, 1, entry=50, stop=48)
    assert out["shares"] == 50 and out["dollar_risk"] == 100
    assert out["position_value"] == 2_500 and out["side"] == "long"
    assert not out["capped_by_cash"] and "50 shares" in out["explain"]


def test_position_size_is_capped_by_cash_and_explains_it():
    out = risk.position_size(1_000, 5, entry=100, stop=99.9)
    assert out["shares"] == 10 and out["capped_by_cash"]
    assert out["dollar_risk"] == pytest.approx(1.0)
    assert "cannot buy more" in out["explain"]


@pytest.mark.parametrize("args", [(0, 1, 10, 9), (100, 0, 10, 9), (100, 1, 10, 10), (100, 101, 10, 9)])
def test_position_size_rejects_nonsense(args):
    with pytest.raises(ValueError):
        risk.position_size(*args)


def test_losing_half_needs_doubling():
    assert risk.recovery_needed(50) == pytest.approx(100)
    assert risk.recovery_needed(0) == 0
    assert {r["loss_pct"]: r["gain_needed_pct"] for r in risk.drawdown_table()}[90] == 900.0


def test_expectancy_and_kelly():
    assert risk.expectancy(0.5, 2) == pytest.approx(0.5)
    k = risk.kelly_fraction(0.5, 2)
    assert k["full"] == pytest.approx(0.25) and k["half"] == pytest.approx(0.125)
    assert risk.kelly_fraction(0.3, 1)["full"] == 0


def test_simulation_is_seeded_and_bigger_bets_ruin_more_often():
    a = risk.simulate_paths(0.5, 1.5, 2, trades=100, paths=500)
    b = risk.simulate_paths(0.5, 1.5, 2, trades=100, paths=500)
    big = risk.simulate_paths(0.5, 1.5, 20, trades=100, paths=500)
    assert a["probability_of_ruin"] == b["probability_of_ruin"]
    assert big["probability_of_ruin"] > a["probability_of_ruin"]
    assert len(a["sample_paths"]) == 20 and len(a["sample_paths"][0]) == 101
    assert a["sample_paths"][0][0] == 1.0


def test_a_sure_loser_is_always_ruined():
    out = risk.simulate_paths(0.0, 1.0, 10, trades=10, paths=50)
    assert out["probability_of_ruin"] == 1.0
    assert out["final_equity_percentiles"][50] == pytest.approx(0.9 ** 10)


def test_portfolio_heat_adds_every_stop():
    out = risk.portfolio_heat(10_000, [{"shares": 10, "entry": 50, "stop": 45},
                                      {"shares": 5, "entry": 100, "stop": 90}])
    assert out["dollar_risk"] == 100 and out["heat_pct"] == pytest.approx(1.0)


def test_correlation_of_identical_and_opposite_series():
    up = pd.Series([1, 2, 1.5, 3, 2.5], index=range(5))
    out = risk.correlation_matrix({"A": up, "B": up * 2, "C": 10 - up})
    m = dict(zip(out["symbols"], out["matrix"]))
    assert m["A"][1] == pytest.approx(1.0) and m["A"][2] < 0
    assert out["days"] == 4

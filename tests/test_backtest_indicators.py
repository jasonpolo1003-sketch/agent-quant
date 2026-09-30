"""Indicators exactly as SC-0002's implementation block defines them.

Expected values are worked by hand, not produced by the code under test.
Closes 10, 11, 10, 12, 12, 11 give changes +1, -1, +2, 0, -1.
"""

import math

import pandas as pd
import pytest

from quant_brain.backtest import indicators as ind

CLOSES = pd.Series([10.0, 11.0, 10.0, 12.0, 12.0, 11.0])


def test_wilder_rsi_seeds_with_a_simple_mean_then_smooths():
    rsi = ind.rsi_wilder(CLOSES, 2)

    assert rsi.iloc[:2].isna().all()
    # idx2: ag=(1+0)/2=0.5, al=(0+1)/2=0.5 -> 50
    # idx3: ag=(0.5+2)/2=1.25, al=(0.5+0)/2=0.25 -> RS 5 -> 83.333
    # idx4: ag=0.625, al=0.125 -> RS 5 -> 83.333
    # idx5: ag=0.3125, al=(0.125+1)/2=0.5625 -> RS 0.5556 -> 35.714
    expected = [50.0, 100 - 100 / 6, 100 - 100 / 6, 100 - 100 / (1 + 0.3125 / 0.5625)]
    assert rsi.iloc[2:].tolist() == pytest.approx(expected, abs=1e-12)


def test_cutler_rsi_uses_simple_means_of_the_last_n_changes():
    rsi = ind.rsi_cutler(CLOSES, 2)

    assert rsi.iloc[:2].isna().all()
    # idx2: g(1,0)=.5 l(0,1)=.5 -> 50; idx3: g(0,2)=1 l(1,0)=.5 -> 66.667
    # idx4: g(2,0)=1 l(0,0)=0 -> 100; idx5: g(0,0)=0 l(0,1)=.5 -> 0
    assert rsi.iloc[2:].tolist() == pytest.approx([50.0, 100 - 100 / 3, 100.0, 0.0], abs=1e-12)


@pytest.mark.parametrize("fn", [ind.rsi_wilder, ind.rsi_cutler])
def test_rsi_is_100_when_there_are_no_losses(fn):
    assert fn(pd.Series([1.0, 2.0, 3.0, 4.0]), 2).iloc[2:].tolist() == [100.0, 100.0]


def test_sma_includes_the_current_bar_and_needs_a_full_window():
    sma = ind.sma(CLOSES, 3)

    assert sma.iloc[:2].isna().all()
    assert sma.iloc[2] == pytest.approx((10 + 11 + 10) / 3)
    assert sma.iloc[5] == pytest.approx((12 + 12 + 11) / 3)


def test_wilder_rsi_matches_an_independent_recursion_on_a_long_series():
    closes = pd.Series([100 + 5 * math.sin(i / 3) + (i % 7) * 0.3 for i in range(300)])
    rsi = ind.rsi_wilder(closes, 14)

    changes = closes.diff().tolist()
    gains = [max(c, 0) for c in changes[1:]]
    losses = [max(-c, 0) for c in changes[1:]]
    ag, al = sum(gains[:14]) / 14, sum(losses[:14]) / 14
    values = [100 - 100 / (1 + ag / al)]
    for g, lo in zip(gains[14:], losses[14:], strict=True):
        ag, al = (ag * 13 + g) / 14, (al * 13 + lo) / 14
        values.append(100 - 100 / (1 + ag / al))
    assert rsi.iloc[14:].tolist() == pytest.approx(values, abs=1e-9)

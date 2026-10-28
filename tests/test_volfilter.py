"""SC-FUT-0006 volatility filter: hand-worked cases."""

from __future__ import annotations

import math
from datetime import date, timedelta

import pytest

from quant_brain.workbench.volfilter import front_returns, high_vol_days, vol_series

MON = date(2024, 1, 1)


def test_returns_follow_the_highest_volume_contract_without_a_roll_jump():
    rows = [
        (MON, "NQH4", 100.0, 900),
        (MON, "NQM4", 102.0, 10),
        (MON + timedelta(1), "NQH4", 101.0, 100),
        (MON + timedelta(1), "NQM4", 104.04, 800),  # roll: NQM4 now front
    ]
    out = front_returns(rows)
    # day 2 uses NQM4 against NQM4's own previous close (102), not NQH4's 100
    assert out == [(MON + timedelta(1), pytest.approx(math.log(104.04 / 102.0)))]


def test_weekend_bars_are_dropped():
    sunday = date(2024, 1, 7)
    rows = [
        (sunday - timedelta(2), "NQH4", 100.0, 5),
        (sunday, "NQH4", 150.0, 5),
        (sunday + timedelta(1), "NQH4", 101.0, 5),
    ]
    assert front_returns(rows) == [(sunday + timedelta(1), pytest.approx(math.log(1.01)))]


def test_vol_is_the_sample_std_of_the_window():
    rets = [(MON + timedelta(i), r) for i, r in enumerate([0.01, -0.01, 0.03])]
    out = vol_series(rets, window=3)
    assert out == [(MON + timedelta(2), pytest.approx(0.02))]


def test_filter_uses_only_bars_before_the_trade_date():
    vols = [(MON + timedelta(i), v) for i, v in enumerate([1.0, 2.0, 3.0, 10.0])]
    # trade on day 3: last bar strictly before is day 2 (vol 3) vs median(1, 2) = 1.5
    row = high_vol_days([MON + timedelta(3)], vols, lookback=2)[0]
    assert row == (MON + timedelta(3), MON + timedelta(2), 3.0, 1.5, True)


def test_not_high_when_equal_to_median_or_without_history():
    vols = [(MON + timedelta(i), v) for i, v in enumerate([2.0, 2.0, 2.0])]
    assert high_vol_days([MON + timedelta(3)], vols, lookback=2)[0][4] is False
    assert high_vol_days([MON + timedelta(1)], vols, lookback=2)[0][4] is False

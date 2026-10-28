"""Plan A1: several sleeves in one prop account. Hand-worked fixtures (written before use)."""

from __future__ import annotations

import dataclasses

import numpy as np
from test_prop_simulator import _table

from quant_brain.config import BRAIN_DIR
from quant_brain.prop import funded, portfolio
from quant_brain.prop.account import Rules, attempt
from quant_brain.prop.funded import XfaRules
from quant_brain.prop.portfolio import Sleeve
from quant_brain.workbench.analysis import COSTS
from quant_brain.workbench.engine import DayTable

PROP = BRAIN_DIR / "_system" / "prop"


def _days(dates, gross, low, ctrl=None, trades=1):
    """A tiny table in cents per contract; control draws default to the same day flipped."""
    n = len(dates)
    gross, low = np.array(gross), np.array(low)
    ctrl = np.array(ctrl) if ctrl is not None else np.stack([gross, -gross], axis=1)
    return DayTable(
        dates=np.array(dates),
        status=np.array(["traded"] * n),
        atr=np.zeros(n, int),
        orb_side=np.ones(n, int),
        orb_gross=gross,
        orb_low=low,
        orb_stress_gross=gross,
        orb_trades=np.full(n, trades),
        entry_bar_stops=np.zeros(n, int),
        gap_trades=np.zeros(n, int),
        ctrl_gross=ctrl,
        ctrl_stress_gross=ctrl,
        ctrl_trades=np.full(ctrl.shape, trades),
        ctrl_ok=np.ones(n, bool),
        ctrl_low=np.minimum(ctrl, 0),
    )


COST = COSTS["L3"]["MNQ"] / 100  # dollars per MNQ round trip


def test_closes_and_lows_add_up_by_date_and_missing_dates_are_zero():
    a = _days(["2020-01-02", "2020-01-03"], [10_000, -5_000], [-2_000, -6_000])
    b = _days(["2020-01-03", "2020-01-06"], [3_000, 4_000], [-1_000, 0])
    book = portfolio.combine([Sleeve("a", a, "MNQ", 1), Sleeve("b", b, "MNQ", 2)])
    assert book.dates.tolist() == ["2020-01-02", "2020-01-03", "2020-01-06"]
    # Jan 2: a only. Jan 3: a + 2 x b. Jan 6: 2 x b.
    np.testing.assert_allclose(book.close, [100 - COST, -50 - COST + 60 - 2 * COST, 80 - 2 * COST])
    np.testing.assert_allclose(book.low[1], -60 - COST + 2 * (-10 - COST))  # lows summed
    assert book.slip == 3 * 2 * 0.5  # 3 MNQ x 2 ticks x $0.50


def test_dll_triggers_on_the_sum_even_when_no_sleeve_hits_it_alone():
    # Each sleeve's low is -$600, under the $1,000 limit; together -$1,200 hits it.
    a = _days(["2020-01-02"], [-30_000], [-60_000], trades=0)
    b = _days(["2020-01-02"], [-30_000], [-60_000], trades=0)
    book = portfolio.combine([Sleeve("a", a, "MNQ", 1), Sleeve("b", b, "MNQ", 1)])
    close, low = funded.apply_dll(book.close, book.low, 1_000, book.slip)
    assert close[0] == -(1_000 + book.slip) and low[0] <= close[0]
    alone = portfolio.combine([Sleeve("a", a, "MNQ", 1)])
    assert funded.apply_dll(alone.close, alone.low, 1_000, alone.slip)[0][0] == -300


def test_combine_pass_can_come_from_the_sum():
    rules = Rules.from_json(PROP / "topstep_50k.json")
    # $1,600/day from two sleeves of $800: the target ($3,000) is reached by day 2.
    dates = ["2020-01-02", "2020-01-03", "2020-01-06"]
    a = _days(dates, [80_000] * 3, [0] * 3, trades=0)
    alone = portfolio.combine([Sleeve("a", a, "MNQ", 1)])
    both = portfolio.combine([Sleeve("a", a, "MNQ", 1), Sleeve("b", a, "MNQ", 1)])
    assert attempt(both.close, both.low, rules, 3).passed
    assert attempt(both.close, both.low, rules, 3).days == 2
    assert not attempt(alone.close[:3], alone.low[:3], rules, 3).passed


def test_luck_uses_the_same_draw_column_for_every_sleeve():
    a = _days(["2020-01-02"], [1_000], [0], ctrl=[[1_000, -1_000]], trades=0)
    b = _days(["2020-01-02"], [2_000], [0], ctrl=[[2_000, -2_000]], trades=0)
    book = portfolio.combine([Sleeve("a", a, "MNQ", 1), Sleeve("b", b, "MNQ", 1)])
    np.testing.assert_allclose(book.c_close[0], [30, -30])


def test_gate_needs_all_three_checks():
    combine_rules, activation = funded.plan_rules(PROP / "topstep_50k.json", "standard")
    xr = XfaRules.from_json(PROP / "topstep_50k_xfa.json", "standard", dll=True, activation=activation)
    dates = [f"2020-{1 + i // 28:02d}-{1 + i % 28:02d}" for i in range(400)]
    strong = dataclasses.replace(_table(n=400, edge=20_000), dates=np.array(dates))
    book = portfolio.combine([Sleeve("s", strong, "MNQ", 1)])
    kw = dict(n_paths=200, outer=10, inner=80)
    r = portfolio.evaluate(book, combine_rules, xr, payout_range=(0.0, 1.0), **kw)
    assert r["gate"] == "pass", r["checks"]
    r = portfolio.evaluate(book, combine_rules, xr, payout_range=(0.0, 0.01), **kw)
    assert r["gate"] == "fail" and not r["checks"]["payout_chance_in_stated_range"]
    none = dataclasses.replace(_table(n=400, edge=0), dates=np.array(dates))
    r = portfolio.evaluate(
        portfolio.combine([Sleeve("n", none, "MNQ", 1)]),
        combine_rules,
        xr,
        payout_range=(0.0, 1.0),
        **kw,
    )
    assert r["gate"] == "fail"

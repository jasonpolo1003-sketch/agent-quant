"""Backtest workbench: plug-ins, cached runs, honesty counter, slices (synthetic + dev sample)."""

from __future__ import annotations

import dataclasses
import random
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pytest
from futures_day_builder import random_day

from quant_brain.futures import orb
from quant_brain.workbench import analysis, engine
from quant_brain.workbench.strategies import OpeningRangeBreakout, make


def synthetic_days(market: str, n: int = 30, seed: int = 0):
    rng = random.Random(seed)
    out = []
    for i in range(n):
        d = random_day(rng)
        out.append(
            dataclasses.replace(
                d,
                trade_date=date(2020, 1, 1) + timedelta(days=i),
                root=market,
                atr_tr_sum=rng.randint(100, 800),
            )
        )
    return out


def loader(market, start, end, roll_column):
    return synthetic_days(market)


def test_default_plugin_is_the_frozen_rule():
    for day in synthetic_days("MNQ", 200, seed=3):
        prepared = OpeningRangeBreakout().prepare(day)
        assert prepared.stop_ticks == orb.stop_from_sum(day.atr_tr_sum)
        assert OpeningRangeBreakout().simulate(prepared) == orb.simulate_day(prepared)


def test_settings_change_the_rule_and_are_validated():
    day = OpeningRangeBreakout().prepare(synthetic_days("MNQ", 1)[0])
    wide = OpeningRangeBreakout(stop_fraction="0.30").prepare(day)
    assert wide.stop_ticks > day.stop_ticks
    assert OpeningRangeBreakout(range_bars=30).first_fill == orb.add_minutes(orb.RANGE_START, 31)
    with pytest.raises(ValueError):
        make("orb", {"range_bars": 0})
    with pytest.raises(ValueError):
        make("nope")


def test_runs_are_cached_and_counted_once(tmp_path):
    first, rec1, cached1 = engine.run(tmp_path, make("orb"), "MNQ", "fixed", loader)
    again, rec2, cached2 = engine.run(tmp_path, make("orb"), "MNQ", "fixed", loader)
    assert (cached1, cached2) == (False, True) and rec1 == rec2
    assert np.array_equal(first.orb_gross, again.orb_gross)
    assert analysis.honesty(tmp_path, "orb")["trials"] == 1
    engine.run(tmp_path, make("orb", {"range_bars": 30}), "MNQ", "fixed", loader)
    bar = analysis.honesty(tmp_path, "orb")
    assert bar["trials"] == 2 and bar["alpha"] < 0.05


def test_refuses_exam_period_days(tmp_path):
    def leaky(market, start, end, roll_column):
        return [
            dataclasses.replace(d, trade_date=date(2025, 2, 3)) for d in synthetic_days(market, 2)
        ]

    with pytest.raises(RuntimeError, match="exam"):
        engine.run(tmp_path, make("orb"), "MNQ", "fixed", leaky)


def test_regimes_only_look_backwards(tmp_path):
    table, _, _ = engine.run(
        tmp_path, make("orb"), "MNQ", "fixed", lambda *a: synthetic_days("MNQ", 300, seed=9)
    )
    labels = analysis.regimes(table)
    changed = dataclasses.replace(table, atr=table.atr.copy())
    changed.atr[-1] = 10**9  # a future spike must not relabel the past
    assert (analysis.regimes(changed)[:-1] == labels[:-1]).all()
    assert set(labels[analysis.REGIME_LOOKBACK :]) <= {"calm", "normal", "volatile"}


def test_grid_slices_and_costs(tmp_path):
    table, record, _ = engine.run(tmp_path, make("orb"), "MNQ", "fixed", loader)
    result = analysis.summary(tmp_path, table, record, replicates=199)
    costs = result["grid"]["costs"]
    assert costs["L1"]["per_day"] >= costs["L4"]["per_day"]
    assert result["verdict"]["outcome"] in {
        "pass_to_execution_calibration",
        "not_demonstrated",
        "inconclusive",
    }
    assert set(result["grid"]["years"]) == {"2020"}


DEV = Path("C:/Users/jason/OneDrive/Desktop/Quant/data/databento/dev_2019-05-01_2024-12-31")
REPO = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(not DEV.exists(), reason="dev partition not on this machine")
def test_plugin_reproduces_sc_fut_0001_development_results_on_sample_days():
    import csv

    from quant_brain.futures import runner
    from quant_brain.futures.bars import load_days

    days = load_days(
        DEV / runner.DEV_BARS,
        REPO / runner.ROLL_CSV,
        REPO / runner.CALENDAR,
        root="MNQ",
        start=date(2022, 3, 1),
        end=date(2022, 3, 31),
    )
    table = engine.simulate(make("orb"), days)
    with (REPO / runner.REPORTS / "development" / "MNQ.development.daily.csv").open(
        encoding="utf-8"
    ) as handle:
        frozen = {r["trade_date"]: r for r in csv.DictReader(handle)}
    nets = table.orb_gross - 322 * table.orb_trades
    ctrl = (table.ctrl_gross - 322 * table.ctrl_trades).mean(axis=1)
    assert len(table.dates) >= 20
    for i, d in enumerate(table.dates):
        assert nets[i] == int(frozen[d]["orb_cents"]), d
        assert ctrl[i] == pytest.approx(float(frozen[d]["control_cents"]), abs=1e-9), d

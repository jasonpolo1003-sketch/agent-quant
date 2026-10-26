"""Control fixtures C1-C5 (brain/_system/futures/orb-fixtures.md)."""

from __future__ import annotations

import dataclasses
from datetime import date, time

from futures_day_builder import make_day

from quant_brain.futures.controls import daily_control
from quant_brain.futures.orb import minute_span


def test_c1_no_orb_trade_means_zero_control():
    result = daily_control(make_day(), 0)
    assert (result.mean_cents, result.draws) == (0.0, [])


def test_c2_flat_day_every_draw_pays_only_costs():
    result = daily_control(make_day(), 1)
    assert result.mean_cents == -322 and result.evaluable_draws == 500
    assert all(len(d.trades) == 1 for d in result.draws)
    fills = {d.trades[0].entry_minute for d in result.draws}
    assert min(fills) >= time(8, 46) and max(fills) <= time(14, 30) and len(fills) > 100
    sides = [d.trades[0].side for d in result.draws]
    assert 200 < sides.count(1) < 300


def test_c3_second_trade_not_taken_after_flatten():
    result = daily_control(make_day(), 2)
    assert result.mean_cents == -322
    assert result.not_taken == 500


def test_c4_deterministic_per_day_and_root():
    day = make_day({"09:00": (105, 120, 90, 110)})
    first, again = daily_control(day, 1), daily_control(day, 1)
    assert first.draws == again.draws
    other_day = dataclasses.replace(day, trade_date=date(2020, 1, 3))
    assert daily_control(other_day, 1).draws != first.draws
    other_root = dataclasses.replace(day, root="MES")
    fills = [d.trades[0].entry_minute for d in first.draws]
    assert [d.trades[0].entry_minute for d in daily_control(other_root, 1).draws] != fills


def test_c5_rejection_lands_on_only_available_minute():
    missing = tuple(
        m.strftime("%H:%M") for m in minute_span(time(8, 46), time(14, 30)) if m != time(10, 0)
    )
    result = daily_control(make_day(missing=missing), 1)
    assert {d.trades[0].entry_minute for d in result.draws} == {time(10, 0)}
    assert result.rejections > 0 and result.evaluable_draws == 500


def test_day_with_missing_flatten_is_not_paired_on_surviving_draws():
    from quant_brain.futures.inference import day_record
    from quant_brain.futures.orb import simulate_day

    # ORB is stopped on its entry bar (evaluable) but the 15:07 bar is missing, so
    # control draws that run to the flatten cannot be evaluated.
    day = make_day(
        {"08:50": (105, 112, 105, 111), "08:51": (111, 111, 106, 108)}, missing=("15:07",)
    )
    result = simulate_day(day)
    assert result.status == "traded"
    control = daily_control(day, len(result.trades))
    assert 0 < control.non_evaluable_draws < 500
    assert day_record(result, control).status == "non_evaluable"

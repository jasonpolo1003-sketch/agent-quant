"""Incremental SC-FUT-0005 engine (live/engine.py) vs the batch rule (workbench/noise.py).

Hand-worked days first: the noise-area fixtures (tests/test_noise_area_fixtures.py: 08:30 bar
(105, 110, 100, 105), previous close 105, sigma 2% -> bands 107.1 / 102.9) replayed bar by bar,
with the expected legs written out again here, then the event timing a live runner relies on,
then random synthetic days (gaps, missing flatten bars, early closes, odd volumes) where every
trade must equal NoiseArea().simulate's. Synthetic data only; the practice-data replay is
scripts/live_replay_check.py.
"""

from __future__ import annotations

import dataclasses
import random
from datetime import date, time, timedelta

import pytest
from futures_day_builder import make_day, random_day, t

from quant_brain.live.engine import (
    Bar,
    ModelFill,
    NoiseEngine,
    SessionContext,
    SigmaHistory,
    Signal,
    Void,
    bars_of,
    context_of,
    decide,
    replay,
)
from quant_brain.workbench.noise import NoiseArea

STRAT = NoiseArea()
CHECKS = [h * 60 + m for h in range(9, 15) for m in (0, 30)]
SIGMA = {c: 0.02 for c in CHECKS}
BREAKOUT = {"08:59": (105, 108, 105, 108)}


def day(bars=None, missing=(), prev_close=105, volumes=None, exit_minute="15:07"):
    d = make_day(bars, missing=missing, root="MNQ", exit_minute=exit_minute)
    vol = {m: 1 for m in d.bars} | {t(k): v for k, v in (volumes or {}).items()}
    return dataclasses.replace(d, prev_close=prev_close, volumes=vol, context={"sigma": SIGMA})


def legs(trades):
    return [(x.side, x.entry_minute, x.entry_ticks, x.exit_minute, x.exit_ticks) for x in trades]


def run(d, sigma=SIGMA):
    e = replay(d, sigma)
    batch = STRAT.simulate(dataclasses.replace(d, context={"sigma": sigma}))
    assert e.trades() == batch.trades and e.status == batch.status
    return e


# --- the noise-area fixtures, bar by bar --------------------------------------------------


def test_e1_long_on_breakout_held_to_the_close():
    e = run(day({**BREAKOUT, "10:10": (108, 120, 108, 120)}))
    assert legs(e.trades()) == [(1, t("09:00"), 108, t("15:00"), 120)]
    assert e.trades()[0].net_cents == 12 * 50 - 322


def test_e2_exit_back_inside_the_band():
    e = run(day({**BREAKOUT, "10:29": (108, 108, 106, 106)}))
    assert legs(e.trades()) == [(1, t("09:00"), 108, t("10:30"), 106)]


def test_e3_reverse_at_the_same_check():
    e = run(day({**BREAKOUT, "10:29": (108, 108, 102, 102)}))
    assert legs(e.trades()) == [
        (1, t("09:00"), 108, t("10:30"), 102),
        (-1, t("10:30"), 102, t("15:00"), 102),
    ]


def test_e4_gap_widens_band_and_no_sigma_no_action():
    assert run(day(BREAKOUT, prev_close=110)).legs == []
    assert run(day(BREAKOUT), sigma={}).legs == []


def test_e5_vwap_stop_and_same_side_reentry_next_check():
    bars = {**BREAKOUT, "09:05": (108, 115, 108, 115), "10:29": (115, 115, 112, 112)}
    heavy = {f"09:{m:02d}": 1_000 for m in range(5, 60)}
    e = run(day(bars, volumes=heavy))
    assert [x[1] for x in legs(e.trades())] == [
        t(h) for h in ("09:00", "11:00", "12:00", "13:00", "14:00")
    ]


def test_e6_missing_check_bar_voids_that_check():
    e = NoiseEngine(context_of(day(BREAKOUT, missing=("09:00",)), SIGMA))
    events = [ev for b in bars_of(day(BREAKOUT, missing=("09:00",))) for ev in e.on_bar(b)]
    assert any(isinstance(ev, Void) and ev.check == t("09:00") for ev in events)
    e.end_session()
    assert legs(e.trades())[0][1] == t("09:30")
    run(day(BREAKOUT, missing=("09:00",)))


def test_e7_early_close_and_missing_flatten_bar():
    assert legs(run(day(BREAKOUT, exit_minute="12:12")).trades()) == [
        (1, t("09:00"), 108, t("12:00"), 108)
    ]
    assert run(day({"11:59": (105, 108, 105, 108)}, exit_minute="12:12")).legs == []
    e = run(day(BREAKOUT, missing=("15:00",)))
    assert e.status == "non_evaluable" and e.trades() == []


def test_e8_short_mirror():
    e = run(day({"08:59": (105, 105, 102, 102), "10:10": (102, 102, 90, 90)}))
    assert legs(e.trades()) == [(-1, t("09:00"), 102, t("15:00"), 90)]


def test_e9_no_open_bar_or_no_previous_close_is_no_trade():
    assert run(day(BREAKOUT, missing=("08:30",))).status == "no_trade"
    assert run(day(BREAKOUT, prev_close=None)).status == "no_trade"


# --- timing: what the runner sees ---------------------------------------------------------


def test_signal_comes_with_the_bar_ending_at_the_check_and_fills_on_the_next():
    d = day({**BREAKOUT, "10:29": (108, 108, 102, 102)})
    e = NoiseEngine(context_of(d, SIGMA))
    seen = {b.minute: e.on_bar(b) for b in bars_of(d)}
    (sig,) = [x for x in seen[t("08:59")] if isinstance(x, Signal)]
    assert sig.check == t("09:00") and sig.price == 108 and sig.order.quantity == 1
    assert sig.upper == pytest.approx(107.1) and sig.order.reason == "long"
    (fill,) = seen[t("09:00")]  # 09:00 is flat at the prior close, 108
    assert isinstance(fill, ModelFill) and (fill.price, fill.position) == (108, 1)
    (rev,) = [x for x in seen[t("10:29")] if isinstance(x, Signal)]
    assert rev.order.quantity == -2 and rev.order.reason == "reverse_short"
    (flat,) = [x for x in seen[t("14:59")] if isinstance(x, Signal)]
    assert flat.order.reason == "flatten" and flat.order.quantity == 1
    (last,) = seen[t("15:00")]
    assert last.closed[0].reason == "close" and last.position == 0


def test_out_of_order_bar_is_refused():
    e = NoiseEngine(SessionContext(date(2020, 1, 2), "MNQ", 105, SIGMA))
    e.on_bar(Bar(t("08:30"), 105, 110, 100, 105))
    with pytest.raises(ValueError):
        e.on_bar(Bar(t("08:30"), 105, 110, 100, 105))


def test_decide_table():
    assert decide(0, 108, 107.1, 102.9, 105) == (False, 1)
    assert decide(1, 106, 107.1, 102.9, 105) == (True, 0)
    assert decide(1, 102, 107.1, 102.9, 105) == (True, -1)
    assert decide(1, 110, 107.1, 102.9, 111) == (True, 0)  # VWAP stop; no same-side re-entry
    assert decide(-1, 104, 107.1, 102.9, 105) == (True, 0)
    assert decide(0, 105, 107.1, 102.9, 105) == (False, 0)


# --- sigma table and random days ----------------------------------------------------------


def _sequence(rng: random.Random, n: int):
    days, prev = [], None
    for i in range(n):
        d = random_day(rng)
        vols = {m: rng.choice([0, 1, 5, 40, 300]) for m in d.bars if rng.random() > 0.02}
        if rng.random() < 0.03:
            d = dataclasses.replace(d, bars={})
        prev_close = prev if rng.random() > 0.03 else None
        days.append(
            dataclasses.replace(
                d,
                root="MNQ",
                trade_date=date(2020, 1, 2) + timedelta(days=i),
                volumes=vols,
                prev_close=prev_close,
            )
        )
        if d.bars:
            prev = d.bars[max(d.bars)][3]
    return days


@pytest.mark.parametrize("seed", range(6))
def test_random_days_equal_the_batch_rule(seed):
    rng = random.Random(seed)
    days = _sequence(rng, 80)
    history = SigmaHistory("MNQ")
    traded = 0
    for prepared, raw in zip(STRAT.prepare_all(days), days, strict=True):
        sigma = history.sigma()
        assert sigma == prepared.context["sigma"]
        batch = STRAT.simulate(prepared)
        e = replay(raw, sigma)
        assert e.trades() == batch.trades
        assert e.status == ("no_trade" if batch.status == "ineligible" else batch.status)
        traded += bool(batch.trades)
        history.add_session(raw.bars)
    assert traded > 0


def test_sigma_history_needs_ten_sessions_and_keeps_fourteen():
    h = SigmaHistory()
    d = make_day({"08:59": (105, 105, 100, 100)})
    for _ in range(9):
        h.add_session(d.bars)
    assert h.sigma() == {}
    h.add_session(d.bars)
    assert h.sigma()[9 * 60] == pytest.approx(5 / 105)
    for _ in range(14):
        h.add_session(make_day().bars)  # flat days: move 0
    h.add_session({})  # no-bar session is skipped
    assert h.sigma()[9 * 60] == 0.0
    assert time(9, 0)

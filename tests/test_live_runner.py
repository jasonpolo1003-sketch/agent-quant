"""Runner + FakeBroker on synthetic days: replay equals the engine, and every risk switch.

Same synthetic day as the noise-area fixtures: 08:30 bar (105, 110, 100, 105), flat at the
previous close, sigma 2% -> upper 107.1. BREAKOUT closes 108 at 08:59 -> long at the 09:00
open; RALLY then trades 120 from 10:10 to the close (+12 ticks = $6 per contract).
"""

from __future__ import annotations

import dataclasses
import json
from datetime import datetime, timedelta

from futures_day_builder import make_day, t

from quant_brain.live import STARTUP_WARNING
from quant_brain.live.broker import FakeBroker
from quant_brain.live.engine import bars_of, context_of
from quant_brain.live.runner import RiskConfig, Runner
from quant_brain.workbench.noise import NoiseArea

SIGMA = {h * 60 + m: 0.02 for h in range(9, 15) for m in (0, 30)}
BREAKOUT = {"08:59": (105, 108, 105, 108)}
RALLY = {**BREAKOUT, "10:10": (108, 120, 108, 120)}
REVERSE = {**BREAKOUT, "10:29": (108, 108, 102, 102)}


def day(bars, **kw):
    d = make_day(bars, root="MNQ", **kw)
    return dataclasses.replace(d, prev_close=105, volumes={m: 1 for m in d.bars})


def run(d, risk=RiskConfig(kill_file=None), delay=0.5, delays=None, journal=None, hook=None):
    broker = FakeBroker("MNQ")
    r = Runner(context_of(d, SIGMA), broker, risk, journal, now=datetime(2020, 1, 2, 8, 0))
    for b in bars_of(d):
        end = datetime.combine(d.trade_date, b.minute) + timedelta(minutes=1)
        if hook:
            hook(b, r)
        r.on_bar(b, end + timedelta(seconds=(delays or {}).get(b.minute, delay)))
    r.end_session(datetime(2020, 1, 2, 16, 0))
    return r, broker


def trips(broker):
    return [
        (x.side, x.entry_at.time(), x.entry, x.exit_at.time(), x.exit) for x in broker.round_trips
    ]


def kinds(r, kind):
    return [x for x in r.records if x["kind"] == kind]


def test_replay_matches_the_batch_rule():
    for bars in (RALLY, REVERSE, {**BREAKOUT, "10:29": (108, 108, 106, 106)}):
        d = day(bars)
        r, broker = run(d)
        batch = NoiseArea().simulate(dataclasses.replace(d, context={"sigma": SIGMA}))
        assert trips(broker) == [
            (x.side, x.entry_minute, x.entry_ticks, x.exit_minute, x.exit_ticks)
            for x in batch.trades
        ]
        assert r.halted is None and broker.position() == 0


def test_journal_is_jsonl_with_latency_and_startup_warning(tmp_path):
    path = tmp_path / "j.jsonl"
    r, _ = run(day(REVERSE), journal=path)
    r.close()
    lines = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]
    assert lines[0]["kind"] == "startup" and lines[0]["warning"] == STARTUP_WARNING
    orders = [x for x in lines if x["kind"] == "order"]
    assert [o["quantity"] for o in orders] == [1, -2, 1]
    assert [o["seconds_after_check"] for o in orders] == [0.5, 0.5, 0.5]
    assert orders[0]["check"] == "09:00:00" and orders[0]["ts"] == "2020-01-02T09:00:00.500000"
    assert {"signal", "model_fill", "fill", "session_end"} <= {x["kind"] for x in lines}


def test_late_check_order_is_refused_but_exits_still_go():
    r, broker = run(day(RALLY), delays={t("08:59"): 6.0})  # entry would leave 6 s after 09:00
    assert broker.round_trips == [] and broker.orders == []
    (ref,) = kinds(r, "refused")
    assert ref["reasons"] == ["late"] and ref["wanted"] == 1 and ref["allowed"] == 0
    # late reversal: the exit part goes, the new short is refused
    r, broker = run(day(REVERSE), delays={t("10:29"): 30.0})
    assert trips(broker) == [(1, t("09:00"), 108, t("10:30"), 102)] and broker.position() == 0
    assert kinds(r, "refused")[0]["allowed"] == 0


def test_stale_feed_blocks_entries():
    r, broker = run(
        day(RALLY), delays={t("08:59"): 4.0}, risk=RiskConfig(stale_seconds=3, kill_file=None)
    )
    assert broker.orders == [] and kinds(r, "stale_feed")
    assert "stale_feed" in kinds(r, "refused")[0]["reasons"]


def test_heartbeat_flags_a_silent_feed():
    d = day(RALLY)
    r = Runner(
        context_of(d, SIGMA), FakeBroker(), RiskConfig(kill_file=None), now=datetime(2020, 1, 2, 8)
    )
    r.on_bar(bars_of(d)[0], datetime(2020, 1, 2, 8, 31, 0, 200000))
    r.on_clock(datetime(2020, 1, 2, 8, 32, 5))
    assert not kinds(r, "stale_feed")
    r.on_clock(datetime(2020, 1, 2, 8, 32, 11))
    assert kinds(r, "stale_feed")[0]["source"] == "heartbeat"


def test_daily_loss_stop_flattens_and_halts():
    bars = {**BREAKOUT, "09:20": (108, 108, 90, 90), "09:21": (90, 90, 90, 90)}
    # long 1 at 108 (09:00); 09:20 closes 90 = -18 ticks = -$9 -> stop at $8
    r, broker = run(day(bars), risk=RiskConfig(daily_loss_stop_cents=800, kill_file=None))
    assert r.halted == "daily_loss_stop"
    assert trips(broker) == [(1, t("09:00"), 108, t("09:21"), 90)]
    assert broker.position() == 0 and kinds(r, "halt")[0]["pnl_cents"] == -900


def test_kill_switch_file(tmp_path):
    stop = tmp_path / "STOP"

    def hook(b, r):
        if b.minute == t("11:00"):
            stop.write_text("stop")

    r, broker = run(day(RALLY), risk=RiskConfig(kill_file=stop), hook=hook)
    assert r.halted == "kill_switch"
    assert trips(broker) == [(1, t("09:00"), 108, t("11:01"), 120)]


def test_max_position_clamps_contracts():
    r, _ = run(day(REVERSE), risk=RiskConfig(contracts=3, max_position=2, kill_file=None))
    assert [o["quantity"] for o in kinds(r, "order")] == [2, -4, 2]


def test_session_close_guard_flattens_even_without_the_engine():
    d = day(RALLY)
    broker = FakeBroker()
    r = Runner(
        context_of(d, SIGMA), broker, RiskConfig(kill_file=None), now=datetime(2020, 1, 2, 8)
    )
    broker.place_market_order(1, datetime(2020, 1, 2, 14, 0), "stray", price=100)
    r.on_clock(datetime(2020, 1, 2, 15, 0, 0, 100000))
    assert kinds(r, "order")[0]["reason"] == "session_close" and broker.working() == -1


def test_early_close_flattens_at_noon():
    _, broker = run(day(BREAKOUT, exit_minute="12:12"))
    assert trips(broker) == [(1, t("09:00"), 108, t("12:00"), 108)]

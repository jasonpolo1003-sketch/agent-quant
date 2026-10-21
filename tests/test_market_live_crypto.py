"""Live crypto normalisation on captured Coinbase messages, and reconnects with a fake socket."""

import asyncio
import json

import pytest

from quant_brain.config import PROJECT_ROOT
from quant_brain.market import live_crypto as lc

MESSAGES = json.loads((PROJECT_ROOT / "tests/fixtures/coinbase_ws_messages.json").read_text())["messages"]


def run_all(messages):
    state = lc.FeedState()
    events = []
    for m in messages:
        m = dict(m)
        m.pop("sequence_num", None)  # the trimmed capture is not contiguous
        events += state.process(m)
    return state, events


def test_ticker_trades_book_and_heartbeat_are_normalised():
    _, events = run_all(MESSAGES)
    kinds = [e["type"] for e in events]
    assert {"ticker", "trade", "book", "heartbeat"} <= set(kinds)
    ticker = next(e for e in events if e["type"] == "ticker")
    assert ticker["product"] == "BTC-USD" and ticker["price"] == pytest.approx(83439.74)
    trades = [e for e in events if e["type"] == "trade"]
    assert all(t["history"] for t in trades) and trades[0]["time"] <= trades[-1]["time"]


def test_book_applies_snapshot_then_updates_and_removes_zero_levels():
    state, events = run_all(MESSAGES)
    book = [e for e in events if e["type"] == "book"][-1]
    assert book["best_bid"] == pytest.approx(83439.74) and book["best_ask"] == pytest.approx(83439.75)
    assert book["spread"] == pytest.approx(0.01) and book["spread_bps"] < 0.01
    assert 83420.0 not in state.books["BTC-USD"].bids
    assert book["bids"][0][0] > book["bids"][-1][0] and book["asks"][0][0] < book["asks"][-1][0]


def test_a_sequence_gap_is_reported():
    state = lc.FeedState()
    assert state.process({"sequence_num": 0, "channel": "heartbeats", "events": []}) == []
    out = state.process({"sequence_num": 3, "channel": "heartbeats", "events": []})
    assert out[0]["type"] == "status" and out[0]["state"] == "gap" and "1..2" in out[0]["detail"]


def test_out_of_order_startup_sequence_is_not_a_gap():
    state = lc.FeedState()

    assert state.process(MESSAGES[0]) == []  # subscriptions, sequence 1
    out = state.process(MESSAGES[1])  # ticker snapshot, sequence 0

    assert [event["type"] for event in out] == ["ticker"]
    assert state.last_seq == 1


def test_live_trades_build_one_minute_candles():
    state = lc.FeedState()
    def trades(*rows):
        return {"channel": "market_trades", "events": [{"type": "update", "trades": [
            {"product_id": "BTC-USD", "trade_id": str(i), "price": str(p), "size": "1", "time": t,
             "side": "BUY"} for i, (t, p) in enumerate(rows)]}]}
    state.process(trades(("2026-09-30T01:00:05Z", 100), ("2026-09-30T01:00:30Z", 103),
                         ("2026-09-30T01:00:50Z", 99)))
    out = state.process(trades(("2026-09-30T01:01:02Z", 101)))
    [candle] = [e for e in out if e["type"] == "candle"]
    assert (candle["open"], candle["high"], candle["low"], candle["close"], candle["volume"]) == \
        (100, 103, 99, 99, 3)


class FakeSocket:
    def __init__(self, messages, fail=False):
        self.messages, self.fail, self.sent = messages, fail, []

    async def __aenter__(self):
        if self.fail:
            raise OSError("network down")
        return self

    async def __aexit__(self, *exc):
        return False

    async def send(self, msg):
        self.sent.append(json.loads(msg))

    def __aiter__(self):
        async def gen():
            for m in self.messages:
                yield json.dumps(m)
        return gen()


def test_stream_reports_a_pause_then_goes_live(monkeypatch):
    sockets = iter([FakeSocket([], fail=True), FakeSocket([MESSAGES[1]])])

    async def no_sleep(_):
        return None

    monkeypatch.setattr(lc.asyncio, "sleep", no_sleep)

    async def collect():
        return [e async for e in lc.stream(["BTC-USD"], connect=lambda *a, **k: next(sockets),
                                           stop_after=3)]
    events = asyncio.run(asyncio.wait_for(collect(), timeout=5))
    assert events[0]["state"] == "paused" and "reconnecting" in events[0]["detail"]
    assert events[1]["state"] == "live" and events[2]["type"] == "ticker"
    assert len(events) == 3


def test_a_closed_connection_is_reported_not_silent(monkeypatch):
    sockets = iter([FakeSocket([]), FakeSocket([])])

    async def no_sleep(_):
        return None

    monkeypatch.setattr(lc.asyncio, "sleep", no_sleep)

    async def collect():
        return [e async for e in lc.stream(["BTC-USD"], connect=lambda *a, **k: next(sockets),
                                           stop_after=3)]
    events = asyncio.run(asyncio.wait_for(collect(), timeout=5))
    assert [e["state"] for e in events] == ["live", "paused", "live"]
    assert "connection closed" in events[1]["detail"]

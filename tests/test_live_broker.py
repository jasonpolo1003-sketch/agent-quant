"""FakeBroker (hand-worked fills and P&L) and the ProjectX client's safety and request shapes.

No network: ProjectXBroker is only ever built with a fake environment and a recording fake
transport; the inert default (no live=True, or no credentials) must raise.
"""

from __future__ import annotations

from datetime import datetime, time

import pytest

from quant_brain.live import projectx
from quant_brain.live.broker import FakeBroker
from quant_brain.live.engine import Bar
from quant_brain.live.projectx import (
    LiveTradingDisabled,
    ProjectXBroker,
    bar_from_gateway,
    market_order_payload,
)

T0 = datetime(2024, 3, 15, 9, 0)


def bar(o, minute=time(9, 0)):
    return Bar(minute, o, o, o, o, 10)


def test_fake_broker_fills_at_next_bar_open_and_books_pnl():
    b = FakeBroker("MNQ", fee_cents_per_side=37)
    b.place_market_order(1, T0, "long")
    assert b.position() == 0 and b.working() == 1
    (filled,) = b.on_bar(bar(100), T0)
    assert filled.fill_price == 100 and b.position() == 1 and b.working() == 0
    assert b.day_pnl_cents(mark=104) == 4 * 50 - 37
    b.place_market_order(-2, T0, "reverse")  # sell 2 at 110: close long +10 ticks, open short
    b.on_bar(bar(110, time(10, 30)), datetime(2024, 3, 15, 10, 30))
    assert b.position() == -1 and b.realized_cents == 500 and b.fees_cents == 3 * 37
    assert [(r.side, r.entry, r.exit) for r in b.round_trips] == [(1, 100, 110)]
    b.place_market_order(1, T0, "flat", price=106)  # immediate fill at a given price
    assert b.position() == 0 and b.realized_cents == 500 + 4 * 50
    assert b.day_pnl_cents(mark=0) == 700 - 4 * 37
    with pytest.raises(ValueError):
        b.place_market_order(0, T0)


def test_projectx_is_inert_by_default():
    with pytest.raises(LiveTradingDisabled):
        ProjectXBroker()
    with pytest.raises(LiveTradingDisabled):
        ProjectXBroker(live=True, env={})
    with pytest.raises(LiveTradingDisabled):
        ProjectXBroker(live="yes", env=_env())  # only the literal True arms it


def _env():
    return {
        projectx.ENV_USERNAME: "someone",
        projectx.ENV_API_KEY: "not-a-real-key",
        projectx.ENV_ACCOUNT_ID: "465",
    }


class FakeTransport:
    def __init__(self, replies):
        self.replies, self.calls = replies, []

    def __call__(self, url, body, headers):
        self.calls.append((url, body, headers))
        path = url.split("/api/", 1)[1]
        return self.replies[path]


OK = {"success": True, "errorCode": 0, "errorMessage": None}


def test_projectx_request_shapes_with_a_fake_transport():
    fake = FakeTransport(
        {
            "Auth/loginKey": OK | {"token": "tok"},
            "Order/place": OK | {"orderId": 9056},
            "Position/searchOpen": OK
            | {
                "positions": [
                    {
                        "contractId": "CON.F.US.MNQ.Z26",
                        "type": 2,
                        "size": 1,
                        "averagePrice": 20000.25,
                    }
                ]
            },
        }
    )
    b = ProjectXBroker(live=True, env=_env(), transport=fake, contract_id="CON.F.US.MNQ.Z26")
    assert "not-a-real-key" not in repr(b)
    assert b.place_market_order(-1, T0, "short") == "9056"
    login, place = fake.calls
    assert login[0] == "https://api.topstepx.com/api/Auth/loginKey"
    assert login[1] == {"userName": "someone", "apiKey": "not-a-real-key"}
    assert place[2]["Authorization"] == "Bearer tok"
    assert place[1]["type"] == 2 and place[1]["side"] == 1 and place[1]["size"] == 1
    assert place[1]["accountId"] == 465
    assert b.position() == -1


def test_projectx_failed_login_body_raises():
    fake = FakeTransport({"Auth/loginKey": {"success": False, "errorCode": 3, "errorMessage": "x"}})
    b = ProjectXBroker(live=True, env=_env(), transport=fake)
    with pytest.raises(projectx.GatewayError):
        b.login()


def test_payload_and_bar_conversion():
    buy = market_order_payload(1, "C", 2)
    assert (buy["side"], buy["size"], buy["type"]) == (0, 2, 2)
    d, b = bar_from_gateway(
        {
            "t": "2024-12-20T15:00:00+00:00",
            "o": 21000.25,
            "h": 21001.0,
            "l": 20999.5,
            "c": 21000.0,
            "v": 812,
        },
        0.25,
    )
    assert d.isoformat() == "2024-12-20" and b.minute == time(9, 0)  # CST = UTC-6
    assert (b.open, b.high, b.low, b.close, b.volume) == (84001, 84004, 83998, 84000, 812)
    with pytest.raises(ValueError):
        projectx.to_ticks(21000.1, 0.25)

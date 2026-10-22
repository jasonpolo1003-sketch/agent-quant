"""Live crypto from Coinbase's public WebSocket, the terminal's free live classroom (PROP-010 phase 5).

No key and no account: the public channels (ticker, market_trades, level2,
heartbeats) need none. Messages are normalised into small events: ticker,
trade, book (top levels, spread, mid), candle (1-minute bars built from
trades) and status. A missed sequence number or a dropped connection is
reported as a status event and the stream reconnects for a fresh snapshot,
so the screen never shows a silently stale book. Display and practice only:
live data never feeds a backtest or a strategy card.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import math
from collections.abc import AsyncIterator, Callable, Iterable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

WS_URL = "wss://advanced-trade-ws.coinbase.com"
CHANNELS = ("ticker", "market_trades", "level2", "heartbeats")
SOURCE = {"name": "Coinbase Advanced Trade (public WebSocket)", "freshness": "LIVE",
          "url": "https://docs.cdp.coinbase.com/coinbase-app/advanced-trade-apis/guides/websocket"}


def _f(x: Any) -> float | None:
    if isinstance(x, bool):
        return None
    try:
        value = float(x)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


@dataclass
class OrderBook:
    bids: dict[float, float] = field(default_factory=dict)
    asks: dict[float, float] = field(default_factory=dict)

    def apply(self, updates: Iterable[dict[str, Any]], *, snapshot: bool = False) -> None:
        if snapshot:
            self.bids.clear()
            self.asks.clear()
        for u in updates:
            price, qty = _f(u.get("price_level")), _f(u.get("new_quantity"))
            if price is None or qty is None or price <= 0 or qty < 0:
                continue
            side = self.bids if u.get("side") == "bid" else self.asks
            if qty == 0:
                side.pop(price, None)
            else:
                side[price] = qty

    def view(self, depth: int = 10) -> dict[str, Any]:
        bids = sorted(self.bids.items(), reverse=True)[:depth]
        asks = sorted(self.asks.items())[:depth]
        best_bid = bids[0][0] if bids else None
        best_ask = asks[0][0] if asks else None
        mid = (best_bid + best_ask) / 2 if best_bid is not None and best_ask is not None else None
        spread = best_ask - best_bid if mid is not None else None
        return {"bids": [[p, q] for p, q in bids], "asks": [[p, q] for p, q in asks],
                "best_bid": best_bid, "best_ask": best_ask, "mid": mid, "spread": spread,
                "spread_bps": 10_000 * spread / mid if mid else None}


@dataclass
class CandleBuilder:
    """1-minute OHLCV bars from live trades (not the snapshot's history); the first bar is partial."""
    seconds: int = 60
    current: dict[str, Any] | None = None

    def add(self, time_iso: str, price: float, size: float) -> dict[str, Any] | None:
        """Returns the finished previous bar when a trade opens a new one."""
        ts = datetime.fromisoformat(time_iso.replace("Z", "+00:00")).timestamp()
        bucket = int(ts // self.seconds * self.seconds)
        finished = None
        if self.current and self.current["time"] != bucket:
            finished, self.current = self.current, None
        if self.current is None:
            self.current = {"time": bucket, "open": price, "high": price, "low": price,
                            "close": price, "volume": 0.0}
        c = self.current
        c["high"], c["low"], c["close"] = max(c["high"], price), min(c["low"], price), price
        c["volume"] += size
        return finished


@dataclass
class FeedState:
    """Turns raw Coinbase messages into terminal events; tracks gaps."""
    depth: int = 10
    last_seq: int | None = None
    books: dict[str, OrderBook] = field(default_factory=dict)
    candles: dict[str, CandleBuilder] = field(default_factory=dict)

    def process(self, message: dict[str, Any]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        seq = message.get("sequence_num")
        if isinstance(seq, int):
            if self.last_seq is None:
                self.last_seq = seq
            elif seq > self.last_seq:
                if seq > self.last_seq + 1:
                    out.append({"type": "status", "state": "gap",
                                "detail": f"missed messages {self.last_seq + 1}..{seq - 1}; resyncing"})
                self.last_seq = seq
        channel = message.get("channel")
        when = message.get("timestamp")
        for event in message.get("events", []):
            if channel == "ticker":
                for t in event.get("tickers", []):
                    out.append({"type": "ticker", "product": t["product_id"], "time": when,
                                "price": _f(t.get("price")), "bid": _f(t.get("best_bid")),
                                "ask": _f(t.get("best_ask")),
                                "change_24h_pct": _f(t.get("price_percent_chg_24_h")),
                                "high_24h": _f(t.get("high_24_h")), "low_24h": _f(t.get("low_24_h")),
                                "volume_24h": _f(t.get("volume_24_h"))})
            elif channel == "market_trades":
                history = event.get("type") == "snapshot"
                trades = sorted(event.get("trades", []), key=lambda x: x["time"])
                for t in trades:
                    price, size = _f(t.get("price")), _f(t.get("size"))
                    if price is None or size is None or price <= 0 or size < 0:
                        continue
                    out.append({"type": "trade", "product": t["product_id"], "time": t["time"],
                                "price": price, "size": size, "side": t["side"].lower(),
                                "history": history})
                    if not history:
                        done = self.candles.setdefault(t["product_id"], CandleBuilder()).add(
                            t["time"], price, size)
                        if done:
                            out.append({"type": "candle", "product": t["product_id"], **done})
            elif channel == "l2_data":
                product = event["product_id"]
                book = self.books.setdefault(product, OrderBook())
                book.apply(event.get("updates", []), snapshot=event.get("type") == "snapshot")
                out.append({"type": "book", "product": product, "time": when,
                            **book.view(self.depth)})
            elif channel == "heartbeats":
                out.append({"type": "heartbeat", "time": when})
        return out


def subscribe_messages(products: Iterable[str], channels: Iterable[str] = CHANNELS) -> list[str]:
    return [json.dumps({"type": "subscribe", "product_ids": list(products), "channel": c})
            for c in channels]


async def stream(
    products: Iterable[str], *, channels: Iterable[str] = CHANNELS, depth: int = 10,
    connect: Callable[..., Any] | None = None, max_backoff: float = 30.0,
    stop_after: int | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Yield events forever (or ``stop_after`` events, status events included), reconnecting."""
    count = 0
    inner = _stream(list(products), list(channels), depth, connect, max_backoff)
    async with contextlib.aclosing(inner):
        async for event in inner:
            yield event
            count += 1
            if stop_after is not None and count >= stop_after:
                return


async def _stream(products, channels, depth, connect, max_backoff) -> AsyncIterator[dict[str, Any]]:
    if connect is None:
        import websockets

        connect = websockets.connect
    backoff = 1.0
    while True:
        state = FeedState(depth=depth)
        try:
            async with connect(WS_URL, max_size=2**24) as ws:
                for msg in subscribe_messages(products, channels):
                    await ws.send(msg)
                yield {"type": "status", "state": "live", "detail": f"subscribed {products}",
                       "source": SOURCE}
                backoff = 1.0
                async for raw in ws:
                    events = state.process(json.loads(raw))
                    for event in events:
                        yield event
                    if any(e["type"] == "status" and e["state"] == "gap" for e in events):
                        break  # reconnect for a fresh snapshot
            reason = "connection closed"
        except Exception as exc:  # network errors and websockets' closed/handshake errors
            reason = type(exc).__name__
        yield {"type": "status", "state": "paused",
               "detail": f"feed paused ({reason}); reconnecting in {backoff:.0f}s"}
        await asyncio.sleep(backoff)
        backoff = min(max_backoff, backoff * 2)

"""Broker interface for the live runner, and FakeBroker (the dry-run broker).

The runner thinks in target positions (contracts) and sends signed market orders. A Broker
reports its filled position and the quantity still working, takes market orders stamped with
the wall-clock send time, and turns bars into fills (FakeBroker) or polls them (ProjectX).

FakeBroker fills a market order at a price given at send time, or else at the open of the
next bar it is shown: the same fill the backtest assumes (orders sent at the HH:00/HH:30
check fill at the open of the check-minute bar). It keeps FIFO lots, so `round_trips` can be
compared one for one with the engine's legs, and computes P&L in integer cents from ticks.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from quant_brain.futures import orb


@dataclass
class OrderRecord:
    order_id: str
    quantity: int  # signed contracts
    sent_at: datetime
    tag: str
    status: str = "working"  # working | filled | cancelled
    fill_price: int | None = None
    filled_at: datetime | None = None


@dataclass(frozen=True)
class RoundTrip:
    side: int
    entry_at: datetime
    entry: int
    exit_at: datetime
    exit: int


class Broker(Protocol):
    def position(self) -> int: ...

    def working(self) -> int: ...

    def place_market_order(self, quantity: int, sent_at: datetime, tag: str) -> str: ...

    def on_bar(self, bar, bar_start: datetime) -> list[OrderRecord]: ...

    def day_pnl_cents(self, mark: int) -> int: ...


@dataclass
class _Lot:
    side: int
    price: int
    at: datetime


@dataclass
class FakeBroker:
    root: str = "MNQ"
    fee_cents_per_side: int = 0  # per contract per side
    orders: list[OrderRecord] = field(default_factory=list)
    round_trips: list[RoundTrip] = field(default_factory=list)
    realized_cents: int = 0
    fees_cents: int = 0
    _lots: list[_Lot] = field(default_factory=list)
    _ids: itertools.count = field(default_factory=lambda: itertools.count(1))

    def position(self) -> int:
        return sum(lot.side for lot in self._lots)

    def working(self) -> int:
        return sum(o.quantity for o in self.orders if o.status == "working")

    def place_market_order(
        self, quantity: int, sent_at: datetime, tag: str = "", price: int | None = None
    ) -> str:
        if quantity == 0:
            raise ValueError("zero-quantity order")
        order = OrderRecord(f"fake-{next(self._ids)}", quantity, sent_at, tag)
        self.orders.append(order)
        if price is not None:
            self._fill(order, price, sent_at)
        return order.order_id

    def cancel_all(self) -> None:
        for o in self.orders:
            if o.status == "working":
                o.status = "cancelled"

    def on_bar(self, bar, bar_start: datetime) -> list[OrderRecord]:
        """Fill every working order at this bar's open (in send order)."""
        filled = []
        for o in self.orders:
            if o.status == "working":
                self._fill(o, bar.open, bar_start)
                filled.append(o)
        return filled

    def _fill(self, order: OrderRecord, price: int, at: datetime) -> None:
        order.status, order.fill_price, order.filled_at = "filled", price, at
        step = 1 if order.quantity > 0 else -1
        tick = orb.TICK_CENTS[self.root]
        for _ in range(abs(order.quantity)):
            self.fees_cents += self.fee_cents_per_side
            if self._lots and self._lots[0].side != step:
                lot = self._lots.pop(0)  # FIFO close
                self.realized_cents += int(lot.side * (price - lot.price) * tick)
                self.round_trips.append(RoundTrip(lot.side, lot.at, lot.price, at, price))
            else:
                self._lots.append(_Lot(step, price, at))

    def day_pnl_cents(self, mark: int) -> int:
        tick = orb.TICK_CENTS[self.root]
        open_pnl = sum(int(lot.side * (mark - lot.price) * tick) for lot in self._lots)
        return self.realized_cents + open_pnl - self.fees_cents

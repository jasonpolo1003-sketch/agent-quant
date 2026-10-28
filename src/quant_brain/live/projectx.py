"""TopstepX / ProjectX Gateway API client skeleton. INERT BY DEFAULT; never used in tests.

Written from the public docs at gateway.docs.projectx.com (read 2026-10-28); notes, open
questions and links: brain/sources/projectx_api_notes.md. Not yet run against the API.

Safety. Constructing ProjectXBroker raises LiveTradingDisabled unless `live=True` is passed
AND PROJECTX_USERNAME, PROJECTX_API_KEY and PROJECTX_ACCOUNT_ID are set in the environment.
No credentials live in this repo. Every call goes through an injectable `transport`, so tests
use a fake one and nothing touches the network. Order endpoints are only reached through
`place_market_order` / `cancel_order` / `close_position`, which a live Runner calls.

Topstep rules (help.topstep.com 11187768): the API is for simulated accounts (Combine, XFA),
not Live Funded; orders must originate from the trader's personal PC (no VPS / VPN / remote
server); API access is a separate paid subscription; no sandbox (use a Practice account).

REST (POST, JSON, base https://api.topstepx.com; token as `Authorization: Bearer <token>`):
  Auth/loginKey {userName, apiKey} -> {token}; valid 24 h; a failed login is HTTP 200 with
      success=false, so the body must be read.     Auth/validate {} -> {newToken}
  Account/search {onlyActiveAccounts} -> accounts[{id, name, canTrade, isVisible}]
  Contract/search {searchText, live} -> contracts[{id, name, description, tickSize,
      tickValue, activeContract, symbolId}] (up to 20)      Contract/available {live}
  History/retrieveBars {contractId, live, startTime, endTime, unit (1 s, 2 min, 3 h, 4 day,
      5 week, 6 month), unitNumber, limit (<= 20000), includePartialBar}
      -> bars[{t, o, h, l, c, v}], UTC, example returned newest first
  Order/place {accountId, contractId, type (1 limit, 2 market, 4 stop, 5 trailing stop,
      6 join bid, 7 join ask), side (0 bid = buy, 1 ask = sell), size, limitPrice?,
      stopPrice?, trailPrice?, customTag? (unique per account), stopLossBracket?,
      takeProfitBracket?} -> {orderId}
  Order/cancel {accountId, orderId}   Order/searchOpen {accountId} -> orders[...]
  Order/search, Order/modify (not used)
  Position/searchOpen {accountId} -> positions[{contractId, type (1 long, 2 short), size,
      averagePrice}]   Position/closeContract {accountId, contractId}
  Trade/search {accountId, startTimestamp, endTimestamp?} -> trades[{profitAndLoss (null on
      an opening half-turn), fees, side, size, voided, orderId}]
  Every response carries success / errorCode / errorMessage. Rate limits: retrieveBars 50 per
  30 s, everything else 200 per 60 s; HTTP 429 when exceeded.
Realtime (SignalR over WebSockets, token as access_token query parameter):
  https://rtc.topstepx.com/hubs/user: SubscribeAccounts, SubscribeOrders(accountId),
      SubscribePositions(accountId), SubscribeTrades(accountId); events GatewayUserAccount,
      GatewayUserOrder, GatewayUserPosition, GatewayUserTrade.
  https://rtc.topstepx.com/hubs/market: SubscribeContractQuotes / ContractTrades /
      ContractMarketDepth(contractId); events GatewayQuote, GatewayTrade, GatewayDepth.
  OrderStatus: 0 none, 1 open, 2 filled, 3 cancelled, 4 expired, 5 rejected, 6 pending.
Not implemented here: the SignalR hubs (no SignalR client in the deps). The live bar feed is
the open design choice (notes file): build 1-minute bars from GatewayTrade, or poll
retrieveBars a second after each minute closes.

Doc uncertainties (to settle on a Practice account before any Combine use): whether a bar's
`t` is its start (assumed, as in most feeds); the side codes in Trade/search and
Order/searchOpen (assumed the Order/place codes); whether `size` in Order/searchOpen is
signed (assumed unsigned, sign from side); whether the TopstepX base URL differs per firm
(docs show api.topstepx.com; older snippets show a gateway-api-demo host).
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from datetime import UTC, date, datetime
from enum import IntEnum
from zoneinfo import ZoneInfo

from quant_brain.live.broker import OrderRecord
from quant_brain.live.engine import Bar

BASE_URL = "https://api.topstepx.com"
USER_HUB = "https://rtc.topstepx.com/hubs/user"
MARKET_HUB = "https://rtc.topstepx.com/hubs/market"
ENV_USERNAME = "PROJECTX_USERNAME"
ENV_API_KEY = "PROJECTX_API_KEY"
ENV_ACCOUNT_ID = "PROJECTX_ACCOUNT_ID"
CHICAGO = ZoneInfo("America/Chicago")

Transport = Callable[[str, dict, dict], dict]  # (url, json body, headers) -> response json


class OrderType(IntEnum):
    LIMIT = 1
    MARKET = 2
    STOP = 4
    TRAILING_STOP = 5
    JOIN_BID = 6
    JOIN_ASK = 7


class Side(IntEnum):
    BID = 0  # buy
    ASK = 1  # sell


class PositionType(IntEnum):
    UNDEFINED = 0
    LONG = 1
    SHORT = 2


class BarUnit(IntEnum):
    SECOND = 1
    MINUTE = 2
    HOUR = 3
    DAY = 4
    WEEK = 5
    MONTH = 6


class LiveTradingDisabled(RuntimeError):
    """Raised when the client is built without live=True and environment credentials."""


class GatewayError(RuntimeError):
    pass


def market_order_payload(
    account_id: int, contract_id: str, quantity: int, tag: str | None = None
) -> dict:
    """Order/place body for a signed market order (+ buy, - sell)."""
    if quantity == 0:
        raise ValueError("zero-quantity order")
    return {
        "accountId": account_id,
        "contractId": contract_id,
        "type": int(OrderType.MARKET),
        "side": int(Side.BID if quantity > 0 else Side.ASK),
        "size": abs(quantity),
        "limitPrice": None,
        "stopPrice": None,
        "trailPrice": None,
        "customTag": tag,
        "stopLossBracket": None,
        "takeProfitBracket": None,
    }


def to_ticks(price: float, tick_size: float) -> int:
    ticks = round(price / tick_size)
    if abs(ticks * tick_size - price) > tick_size * 1e-6:
        raise ValueError(f"price {price} is off the {tick_size} grid")
    return ticks


def bar_from_gateway(row: Mapping, tick_size: float) -> tuple[date, Bar]:
    """A retrieveBars row -> (CT trade date, engine Bar in ticks). Assumes `t` = bar start."""
    stamp = datetime.fromisoformat(str(row["t"]).replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=UTC)
    ct = stamp.astimezone(CHICAGO)
    px = [to_ticks(float(row[k]), tick_size) for k in ("o", "h", "l", "c")]
    return ct.date(), Bar(ct.time().replace(second=0, microsecond=0), *px, row.get("v", 0))


def _requests_transport(url: str, body: dict, headers: dict) -> dict:  # pragma: no cover
    import requests

    response = requests.post(url, json=body, headers=headers, timeout=5)
    response.raise_for_status()
    return response.json()


class ProjectXBroker:
    """Broker (live/broker.py protocol) backed by the ProjectX Gateway. Skeleton: untested
    against the real API; see the module docstring for what is assumed."""

    def __init__(
        self,
        *,
        live: bool = False,
        contract_id: str | None = None,
        tick_size: float = 0.25,
        tick_value_cents: int = 50,
        env: Mapping[str, str] | None = None,
        transport: Transport | None = None,
        base_url: str = BASE_URL,
    ):
        if live is not True:
            raise LiveTradingDisabled(
                "ProjectXBroker is inert: pass live=True and set credentials in the environment"
            )
        env = os.environ if env is None else env
        missing = [k for k in (ENV_USERNAME, ENV_API_KEY, ENV_ACCOUNT_ID) if not env.get(k)]
        if missing:
            raise LiveTradingDisabled(f"missing environment variables: {', '.join(missing)}")
        self._username = env[ENV_USERNAME]
        self._api_key = env[ENV_API_KEY]
        self.account_id = int(env[ENV_ACCOUNT_ID])
        self.contract_id = contract_id
        self.tick_size = tick_size
        self.tick_value_cents = tick_value_cents
        self.base_url = base_url.rstrip("/")
        self._transport = transport or _requests_transport
        self._token: str | None = None
        self.session_start: datetime | None = None
        self.sent: list[OrderRecord] = []

    def __repr__(self) -> str:  # never print the key
        return f"ProjectXBroker(account_id={self.account_id}, contract_id={self.contract_id!r})"

    # --- plumbing --------------------------------------------------------------------------

    def _post(self, path: str, body: dict, auth: bool = True) -> dict:
        headers = {"Content-Type": "application/json", "accept": "text/plain"}
        if auth:
            if self._token is None:
                self.login()
            headers["Authorization"] = f"Bearer {self._token}"
        out = self._transport(f"{self.base_url}/api/{path}", body, headers)
        if not out.get("success") or out.get("errorCode", 0) != 0:
            raise GatewayError(
                f"{path}: errorCode {out.get('errorCode')} {out.get('errorMessage')}"
            )
        return out

    def login(self) -> None:
        out = self._post(
            "Auth/loginKey", {"userName": self._username, "apiKey": self._api_key}, False
        )
        self._token = out["token"]

    def validate(self) -> None:
        self._token = self._post("Auth/validate", {}).get("newToken") or self._token

    # --- reads -----------------------------------------------------------------------------

    def search_accounts(self, only_active: bool = True) -> list[dict]:
        return self._post("Account/search", {"onlyActiveAccounts": only_active})["accounts"]

    def search_contracts(self, text: str, live: bool = False) -> list[dict]:
        return self._post("Contract/search", {"searchText": text, "live": live})["contracts"]

    def retrieve_bars(
        self, start: datetime, end: datetime, *, live: bool = False, limit: int = 20_000
    ) -> list[dict]:
        """Closed 1-minute bars in [start, end] (UTC-aware datetimes), oldest first."""
        body = {
            "contractId": self.contract_id,
            "live": live,
            "startTime": start.astimezone(UTC).isoformat(),
            "endTime": end.astimezone(UTC).isoformat(),
            "unit": int(BarUnit.MINUTE),
            "unitNumber": 1,
            "limit": limit,
            "includePartialBar": False,
        }
        return sorted(self._post("History/retrieveBars", body)["bars"], key=lambda r: r["t"])

    def open_positions(self) -> list[dict]:
        return self._post("Position/searchOpen", {"accountId": self.account_id})["positions"]

    def open_orders(self) -> list[dict]:
        return self._post("Order/searchOpen", {"accountId": self.account_id})["orders"]

    def trades_since(self, start: datetime) -> list[dict]:
        body = {"accountId": self.account_id, "startTimestamp": start.isoformat()}
        return self._post("Trade/search", body)["trades"]

    # --- Broker protocol -------------------------------------------------------------------

    def position(self) -> int:
        out = 0
        for p in self.open_positions():
            if p["contractId"] == self.contract_id:
                out += p["size"] if p["type"] == PositionType.LONG else -p["size"]
        return out

    def working(self) -> int:
        out = 0
        for o in self.open_orders():
            if o["contractId"] == self.contract_id and o["type"] == OrderType.MARKET:
                out += o["size"] if o["side"] == Side.BID else -o["size"]
        return out

    def place_market_order(self, quantity: int, sent_at: datetime, tag: str = "") -> str:
        body = market_order_payload(self.account_id, self.contract_id, quantity, None)
        order_id = str(self._post("Order/place", body)["orderId"])
        self.sent.append(OrderRecord(order_id, quantity, sent_at, tag))
        return order_id

    def cancel_order(self, order_id: str) -> None:
        self._post("Order/cancel", {"accountId": self.account_id, "orderId": int(order_id)})

    def close_position(self) -> None:
        self._post(
            "Position/closeContract", {"accountId": self.account_id, "contractId": self.contract_id}
        )

    def on_bar(self, bar, bar_start: datetime) -> list[OrderRecord]:
        """Fills arrive via the user hub (GatewayUserTrade) or Trade/search; not wired yet."""
        return []

    def day_pnl_cents(self, mark: int) -> int:
        """Realized P&L minus fees since session_start, plus open P&L at `mark` ticks."""
        if self.session_start is None:
            raise RuntimeError("set session_start before trading")
        realized = 0.0
        for tr in self.trades_since(self.session_start):
            if tr.get("voided"):
                continue
            realized += (tr.get("profitAndLoss") or 0) - (tr.get("fees") or 0)
        open_cents = 0
        for p in self.open_positions():
            if p["contractId"] == self.contract_id:
                side = 1 if p["type"] == PositionType.LONG else -1
                avg = p["averagePrice"] / self.tick_size
                open_cents += round(side * p["size"] * (mark - avg) * self.tick_value_cents)
        return round(realized * 100) + open_cents

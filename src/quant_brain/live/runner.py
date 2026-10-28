"""Per-minute loop for SC-FUT-0005: closed bar -> engine -> risk gates -> broker -> journal.

One Runner per session. Call `on_bar(bar, now)` as each 1-minute bar closes (`now` = wall
clock, naive America/Chicago), `on_clock(now)` on a heartbeat between bars (a few times a
second live), and `end_session()` at the end. Everything goes to a JSONL journal: signals,
orders (with seconds since the check), fills, refusals, risk events.

The runner trades target positions: target = engine side x RiskConfig.contracts, clamped to
max_position; the order is target minus (filled + working). Risk switches:
- kill switch: if `kill_file` exists, flatten and stop for the session;
- daily loss stop: day P&L (realized + open at the last close, after fees) <= -limit ->
  flatten and stop for the session;
- stale feed: a bar received more than `stale_seconds` after it closed, or no bar for that
  long (heartbeat) -> no exposure-increasing orders;
- late order: a check order going out more than `max_order_delay_seconds` after the
  HH:00/HH:30 check (the SC-FUT-0005 review: one minute late costs 31% of the edge) -> no
  exposure-increasing orders (exits still go);
- session close: flatten when the flatten minute arrives even if the engine has not.
Blocked increases shrink to the risk-reducing part (a refused reversal becomes an exit).
Exits are never refused. The engine keeps its own model position, so a refused entry leaves
the broker flat until the engine's target comes back to the broker's position.

STARTUP_WARNING (Topstep: personal PC only, Combine/XFA only) is logged and journaled at
construction; nothing else here can check it.
"""

from __future__ import annotations

import dataclasses
import json
import logging
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path

from quant_brain.live import STARTUP_WARNING
from quant_brain.live.broker import Broker
from quant_brain.live.engine import Bar, ModelFill, NoiseEngine, SessionContext, Signal, Void

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class RiskConfig:
    contracts: int = 1  # contracts per engine unit
    max_position: int = 2
    daily_loss_stop_cents: int = 50_000
    stale_seconds: float = 10.0
    max_order_delay_seconds: float = 5.0
    kill_file: Path | None = Path("STOP")


def _jsonable(x):
    if dataclasses.is_dataclass(x):
        return {k: _jsonable(v) for k, v in dataclasses.asdict(x).items()}
    if isinstance(x, dict):
        return {str(k): _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    if isinstance(x, (datetime, date, time)):
        return x.isoformat()
    if isinstance(x, Path):
        return str(x)
    return x


class Runner:
    def __init__(
        self,
        ctx: SessionContext,
        broker: Broker,
        risk: RiskConfig = RiskConfig(),
        journal_path: Path | None = None,
        now: datetime | None = None,
    ):
        self.ctx, self.broker, self.risk = ctx, broker, risk
        self.engine = NoiseEngine(ctx)
        self.records: list[dict] = []
        self.halted: str | None = None
        self._journal = journal_path.open("a", encoding="utf-8") if journal_path else None
        self._last_bar_end: datetime | None = None
        self._stale_flagged = False
        self._flat_at = datetime.combine(ctx.trade_date, time(0)) + timedelta(
            minutes=self.engine._flat_n
        )
        log.warning(STARTUP_WARNING)
        self._record(
            now or datetime.now(),
            "startup",
            warning=STARTUP_WARNING,
            context=ctx,
            risk=risk,
            mode=type(broker).__name__,
        )

    # --- journal ---------------------------------------------------------------------------

    def _record(self, now: datetime, kind: str, **fields) -> dict:
        rec = {"ts": now.isoformat(), "kind": kind} | _jsonable(fields)
        self.records.append(rec)
        if self._journal:
            self._journal.write(json.dumps(rec, sort_keys=True) + "\n")
            self._journal.flush()
        return rec

    def _at(self, minute: time) -> datetime:
        return datetime.combine(self.ctx.trade_date, minute)

    # --- the loop --------------------------------------------------------------------------

    def on_bar(self, bar: Bar, now: datetime) -> None:
        start = self._at(bar.minute)
        bar_end = start + timedelta(minutes=1)
        for order in self.broker.on_bar(bar, start):
            self._record(
                now,
                "fill",
                order_id=order.order_id,
                quantity=order.quantity,
                price=order.fill_price,
                filled_at=order.filled_at,
                tag=order.tag,
                position=self.broker.position(),
            )
        self._last_bar_end = bar_end
        lag = (now - bar_end).total_seconds()
        stale = lag > self.risk.stale_seconds
        if stale:
            self._record(now, "stale_feed", bar=bar.minute, lag_seconds=lag)
        self._stale_flagged = stale
        self._check_kill(now)
        for ev in self.engine.on_bar(bar):
            if isinstance(ev, Signal):
                self._record(now, "signal", **dataclasses.asdict(ev))
                if ev.order is not None:
                    self._act(ev, now, stale)
            elif isinstance(ev, ModelFill):
                self._record(now, "model_fill", **dataclasses.asdict(ev))
            elif isinstance(ev, Void):
                self._record(now, "void", check=ev.check, reason=ev.reason)
                self._move_to(self.engine.side * self.risk.contracts, now, "reconcile", stale)
        pnl = self.broker.day_pnl_cents(bar.close)
        if not self.halted and pnl <= -self.risk.daily_loss_stop_cents:
            self._halt(now, "daily_loss_stop", pnl_cents=pnl)
        if bar_end >= self._flat_at:
            self._session_close(now)

    def on_clock(self, now: datetime) -> None:
        """Heartbeat between bars: stale feed, kill switch and session-close flatten."""
        if self._last_bar_end is not None and not self._stale_flagged:
            behind = (now - self._last_bar_end).total_seconds() - 60
            if behind > self.risk.stale_seconds:
                self._stale_flagged = True
                self._record(now, "stale_feed", lag_seconds=behind, source="heartbeat")
        self._check_kill(now)
        if now >= self._flat_at:
            self._session_close(now)

    def end_session(self, now: datetime | None = None) -> dict:
        status = self.engine.end_session()
        return self._record(
            now or datetime.now(),
            "session_end",
            engine_status=status,
            model_legs=self.engine.legs,
            broker_position=self.broker.position(),
            broker_working=self.broker.working(),
            halted=self.halted,
        )

    # --- orders and risk -------------------------------------------------------------------

    def _act(self, sig: Signal, now: datetime, stale: bool) -> None:
        delay = (now - self._at(sig.check)).total_seconds()
        late = delay > self.risk.max_order_delay_seconds
        self._move_to(
            sig.target * self.risk.contracts, now, sig.order.reason, stale, late, delay, sig.check
        )

    def _move_to(
        self,
        target: int,
        now: datetime,
        reason: str,
        stale: bool = False,
        late: bool = False,
        delay: float | None = None,
        check: time | None = None,
    ) -> None:
        cap = self.risk.max_position
        target = max(-cap, min(cap, target))
        if self.halted:
            target = 0
        current = self.broker.position() + self.broker.working()
        if target == current:
            return
        increases = target != 0 and (abs(target) > abs(current) or target * current < 0)
        blocks = [
            name
            for name, on in (("stale_feed", stale), ("late", late), ("halted", self.halted))
            if on
        ]
        if increases and blocks:
            allowed = 0 if target * current < 0 else current
            self._record(
                now,
                "refused",
                wanted=target,
                allowed=allowed,
                reasons=blocks,
                check=check,
                seconds_after_check=delay,
            )
            target = allowed
            if target == current:
                return
        qty = target - current
        order_id = self.broker.place_market_order(qty, now, reason)
        self._record(
            now,
            "order",
            order_id=order_id,
            quantity=qty,
            target=target,
            reason=reason,
            check=check,
            seconds_after_check=delay,
        )

    def _check_kill(self, now: datetime) -> None:
        kill = self.risk.kill_file
        if kill is not None and kill.exists() and self.halted != "kill_switch":
            self._halt(now, "kill_switch", file=kill)

    def _halt(self, now: datetime, reason: str, **fields) -> None:
        self.halted = reason
        self._record(now, "halt", reason=reason, **fields)
        self._move_to(0, now, reason)

    def _session_close(self, now: datetime) -> None:
        if self.broker.position() + self.broker.working() != 0:
            self._move_to(0, now, "session_close")

    def close(self) -> None:
        if self._journal:
            self._journal.close()
            self._journal = None

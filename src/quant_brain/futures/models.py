"""Immutable event contracts for deterministic futures replay."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import IntEnum


class ReplayContractError(ValueError):
    """Input events violate the deterministic replay contract."""


@dataclass(frozen=True, slots=True)
class TickPrice:
    """A non-negative price represented as an exact number of contract ticks."""

    ticks: int

    def __post_init__(self) -> None:
        if type(self.ticks) is not int or self.ticks < 0:
            raise ValueError("ticks must be a non-negative integer")


@dataclass(frozen=True, slots=True)
class MinorMoney:
    """A signed monetary amount in the currency's minor unit (for USD, cents)."""

    units: int

    def __post_init__(self) -> None:
        if type(self.units) is not int:
            raise ValueError("units must be an integer")


def futures_pnl(
    entry: TickPrice, exit_: TickPrice, *, position: int, tick_value_minor: int
) -> MinorMoney:
    """Exact futures P&L before fees; signed position is positive long, negative short."""
    if type(position) is not int or position == 0:
        raise ValueError("position must be a non-zero integer")
    if type(tick_value_minor) is not int or tick_value_minor <= 0:
        raise ValueError("tick_value_minor must be a positive integer")
    return MinorMoney((exit_.ticks - entry.ticks) * position * tick_value_minor)


class EventKind(IntEnum):
    """Explicit processing priority for events with the same process time."""

    SESSION_TRANSITION = 10
    BAR_PUBLISHED = 20
    FORCED_FLATTEN = 30
    ORDER_CANCELLED = 40
    FILL = 50
    SIGNAL = 60
    ORDER_ACTIVATED = 70


@dataclass(frozen=True, slots=True)
class ReplayEvent:
    """An immutable event with occurrence and decision-availability timestamps."""

    event_id: str
    kind: EventKind
    event_time: datetime
    available_at: datetime
    source: str
    source_sequence: int
    payload_sha256: str

    def __post_init__(self) -> None:
        if type(self.event_id) is not str or not self.event_id:
            raise ValueError("event_id must be a non-empty string")
        if not isinstance(self.kind, EventKind):
            raise ValueError("kind must be an EventKind")
        if type(self.source) is not str or not self.source:
            raise ValueError("source must be a non-empty string")
        if type(self.source_sequence) is not int or self.source_sequence < 0:
            raise ValueError("source_sequence must be non-negative")
        if type(self.payload_sha256) is not str or len(self.payload_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in self.payload_sha256
        ):
            raise ValueError("payload_sha256 must be 64 lowercase hexadecimal characters")
        for name, value in (("event_time", self.event_time), ("available_at", self.available_at)):
            if not isinstance(value, datetime):
                raise ValueError(f"{name} must be a datetime")
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{name} must be timezone-aware UTC")
            object.__setattr__(self, name, value.astimezone(UTC))

    @property
    def process_at(self) -> datetime:
        """The earliest time replay may process the event."""
        return max(self.event_time, self.available_at)

    @property
    def order_key(self) -> tuple[datetime, int, str, int, str]:
        """A stable total-order key independent of input/container order."""
        return (
            self.process_at,
            int(self.kind),
            self.source,
            self.source_sequence,
            self.event_id,
        )


def order_events(events: Iterable[ReplayEvent]) -> list[ReplayEvent]:
    """Deduplicate exact replays and return the frozen deterministic order."""
    unique: dict[str, ReplayEvent] = {}
    for event in events:
        prior = unique.get(event.event_id)
        if prior is None:
            unique[event.event_id] = event
        elif prior != event:
            raise ReplayContractError(f"conflicting duplicate event_id: {event.event_id}")
    return sorted(unique.values(), key=lambda event: event.order_key)


def canonical_event_bytes(event: ReplayEvent) -> bytes:
    """Serialize one event to the versioned, byte-stable scientific format."""
    values = {
        "schema_version": 1,
        "event_id": event.event_id,
        "kind": int(event.kind),
        "event_time": event.event_time.isoformat(timespec="microseconds").replace("+00:00", "Z"),
        "available_at": event.available_at.isoformat(timespec="microseconds").replace(
            "+00:00", "Z"
        ),
        "source": event.source,
        "source_sequence": event.source_sequence,
        "payload_sha256": event.payload_sha256,
    }
    return json.dumps(values, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()

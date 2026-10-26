"""Phase B replay contracts: deterministic events before futures behavior exists."""

from datetime import UTC, datetime, timedelta, timezone
from itertools import permutations

import pytest

from quant_brain.futures.models import (
    EventKind,
    MinorMoney,
    ReplayContractError,
    ReplayEvent,
    TickPrice,
    canonical_event_bytes,
    futures_pnl,
    order_events,
)


def utc(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 3, 9, hour, minute, tzinfo=UTC)


def event(
    event_id: str,
    kind: EventKind,
    *,
    event_time: datetime,
    available_at: datetime,
    source: str,
    sequence: int,
) -> ReplayEvent:
    return ReplayEvent(
        event_id=event_id,
        kind=kind,
        event_time=event_time,
        available_at=available_at,
        source=source,
        source_sequence=sequence,
        payload_sha256="a" * 64,
    )


def test_event_order_is_total_and_independent_of_input_permutation():
    events = [
        event(
            "scheduled-flatten",
            EventKind.FORCED_FLATTEN,
            event_time=utc(20, 8),
            available_at=utc(12),
            source="account-rules",
            sequence=1,
        ),
        event(
            "bar-close",
            EventKind.BAR_PUBLISHED,
            event_time=utc(20, 7),
            available_at=utc(20, 8),
            source="market",
            sequence=11,
        ),
        event(
            "cancel",
            EventKind.ORDER_CANCELLED,
            event_time=utc(20, 8),
            available_at=utc(20, 8),
            source="risk",
            sequence=1,
        ),
        event(
            "late-bar",
            EventKind.BAR_PUBLISHED,
            event_time=utc(20, 6),
            available_at=utc(20, 8) + timedelta(seconds=1),
            source="market",
            sequence=10,
        ),
    ]

    expected = ["bar-close", "scheduled-flatten", "cancel", "late-bar"]
    for shuffled in permutations(events):
        assert [item.event_id for item in order_events(shuffled)] == expected


def test_event_rejects_naive_timestamps():
    with pytest.raises(ValueError, match="timezone-aware"):
        event(
            "naive",
            EventKind.BAR_PUBLISHED,
            event_time=datetime(2026, 3, 9, 9, 30),
            available_at=utc(14, 30),
            source="market",
            sequence=1,
        )


def test_event_normalizes_aware_timestamps_to_utc():
    eastern = timezone(timedelta(hours=-4))

    item = event(
        "aware",
        EventKind.BAR_PUBLISHED,
        event_time=datetime(2026, 3, 9, 9, 30, tzinfo=eastern),
        available_at=datetime(2026, 3, 9, 9, 31, tzinfo=eastern),
        source="market",
        sequence=1,
    )

    assert item.event_time == utc(13, 30)
    assert item.available_at == utc(13, 31)
    assert item.event_time.tzinfo is UTC and item.available_at.tzinfo is UTC


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"event_id": ""}, "event_id"),
        ({"event_id": 1}, "event_id"),
        ({"source": ""}, "source"),
        ({"source": 1}, "source"),
        ({"source_sequence": -1}, "source_sequence"),
        ({"source_sequence": float("nan")}, "source_sequence"),
        ({"kind": 20}, "kind"),
        ({"event_time": "2026-03-09T14:30:00Z"}, "event_time"),
        ({"available_at": "2026-03-09T14:30:00Z"}, "available_at"),
        ({"payload_sha256": "not-a-hash"}, "payload_sha256"),
        ({"payload_sha256": 1}, "payload_sha256"),
    ],
)
def test_event_rejects_invalid_identity_fields(change, message):
    values = {
        "event_id": "valid",
        "kind": EventKind.BAR_PUBLISHED,
        "event_time": utc(14, 30),
        "available_at": utc(14, 30),
        "source": "market",
        "source_sequence": 0,
        "payload_sha256": "a" * 64,
        **change,
    }

    with pytest.raises(ValueError, match=message):
        ReplayEvent(**values)


def test_futures_pnl_uses_exact_integer_ticks_and_minor_currency_units():
    entry = TickPrice(420_000)
    exit_ = TickPrice(420_003)

    assert futures_pnl(entry, exit_, position=2, tick_value_minor=125) == MinorMoney(750)
    assert futures_pnl(entry, exit_, position=-2, tick_value_minor=125) == MinorMoney(-750)


@pytest.mark.parametrize(
    ("operation", "message"),
    [
        (lambda: TickPrice(-1), "ticks"),
        (lambda: TickPrice(1.0), "ticks"),
        (lambda: MinorMoney(1.5), "units"),
        (lambda: futures_pnl(TickPrice(1), TickPrice(2), position=0, tick_value_minor=125),
         "position"),
        (lambda: futures_pnl(TickPrice(1), TickPrice(2), position=1, tick_value_minor=0),
         "tick_value_minor"),
    ],
)
def test_exact_numeric_contract_rejects_invalid_values(operation, message):
    with pytest.raises(ValueError, match=message):
        operation()


def test_event_canonical_serialization_is_byte_specified():
    item = event(
        "bar-1",
        EventKind.BAR_PUBLISHED,
        event_time=utc(14, 30),
        available_at=utc(14, 30) + timedelta(microseconds=12),
        source="market",
        sequence=7,
    )

    assert canonical_event_bytes(item) == (
        b'{"available_at":"2026-03-09T14:30:00.000012Z","event_id":"bar-1",'
        b'"event_time":"2026-03-09T14:30:00.000000Z","kind":20,'
        b'"payload_sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",'
        b'"schema_version":1,"source":"market","source_sequence":7}'
    )


def test_event_order_deduplicates_exact_replays_and_rejects_conflicting_ids():
    original = event(
        "same-id",
        EventKind.BAR_PUBLISHED,
        event_time=utc(14, 30),
        available_at=utc(14, 30),
        source="market",
        sequence=1,
    )
    exact_replay = event(
        "same-id",
        EventKind.BAR_PUBLISHED,
        event_time=utc(14, 30),
        available_at=utc(14, 30),
        source="market",
        sequence=1,
    )
    conflicting = event(
        "same-id",
        EventKind.BAR_PUBLISHED,
        event_time=utc(14, 31),
        available_at=utc(14, 31),
        source="market",
        sequence=2,
    )

    assert order_events([exact_replay, original]) == [original]
    with pytest.raises(ReplayContractError, match="conflicting duplicate event_id"):
        order_events([original, conflicting])

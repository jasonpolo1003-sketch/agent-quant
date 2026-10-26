"""Development-only physical partition of time-ordered Databento OHLCV files.

The locked held-out period must stay unseen. `split_ohlcv` copies records
byte-for-byte while their `ts_event` is before the cutoff and stops at the
first record at or after it: no locked-period record is written, and only its
timestamp is ever inspected. Outputs report counts and timestamps, never prices.
"""

from __future__ import annotations

import hashlib
import struct
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import databento_dbn as dbn
import zstandard

CHICAGO = ZoneInfo("America/Chicago")
OHLCV_SCHEMAS = {"ohlcv-1s", "ohlcv-1m", "ohlcv-1h", "ohlcv-1d"}
CHUNK_BYTES = 1 << 20
# DBN v2/v3 metadata: magic(3) version(1) length(4) dataset(16) schema(2) start(8) end(8).
_END_OFFSET = 34


def trade_date_cutoff_ns(first_locked: date) -> int:
    """UTC nanoseconds at which CME trade date `first_locked` can first begin.

    A Globex trade date D opens at 17:00 CT on the prior calendar day, after the
    16:00-17:00 CT maintenance break, so everything before this instant belongs
    to trade dates before D.
    """
    opens = datetime.combine(first_locked - timedelta(days=1), time(17), tzinfo=CHICAGO)
    return int(opens.timestamp()) * 1_000_000_000


def ns_to_iso(ns: int) -> str:
    return datetime.fromtimestamp(ns / 1e9, tz=UTC).isoformat()


@dataclass(frozen=True)
class SplitResult:
    source: str
    output: str
    schema: str
    records_written: int
    first_ts_event: str | None
    last_ts_event: str | None
    reached_cutoff: bool
    output_sha256: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _patch_end(metadata_bytes: bytes, end_ns: int) -> bytes:
    if metadata_bytes[:3] != b"DBN" or metadata_bytes[3] < 2:
        raise ValueError("unsupported DBN metadata version")
    return (
        metadata_bytes[:_END_OFFSET] + struct.pack("<Q", end_ns) + metadata_bytes[_END_OFFSET + 8 :]
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(CHUNK_BYTES), b""):
            digest.update(block)
    return digest.hexdigest()


def split_ohlcv(source: Path, output: Path, cutoff_ns: int) -> SplitResult:
    """Write records of `source` with ts_event < cutoff_ns to a new `output`.

    Fails closed on an existing output, a non-OHLCV schema, or any decrease in
    ts_event (the early stop is only valid for time-ordered files).
    """
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    decoder = dbn.DBNDecoder(upgrade_policy=dbn.VersionUpgradePolicy.AS_IS)
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_name(output.name + ".partial")
    schema = ""
    written = 0
    first_ts: int | None = None
    last_ts: int | None = None
    reached = False
    metadata_seen = False
    try:
        with source.open("rb") as raw, partial.open("wb") as sink:
            reader = zstandard.ZstdDecompressor().stream_reader(raw)
            writer = zstandard.ZstdCompressor(level=3).stream_writer(sink, closefd=False)
            while not reached:
                chunk = reader.read(CHUNK_BYTES)
                if not chunk:
                    break
                for record in decoder.write_and_decode(chunk):
                    if not metadata_seen:
                        if not isinstance(record, dbn.Metadata):
                            raise ValueError(f"{source.name}: missing DBN metadata")
                        schema = str(record.schema)
                        if schema not in OHLCV_SCHEMAS:
                            raise ValueError(
                                f"{source.name}: schema {schema} is not time-ordered OHLCV"
                            )
                        writer.write(_patch_end(bytes(record.encode()), cutoff_ns))
                        metadata_seen = True
                        continue
                    ts = record.ts_event
                    if last_ts is not None and ts < last_ts:
                        raise ValueError(
                            f"{source.name}: ts_event decreased after record {written}"
                        )
                    if ts >= cutoff_ns:
                        reached = True
                        break
                    writer.write(bytes(record))
                    written += 1
                    first_ts = ts if first_ts is None else first_ts
                    last_ts = ts
            writer.flush(zstandard.FLUSH_FRAME)
            writer.close()
        if not metadata_seen:
            raise ValueError(f"{source.name}: empty DBN stream")
    except BaseException:
        partial.unlink(missing_ok=True)
        raise
    partial.rename(output)
    return SplitResult(
        source=source.name,
        output=output.name,
        schema=schema,
        records_written=written,
        first_ts_event=None if first_ts is None else ns_to_iso(first_ts),
        last_ts_event=None if last_ts is None else ns_to_iso(last_ts),
        reached_cutoff=reached,
        output_sha256=sha256_file(output),
    )

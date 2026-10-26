"""Synthetic tests for the development-only DBN partition."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import databento_dbn as dbn
import pytest
import zstandard

from quant_brain.futures.dev_partition import split_ohlcv, trade_date_cutoff_ns

NS = 1_000_000_000


def _write_dbn(path: Path, timestamps: list[int], *, schema=dbn.Schema.OHLCV_1M) -> None:
    metadata = dbn.Metadata(
        dataset="GLBX.MDP3",
        schema=schema,
        start=0,
        end=10**18,
        stype_in=dbn.SType.RAW_SYMBOL,
        stype_out=dbn.SType.INSTRUMENT_ID,
        symbols=["MNQ.FUT"],
        partial=[],
        not_found=[],
        mappings=[],
    )
    payload = bytearray(metadata.encode())
    for i, ts in enumerate(timestamps):
        record = dbn.OHLCVMsg(
            rtype=0x21,
            publisher_id=1,
            instrument_id=7,
            ts_event=ts,
            open=100 + i,
            high=110 + i,
            low=90 + i,
            close=105 + i,
            volume=1,
        )
        payload += bytes(record)
    path.write_bytes(zstandard.ZstdCompressor().compress(bytes(payload)))


def _decode(path: Path) -> list:
    with path.open("rb") as handle:
        raw = zstandard.ZstdDecompressor().stream_reader(handle).read()
    return dbn.DBNDecoder(upgrade_policy=dbn.VersionUpgradePolicy.AS_IS).write_and_decode(raw)


def test_cutoff_is_globex_open_of_first_locked_trade_date():
    # 2024-12-31 17:00 CST == 23:00 UTC
    assert trade_date_cutoff_ns(date(2025, 1, 1)) == 1735686000 * NS
    # summer (CDT): 2024-06-30 17:00 CDT == 22:00 UTC
    assert trade_date_cutoff_ns(date(2024, 7, 1)) == 1719784800 * NS


def test_writes_only_pre_cutoff_records_byte_exact(tmp_path):
    src, out = tmp_path / "src.dbn.zst", tmp_path / "out.dbn.zst"
    _write_dbn(src, [10, 20, 30, 40, 50])
    result = split_ohlcv(src, out, cutoff_ns=35)
    decoded = _decode(out)
    assert decoded[0].end == 35
    assert [r.ts_event for r in decoded[1:]] == [10, 20, 30]
    assert [bytes(r) for r in decoded[1:]] == [bytes(r) for r in _decode(src)[1:4]]
    assert result.records_written == 3 and result.reached_cutoff
    assert not (tmp_path / "out.dbn.zst.partial").exists()


def test_record_at_cutoff_is_excluded(tmp_path):
    src, out = tmp_path / "src.dbn.zst", tmp_path / "out.dbn.zst"
    _write_dbn(src, [10, 35, 36])
    assert split_ohlcv(src, out, cutoff_ns=35).records_written == 1


def test_refuses_overwrite_and_unordered_input(tmp_path):
    src, out = tmp_path / "src.dbn.zst", tmp_path / "out.dbn.zst"
    _write_dbn(src, [10, 30, 20, 40])
    with pytest.raises(ValueError, match="decreased"):
        split_ohlcv(src, out, cutoff_ns=35)
    assert not out.exists() and not (tmp_path / "out.dbn.zst.partial").exists()
    out.write_bytes(b"x")
    with pytest.raises(FileExistsError):
        split_ohlcv(src, out, cutoff_ns=35)


def test_rejects_non_ohlcv_schema(tmp_path):
    src, out = tmp_path / "src.dbn.zst", tmp_path / "out.dbn.zst"
    _write_dbn(src, [10], schema=dbn.Schema.STATISTICS)
    with pytest.raises(ValueError, match="not time-ordered OHLCV"):
        split_ohlcv(src, out, cutoff_ns=35)

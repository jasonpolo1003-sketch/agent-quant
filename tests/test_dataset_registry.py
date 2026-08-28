import sqlite3

from quant_brain.data.dataset_registry import register_price_dataset, scan_parquet_metadata
from quant_brain.data.price_data import normalize_ohlcv, save_price_data
from quant_brain.db.init_db import init_database

import pandas as pd


def sample_prices():
    return pd.DataFrame(
        {
            "Open": [100.0, 101.0, 102.0],
            "High": [101.0, 102.0, 103.0],
            "Low": [99.0, 100.0, 101.0],
            "Close": [100.5, 101.5, 102.5],
            "Adj Close": [100.4, 101.4, 102.4],
            "Volume": [1000, 1100, 1200],
        },
        index=pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]),
    )


def test_scan_parquet_metadata_reads_saved_price_file(tmp_path):
    normalized = normalize_ohlcv(sample_prices(), symbol="SPY")
    saved = save_price_data(normalized, "SPY", "yfinance", "1d", tmp_path)

    metadata = scan_parquet_metadata(saved["path"])

    assert metadata["symbol"] == "SPY"
    assert metadata["source"] == "yfinance"
    assert metadata["timeframe"] == "1d"
    assert metadata["start_date"] == "2024-01-02"
    assert metadata["end_date"] == "2024-01-04"
    assert metadata["path"] == saved["path"]
    assert metadata["checksum"] == saved["checksum"]


def test_register_price_dataset_upserts_database_row(tmp_path):
    db_path = tmp_path / "brain.sqlite"
    init_database(db_path)
    normalized = normalize_ohlcv(sample_prices(), symbol="SPY")
    saved = save_price_data(normalized, "SPY", "yfinance", "1d", tmp_path)

    first_id = register_price_dataset(db_path, saved)
    second_id = register_price_dataset(db_path, saved)

    assert first_id == saved["dataset_id"]
    assert second_id == saved["dataset_id"]

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("select dataset_id, symbol, source, timeframe, path from price_datasets").fetchall()

    assert rows == [
        (saved["dataset_id"], "SPY", "yfinance", "1d", saved["path"])
    ]

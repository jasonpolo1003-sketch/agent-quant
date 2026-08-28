from pathlib import Path

import pandas as pd
import pytest

from quant_brain.data.price_data import (
    build_dataset_id,
    normalize_ohlcv,
    save_price_data,
    validate_ohlcv,
)


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


def test_build_dataset_id_is_stable_and_readable():
    assert build_dataset_id("spy", "yfinance", "1d", "2020-01-01", "2024-01-01") == (
        "yfinance_SPY_1d_2020-01-01_2024-01-01"
    )


def test_normalize_ohlcv_outputs_standard_columns():
    normalized = normalize_ohlcv(sample_prices(), symbol="SPY")

    assert list(normalized.columns) == [
        "date",
        "symbol",
        "open",
        "high",
        "low",
        "close",
        "adj_close",
        "volume",
    ]
    assert normalized.loc[0, "symbol"] == "SPY"
    assert str(normalized.loc[0, "date"].date()) == "2024-01-02"


def test_validate_ohlcv_rejects_missing_required_columns():
    bad = sample_prices().drop(columns=["Close"])

    with pytest.raises(ValueError, match="missing required columns"):
        validate_ohlcv(bad)


def test_validate_ohlcv_rejects_bad_high_low_relationship():
    bad = sample_prices()
    bad.loc[bad.index[0], "High"] = 98.0

    with pytest.raises(ValueError, match="high below low"):
        validate_ohlcv(bad)


def test_save_price_data_writes_parquet_and_returns_metadata(tmp_path):
    normalized = normalize_ohlcv(sample_prices(), symbol="SPY")

    metadata = save_price_data(
        normalized,
        symbol="SPY",
        source="yfinance",
        timeframe="1d",
        output_dir=tmp_path,
    )

    path = Path(metadata["path"])
    assert path.exists()
    assert path.suffix == ".parquet"
    assert metadata["rows"] == 3
    assert metadata["symbol"] == "SPY"
    assert metadata["start_date"] == "2024-01-02"
    assert metadata["end_date"] == "2024-01-04"

    loaded = pd.read_parquet(path)
    assert len(loaded) == 3
    assert loaded.loc[0, "symbol"] == "SPY"

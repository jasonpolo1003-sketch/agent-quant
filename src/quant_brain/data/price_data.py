from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import yfinance as yf

from quant_brain.config import DATA_DIR, DEFAULT_SYMBOLS

REQUIRED_RAW_COLUMNS = {"Open", "High", "Low", "Close", "Volume"}
STANDARD_COLUMNS = ["date", "symbol", "open", "high", "low", "close", "adj_close", "volume"]


def build_dataset_id(symbol: str, source: str, timeframe: str, start: str, end: str) -> str:
    """Return a stable readable ID for a cached price dataset."""
    return f"{source}_{symbol.upper()}_{timeframe}_{start}_{end}"


def validate_ohlcv(df: pd.DataFrame) -> None:
    """Validate raw OHLCV data before it is saved."""
    missing = REQUIRED_RAW_COLUMNS.difference(df.columns)
    if missing:
        raise ValueError(f"missing required columns: {sorted(missing)}")
    if df.empty:
        raise ValueError("price data is empty")
    if df.index.has_duplicates:
        raise ValueError("price data has duplicate timestamps")
    if df["High"].lt(df["Low"]).any():
        raise ValueError("high below low")
    if df[["Open", "High", "Low", "Close"]].isna().any().any():
        raise ValueError("OHLC price data contains missing values")
    if df["Volume"].isna().any():
        raise ValueError("volume data contains missing values")


def normalize_ohlcv(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Convert yfinance-style OHLCV data to the project standard format."""
    working = df.copy()

    # yfinance can return MultiIndex columns even for one ticker in recent versions.
    # Example: ('Close', 'SPY') should become 'Close'.
    if isinstance(working.columns, pd.MultiIndex):
        working.columns = [col[0] for col in working.columns]

    validate_ohlcv(working)

    if "Adj Close" not in working.columns:
        working["Adj Close"] = working["Close"]

    normalized = working.reset_index()
    date_col = "Date" if "Date" in normalized.columns else normalized.columns[0]
    normalized = normalized.rename(
        columns={
            date_col: "date",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Adj Close": "adj_close",
            "Volume": "volume",
        }
    )
    normalized["symbol"] = symbol.upper()
    normalized = normalized[STANDARD_COLUMNS]
    normalized["date"] = pd.to_datetime(normalized["date"]).dt.tz_localize(None)
    return normalized.sort_values("date").reset_index(drop=True)


def dataframe_checksum(df: pd.DataFrame) -> str:
    """Hash a dataframe's stable CSV representation for reproducibility tracking."""
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    return hashlib.sha256(csv_bytes).hexdigest()


def save_price_data(
    df: pd.DataFrame,
    symbol: str,
    source: str,
    timeframe: str,
    output_dir: str | Path = DATA_DIR / "parquet",
) -> dict[str, object]:
    """Save normalized price data to Parquet and return metadata."""
    if df.empty:
        raise ValueError("cannot save empty price data")

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    start_date = str(pd.to_datetime(df["date"].min()).date())
    end_date = str(pd.to_datetime(df["date"].max()).date())
    dataset_id = build_dataset_id(symbol, source, timeframe, start_date, end_date)
    path = out_dir / f"{dataset_id}.parquet"
    df.to_parquet(path, index=False)

    return {
        "dataset_id": dataset_id,
        "symbol": symbol.upper(),
        "source": source,
        "timeframe": timeframe,
        "start_date": start_date,
        "end_date": end_date,
        "rows": int(len(df)),
        "path": str(path),
        "checksum": dataframe_checksum(df),
    }


def download_yfinance_symbol(
    symbol: str,
    start: str = "2010-01-01",
    end: str | None = None,
    interval: str = "1d",
    auto_adjust: bool = False,
) -> pd.DataFrame:
    """Download one symbol from yfinance and normalize it."""
    raw = yf.download(
        symbol,
        start=start,
        end=end,
        interval=interval,
        auto_adjust=auto_adjust,
        progress=False,
        threads=False,
    )
    return normalize_ohlcv(raw, symbol=symbol)


def download_and_cache_symbols(
    symbols: list[str] | None = None,
    start: str = "2010-01-01",
    end: str | None = None,
    interval: str = "1d",
    output_dir: str | Path = DATA_DIR / "parquet",
) -> list[dict[str, object]]:
    """Download symbols from yfinance and save each as a Parquet dataset."""
    results = []
    for symbol in symbols or DEFAULT_SYMBOLS:
        data = download_yfinance_symbol(symbol, start=start, end=end, interval=interval)
        results.append(
            save_price_data(
                data,
                symbol=symbol,
                source="yfinance",
                timeframe=interval,
                output_dir=output_dir,
            )
        )
    return results

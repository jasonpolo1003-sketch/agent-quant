from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from quant_brain.data.price_data import build_dataset_id, dataframe_checksum
from quant_brain.db.init_db import DEFAULT_DB_PATH, connect, init_database


def scan_parquet_metadata(path: str | Path, source: str = "yfinance", timeframe: str = "1d") -> dict[str, Any]:
    """Read a normalized price Parquet file and return registry metadata."""
    parquet_path = Path(path)
    df = pd.read_parquet(parquet_path)
    required = {"date", "symbol", "open", "high", "low", "close", "adj_close", "volume"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"price parquet missing required columns: {sorted(missing)}")
    if df.empty:
        raise ValueError(f"price parquet is empty: {parquet_path}")

    symbols = sorted(set(df["symbol"].astype(str).str.upper()))
    if len(symbols) != 1:
        raise ValueError(f"expected one symbol per parquet file, found: {symbols}")

    symbol = symbols[0]
    start_date = str(pd.to_datetime(df["date"].min()).date())
    end_date = str(pd.to_datetime(df["date"].max()).date())
    dataset_id = build_dataset_id(symbol, source, timeframe, start_date, end_date)
    checksum = dataframe_checksum(df)

    return {
        "dataset_id": dataset_id,
        "symbol": symbol,
        "source": source,
        "timeframe": timeframe,
        "start_date": start_date,
        "end_date": end_date,
        "adjusted": 1,
        "path": str(parquet_path),
        "checksum": checksum,
        "rows": int(len(df)),
    }


def register_price_dataset(db_path: str | Path, metadata: dict[str, Any]) -> str:
    """Upsert one price dataset metadata record into SQLite."""
    init_database(db_path)
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO price_datasets (
                dataset_id, symbol, source, timeframe, start_date, end_date,
                adjusted, path, checksum
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(dataset_id) DO UPDATE SET
                symbol = excluded.symbol,
                source = excluded.source,
                timeframe = excluded.timeframe,
                start_date = excluded.start_date,
                end_date = excluded.end_date,
                adjusted = excluded.adjusted,
                path = excluded.path,
                checksum = excluded.checksum
            """,
            (
                metadata["dataset_id"],
                metadata["symbol"],
                metadata["source"],
                metadata["timeframe"],
                metadata["start_date"],
                metadata["end_date"],
                int(metadata.get("adjusted", 1)),
                metadata["path"],
                metadata.get("checksum"),
            ),
        )
        conn.commit()
    return str(metadata["dataset_id"])


def register_parquet_directory(
    db_path: str | Path = DEFAULT_DB_PATH,
    parquet_dir: str | Path = Path("data/parquet"),
    source: str = "yfinance",
    timeframe: str = "1d",
) -> list[dict[str, Any]]:
    """Scan a directory of normalized Parquet files and register them."""
    directory = Path(parquet_dir)
    records = []
    for path in sorted(directory.glob("*.parquet")):
        metadata = scan_parquet_metadata(path, source=source, timeframe=timeframe)
        register_price_dataset(db_path, metadata)
        records.append(metadata)
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Register cached Parquet price datasets in SQLite.")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--parquet-dir", default="data/parquet")
    parser.add_argument("--source", default="yfinance")
    parser.add_argument("--timeframe", default="1d")
    args = parser.parse_args()

    records = register_parquet_directory(
        db_path=args.db,
        parquet_dir=args.parquet_dir,
        source=args.source,
        timeframe=args.timeframe,
    )
    print(json.dumps(records, indent=2))


if __name__ == "__main__":
    main()

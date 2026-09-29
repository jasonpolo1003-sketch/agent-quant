"""Daily price datasets: validated, immutable, manifest-backed (Gate F).

Plan: ``brain/_system/plan/gate_f_market_data.md``. Every download becomes a
new dataset. It is accepted only when its Parquet file, its committed
manifest and its ``price_datasets`` row all agree, and only accepted datasets
can be loaded. Writing follows a fixed order -- verified Parquet, then the
manifest, then the DB row last -- so an interruption leaves an artifact the
read-only verifier reports as ``incomplete`` or ``unregistered``, never a DB
row pointing at unverified data.

Price basis: with ``auto_adjust=False`` Yahoo returns *split-adjusted* OHLC
(not the as-traded tape) and a separate ``Adj Close`` that also removes
dividends. Both are stored; ``adj_close / close`` is Yahoo's dividend factor.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PARQUET_DIR = "data/parquet"
MANIFEST_DIR = "data/manifests"
TIMEFRAME = "1d"
SCHEMA_VERSION = 1
COLUMNS = (
    "date", "open", "high", "low", "close", "adj_close", "volume", "dividends", "stock_splits",
)
PRICES = ("open", "high", "low", "close", "adj_close")
PRICE_BASIS = "yahoo_split_adjusted"
PRICE_BASIS_NOTE = (
    "open/high/low/close are Yahoo's split-adjusted prices (auto_adjust=False), not the "
    "as-traded historical tape, and volume is split-adjusted too; a backtest must state "
    "which basis it executes on"
)
ADJUSTMENT_NOTE = (
    "adj_close is Yahoo's split-and-dividend-adjusted close; adj_close / close is Yahoo's "
    "dividend adjustment factor, applied to open/high/low to derive adjusted OHLC"
)
DATE_NOTE = "dates are the exchange's trading dates (US/Eastern), not UTC"
EXCHANGE_TZ = "America/New_York"
MAX_ADJ_FACTOR = 1.0001
GAP_WARNING_WEEKDAYS = 4
MOVE_WARNING = 0.25

_RENAME = {
    "Date": "date", "Open": "open", "High": "high", "Low": "low", "Close": "close",
    "Adj Close": "adj_close", "Volume": "volume", "Dividends": "dividends",
    "Stock Splits": "stock_splits",
}


class MarketDataError(ValueError):
    """A dataset is invalid, incomplete, or cannot be accepted or loaded."""


@dataclass
class DatasetReport:
    dataset_id: str
    state: str  # accepted | unregistered | incomplete | invalid
    path: str | None = None
    problems: list[str] = field(default_factory=list)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# --- shape and validation ------------------------------------------------------------


def normalize_bars(frame: pd.DataFrame) -> pd.DataFrame:
    """Yahoo-shaped (or already-normalized) bars as ``COLUMNS``, one row per trading date."""
    data = frame.copy()
    if isinstance(data.index, pd.DatetimeIndex):
        index = data.index
        # Yahoo's daily index is midnight exchange time; keep its local date.
        data = data.reset_index(drop=True)
        data.insert(0, "date", index.strftime("%Y-%m-%d"))
    data = data.rename(columns=_RENAME)
    for column in ("dividends", "stock_splits"):
        if column not in data:
            data[column] = 0.0
    missing = [column for column in COLUMNS if column not in data]
    if missing:
        raise MarketDataError(f"bars are missing columns: {missing}")
    data = data[list(COLUMNS)].reset_index(drop=True)
    data["date"] = pd.to_datetime(data["date"]).dt.strftime("%Y-%m-%d")
    for column in (*PRICES, "dividends", "stock_splits"):
        data[column] = pd.to_numeric(data[column], errors="coerce").astype("float64")
    data["volume"] = pd.to_numeric(data["volume"], errors="coerce").astype("float64")
    return data


def validate_bars(frame: pd.DataFrame) -> tuple[list[str], list[str]]:
    """Deterministic checks: impossible bars are problems, suspicious ones warnings."""
    problems: list[str] = []
    warnings: list[str] = []
    dates = frame["date"]

    def rows(mask: pd.Series) -> str:
        return ", ".join(dates[mask].astype(str).head(5))

    for column in (*PRICES, "volume"):
        if frame[column].isna().any():
            problems.append(f"missing {column} on {rows(frame[column].isna())}")
    if dates.duplicated().any():
        problems.append(f"duplicate dates: {rows(dates.duplicated())}")
    if not dates.is_monotonic_increasing:
        problems.append("unsorted dates")
    prices = frame[list(PRICES)]
    if (prices <= 0).any().any():
        problems.append(f"non-positive prices on {rows((prices <= 0).any(axis=1))}")
    body_high = frame[["open", "close"]].max(axis=1)
    body_low = frame[["open", "close"]].min(axis=1)
    if (frame["high"] < body_high).any():
        problems.append(f"high below open/close on {rows(frame['high'] < body_high)}")
    if (frame["low"] > body_low).any():
        problems.append(f"low above open/close on {rows(frame['low'] > body_low)}")
    if (frame["volume"] < 0).any():
        problems.append(f"negative volume on {rows(frame['volume'] < 0)}")
    for column in ("dividends", "stock_splits"):
        if frame[column].isna().any():
            problems.append(f"missing {column} on {rows(frame[column].isna())}")
        if (frame[column] < 0).any():
            problems.append(f"negative {column} on {rows(frame[column] < 0)}")
    weekend = pd.to_datetime(dates, errors="coerce").dt.dayofweek >= 5
    if weekend.any():
        problems.append(f"weekend dates: {rows(weekend)}")
    factor = frame["adj_close"] / frame["close"]
    bad_factor = (factor <= 0) | (factor > MAX_ADJ_FACTOR)
    if bad_factor.any():
        problems.append(f"dividend factor out of range (0, {MAX_ADJ_FACTOR}] on {rows(bad_factor)}")

    if not problems:
        parsed = pd.to_datetime(dates).to_numpy(dtype="datetime64[D]")
        missing_weekdays = np.busday_count(parsed[:-1], parsed[1:]) - 1
        for position in np.flatnonzero(missing_weekdays > GAP_WARNING_WEEKDAYS):
            warnings.append(
                f"gap of {missing_weekdays[position]} weekdays after {dates.iloc[position]}"
            )
        if (frame["volume"] == 0).any():
            warnings.append(f"zero volume on {rows(frame['volume'] == 0)}")
        moves = frame["adj_close"].pct_change().abs()
        if (moves > MOVE_WARNING).any():
            warnings.append(f"daily move above {MOVE_WARNING:.0%} on {rows(moves > MOVE_WARNING)}")
    return problems, warnings


def canonical_content_hash(frame: pd.DataFrame) -> str:
    """sha256 of the values in a fixed text form, independent of Parquet encoding."""
    data = normalize_bars(frame)
    lines = [",".join(COLUMNS)]
    for row in data.itertuples(index=False):
        lines.append(",".join([row.date, *(repr(float(value)) for value in row[1:])]))
    return _sha256(("\n".join(lines) + "\n").encode("utf-8"))


def new_dataset_id(symbol: str, now: datetime, run_id: str | None = None) -> str:
    stamp = now.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{symbol}-{TIMEFRAME}-yfinance-{stamp}-{run_id or secrets.token_hex(4)}"


# --- the ordered write ---------------------------------------------------------------


def _write_partial_parquet(root: Path, relative: str, frame: pd.DataFrame, content: str) -> Path:
    final = root / relative
    partial = final.with_name(final.name + ".partial")
    if final.exists() or partial.exists():
        raise MarketDataError(f"{relative} already exists; datasets are never overwritten")
    partial.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(partial, index=False)
    if canonical_content_hash(pd.read_parquet(partial)) != content:
        raise MarketDataError(f"{partial.name} does not read back as written")
    return partial


def _finalise_parquet(partial: Path, final: Path) -> None:
    if final.exists():
        raise MarketDataError(f"{final.name} already exists; datasets are never overwritten")
    os.rename(partial, final)


def _write_manifest(root: Path, manifest: dict[str, Any]) -> None:
    final = root / MANIFEST_DIR / f"{manifest['dataset_id']}.json"
    if final.exists():
        raise MarketDataError(f"{final.name} already exists; manifests are never overwritten")
    final.parent.mkdir(parents=True, exist_ok=True)
    temporary = final.with_name(final.name + ".tmp")
    temporary.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    os.rename(temporary, final)


def register_dataset(db_path: str | Path, manifest: dict[str, Any]) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO price_datasets (dataset_id, symbol, source, timeframe, start_date, "
            "end_date, adjusted, path, checksum) VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)",
            (
                manifest["dataset_id"], manifest["symbol"], manifest["provider"],
                manifest["timeframe"], manifest["first_date"], manifest["last_date"],
                manifest["path"], manifest["content_sha256"],
            ),
        )


def cross_check(
    frame: pd.DataFrame, symbol: str, fetcher: Callable[[str, str, str], pd.Series] | None
) -> dict[str, Any]:
    """Compare daily adjusted returns with a second source. Report only, never a gate."""
    if fetcher is None:
        return {"status": "not_run"}
    try:
        other = pd.Series(fetcher(symbol, frame["date"].iloc[0], frame["date"].iloc[-1]))
        other.index = pd.to_datetime(other.index).tz_localize(None).normalize()
        ours = pd.Series(frame["adj_close"].to_numpy(), index=pd.to_datetime(frame["date"]))
        returns = pd.concat(
            [ours.sort_index().pct_change(), other.sort_index().pct_change()], axis=1, join="inner"
        ).dropna()
        if returns.empty:
            return {"status": "unavailable", "reason": "no overlapping dates"}
        return {
            "status": "compared",
            "source": getattr(fetcher, "source", "second source"),
            "overlap_days": len(returns),
            "return_correlation": float(returns.iloc[:, 0].corr(returns.iloc[:, 1])),
            "max_abs_return_diff": float((returns.iloc[:, 0] - returns.iloc[:, 1]).abs().max()),
        }
    except Exception as exc:  # a second source failing never blocks the dataset
        return {"status": "unavailable", "reason": f"{type(exc).__name__}: {exc}"}


def ingest(
    project_root: str | Path,
    db_path: str | Path,
    symbol: str,
    frame: pd.DataFrame,
    *,
    meta: dict[str, Any],
    now: datetime | None = None,
    cross_check_fetcher: Callable[[str, str, str], pd.Series] | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Validate and store one download as a new accepted dataset, in the fixed order."""
    root = Path(project_root)
    data = normalize_bars(frame)
    problems, warnings = validate_bars(data)
    if problems:
        raise MarketDataError(f"{symbol}: refused: " + "; ".join(problems))
    when = now or datetime.now(UTC)
    # Only completed sessions: the download day's bar may still be forming.
    exchange_today = pd.Timestamp(when).tz_convert(EXCHANGE_TZ).strftime("%Y-%m-%d")
    if data["date"].iloc[-1] >= exchange_today:
        raise MarketDataError(
            f"{symbol}: refused: last bar {data['date'].iloc[-1]} is not before the download "
            f"day {exchange_today} ({EXCHANGE_TZ}) and may be incomplete; fetch with an "
            "earlier end date"
        )
    dataset_id = new_dataset_id(symbol, when, run_id)
    relative = f"{PARQUET_DIR}/{symbol}/{dataset_id}.parquet"
    content = canonical_content_hash(data)

    partial = _write_partial_parquet(root, relative, data, content)
    _finalise_parquet(partial, root / relative)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "dataset_id": dataset_id,
        "symbol": symbol,
        "timeframe": TIMEFRAME,
        **{key: meta[key] for key in ("provider", "provider_version", "requested_start",
                                      "requested_end")},
        "downloaded_at": when.astimezone(UTC).isoformat(),
        "path": relative,
        "rows": len(data),
        "first_date": data["date"].iloc[0],
        "last_date": data["date"].iloc[-1],
        "columns": list(COLUMNS),
        "price_basis": PRICE_BASIS,
        "price_basis_note": PRICE_BASIS_NOTE,
        "adjustment_note": ADJUSTMENT_NOTE,
        "date_note": DATE_NOTE,
        "warnings": warnings,
        "content_sha256": content,
        "file_sha256": _sha256((root / relative).read_bytes()),
        "cross_check": cross_check(data, symbol, cross_check_fetcher),
    }
    _write_manifest(root, manifest)
    # The row goes in last, and only for a dataset that verifies as written.
    problems = _verify_files(root, manifest)
    if problems:
        raise MarketDataError(f"{dataset_id}: not registered: " + "; ".join(problems))
    register_dataset(db_path, manifest)
    return manifest


# --- read-only verification and loading ----------------------------------------------


def _verify_files(root: Path, manifest: dict[str, Any]) -> list[str]:
    path = root / manifest["path"]
    if not path.is_file():
        return [f"{manifest['path']} is missing"]
    problems = []
    if _sha256(path.read_bytes()) != manifest["file_sha256"]:
        problems.append("file sha256 differs from the manifest")
    if canonical_content_hash(pd.read_parquet(path)) != manifest["content_sha256"]:
        problems.append("content sha256 differs from the manifest")
    return problems


def _db_rows(db_path: str | Path) -> dict[str, dict[str, Any]]:
    path = Path(db_path)
    if not path.is_file():
        return {}
    with sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True) as conn:
        conn.row_factory = sqlite3.Row
        try:
            return {row["dataset_id"]: dict(row) for row in conn.execute("SELECT * FROM price_datasets")}
        except sqlite3.OperationalError:
            return {}


def _row_problems(row: dict[str, Any], manifest: dict[str, Any]) -> list[str]:
    expected = {
        "symbol": manifest["symbol"], "source": manifest["provider"],
        "timeframe": manifest["timeframe"], "start_date": manifest["first_date"],
        "end_date": manifest["last_date"], "adjusted": 0, "path": manifest["path"],
        "checksum": manifest["content_sha256"],
    }
    return [f"db {key} is {row.get(key)!r}, manifest says {value!r}"
            for key, value in expected.items() if row.get(key) != value]


def verify_datasets(project_root: str | Path, db_path: str | Path) -> list[DatasetReport]:
    """Classify every dataset artifact found on disk or in the DB. Never writes."""
    root = Path(project_root)
    rows = _db_rows(db_path)
    manifests: dict[str, dict[str, Any]] = {}
    unreadable: dict[str, str] = {}
    if (root / MANIFEST_DIR).is_dir():
        for path in sorted((root / MANIFEST_DIR).glob("*.json")):
            try:
                manifests[path.stem] = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                unreadable[path.stem] = f"unreadable manifest: {type(exc).__name__}: {exc}"
    files: dict[str, str] = {}
    partials: dict[str, str] = {}
    parquet_root = root / PARQUET_DIR
    if parquet_root.is_dir():
        for path in parquet_root.rglob("*.parquet"):
            files[path.name.removesuffix(".parquet")] = path.relative_to(root).as_posix()
        for path in parquet_root.rglob("*.parquet.partial"):
            partials[path.name.removesuffix(".parquet.partial")] = path.relative_to(root).as_posix()

    reports = []
    for dataset_id in sorted(set(rows) | set(manifests) | set(files) | set(partials) | set(unreadable)):
        manifest, row = manifests.get(dataset_id), rows.get(dataset_id)
        if dataset_id in unreadable:
            reports.append(DatasetReport(dataset_id, "invalid", files.get(dataset_id),
                                         [unreadable[dataset_id]]))
            continue
        if manifest is None:
            if row is not None:
                reports.append(DatasetReport(dataset_id, "invalid", row.get("path"),
                                             ["db row without a manifest"]))
            else:
                reports.append(DatasetReport(
                    dataset_id, "incomplete", files.get(dataset_id) or partials.get(dataset_id),
                    ["no manifest: the write did not finish"],
                ))
            continue
        problems = _verify_files(root, manifest)
        if row is not None:
            problems += _row_problems(row, manifest)
        if problems:
            state = "invalid"
        elif row is None:
            state, problems = "unregistered", ["verified files, but no db row"]
        else:
            state = "accepted"
        reports.append(DatasetReport(dataset_id, state, manifest["path"], problems))
    return reports


def load_dataset(project_root: str | Path, db_path: str | Path, dataset_id: str) -> pd.DataFrame:
    """Bars of an accepted dataset only, with derived dividend-adjusted OHLC."""
    reports = {r.dataset_id: r for r in verify_datasets(project_root, db_path)}
    report = reports.get(dataset_id)
    if report is None or report.state != "accepted":
        state = report.state if report else "unknown"
        detail = "; ".join(report.problems) if report else "not found"
        raise MarketDataError(f"{dataset_id} is {state}, not loadable: {detail}")
    frame = pd.read_parquet(Path(project_root) / report.path)
    factor = frame["adj_close"] / frame["close"]
    for column in ("open", "high", "low"):
        frame[f"adj_{column}"] = frame[column] * factor
    return frame

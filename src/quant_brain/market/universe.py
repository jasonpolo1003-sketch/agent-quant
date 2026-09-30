"""Universe lists and the latest accepted daily dataset for each symbol.

A universe is a committed JSON list in ``data/universe/<name>.json``. Prices
come only from accepted Gate F datasets: every artifact is verified once, then
the newest accepted download per symbol is read, with the same derived
dividend-adjusted OHLC as ``load_dataset``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from quant_brain.data.market_data import MANIFEST_DIR, verify_datasets

UNIVERSE_DIR = "data/universe"


def load_universe(project_root: str | Path, name: str = "starter") -> dict[str, Any]:
    return json.loads((Path(project_root) / UNIVERSE_DIR / f"{name}.json").read_text(encoding="utf-8"))


def latest_accepted(project_root: str | Path, db_path: str | Path) -> dict[str, dict[str, Any]]:
    """Manifest of the newest accepted dataset per symbol (verified once, read-only)."""
    root = Path(project_root)
    latest: dict[str, dict[str, Any]] = {}
    for report in verify_datasets(root, db_path):
        if report.state != "accepted":
            continue
        manifest = json.loads((root / MANIFEST_DIR / f"{report.dataset_id}.json").read_text(encoding="utf-8"))
        current = latest.get(manifest["symbol"])
        if current is None or manifest["downloaded_at"] > current["downloaded_at"]:
            latest[manifest["symbol"]] = manifest
    return latest


def read_frame(project_root: str | Path, manifest: dict[str, Any]) -> pd.DataFrame:
    frame = pd.read_parquet(Path(project_root) / manifest["path"])
    factor = frame["adj_close"] / frame["close"]
    for column in ("open", "high", "low"):
        frame[f"adj_{column}"] = frame[column] * factor
    return frame.sort_values("date").reset_index(drop=True)


def provenance(manifest: dict[str, Any]) -> dict[str, Any]:
    """The badge the terminal shows next to any number built from this dataset."""
    return {
        "dataset_id": manifest["dataset_id"], "source": manifest["provider"],
        "freshness": "END OF DAY", "last_date": manifest["last_date"],
        "downloaded_at": manifest["downloaded_at"], "price_basis": manifest["price_basis"],
        "content_sha256": manifest["content_sha256"], "warnings": manifest["warnings"],
        "terms": "Yahoo Finance data via yfinance: personal use only",
    }

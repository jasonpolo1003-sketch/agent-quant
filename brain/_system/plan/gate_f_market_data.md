---
id: gate_f_market_data
type: phase_plan
status: approved
created: 2026-09-28
parent: PROP-007 step 3
---

# Gate F — Local market data with provenance

## Goal
Reproducible, verified daily price history for **SPY, QQQ and IWM**, stored locally, so the first strategy can be backtested. No strategy, signal or backtest work happens in this step.

## Current state
- `price_datasets` exists in the SQLite schema but has 0 rows.
- No data module exists. Earlier handoff claims of a downloader were not true of the reconciled tree.
- `pandas`, `pyarrow`, `duckdb`, `yfinance` and `pandas-datareader` are already dependencies, so **none are added**.
- `data/parquet/` and `db/*.sqlite` are gitignored, so the data files are not in git. A **committed manifest** per dataset is the reproducible, checkable record.

## Design

### Module `src/quant_brain/data/market_data.py` (new, small)
1. `fetch_daily(symbol, start, end, *, fetcher)`
   - The fetcher is injected, so tests never use the network.
   - The live fetcher is yfinance with `auto_adjust=False, actions=True`.
   - It returns **Yahoo's split-adjusted OHLC** and Volume, plus `Adj Close`, Dividends and Stock Splits.
   - With `auto_adjust=False`, Yahoo's OHLC is *not* necessarily the original, as-traded, pre-split series: Yahoo back-adjusts it for splits.
   - The manifest records `price_basis: "yahoo_split_adjusted"`. A later backtest must state which basis it executes on.
2. `validate_bars(frame) -> problems, warnings`, deterministic.
   - **Problems** (fail closed):
     - dates unsorted or duplicated;
     - missing OHLC values;
     - any price ≤ 0;
     - `High < max(Open, Close)` or `Low > min(Open, Close)`;
     - negative volume;
     - an adjustment factor (`Adj Close / Close`) ≤ 0 or > 1.0001.
   - **Warnings** (recorded, not fatal):
     - a gap of more than 4 weekdays;
     - zero-volume days;
     - a daily move above 25%.
3. `save_dataset(frame, meta)`
   - Writes **immutable** Parquet: `data/parquet/<symbol>/<dataset_id>.parquet`, and never overwrites.
   - **Every download is a new dataset**, even with identical data on the same day: `dataset_id = <SYMBOL>-1d-yfinance-<UTC timestamp YYYYMMDDTHHMMSSZ>-<random run id, 8 hex>`.
   - The **full** content sha256 is kept in the manifest, so identical downloads can be recognised by comparing hashes, never by ID.
   - Re-downloads matter because Yahoo restates adjusted history over time.
4. Committed manifest `data/manifests/<dataset_id>.json`, recording:
   - symbol, provider, provider library version, requested range, actual first and last dates, row count and columns;
   - the price basis and adjustment method: Yahoo split-adjusted OHLC is stored, with Yahoo's dividend-adjustment factor `adj_factor = Adj Close / Close` per row, so dividend-and-split-adjusted OHLC can be derived. Neither series is the as-traded tape;
   - a timezone note: dates are the exchange's trading dates;
   - the download time (UTC) and the validation warnings;
   - **two hashes**: the Parquet file bytes, and a canonical content hash (a fixed-format CSV of the rows). The content hash survives a pyarrow upgrade that changes the file bytes.
5. `register_dataset(db, manifest)`: inserts into the existing `price_datasets` (`adjusted = 0`, meaning split-adjusted OHLC stored plus a dividend factor; path; content hash as checksum). **No schema change.** The full detail stays in the manifest.
6. `load_dataset(dataset_id)`
   - Loads **accepted datasets only** (see the next section).
   - Re-verifies both hashes before returning data, and fails closed otherwise.
   - Returns the split-adjusted and the dividend-adjusted columns.

### Partial failure: what counts as accepted
Saving is a fixed sequence. Each step happens only if the previous one verified:
1. Write the Parquet file to `<id>.parquet.partial`, re-read it, and hash it.
2. Rename it to `<id>.parquet`. The name is new, so nothing is overwritten.
3. Run the Stooq cross-check. **This is not a gate:** a failure is recorded as `cross_check: unavailable` and does not block.
4. Write the manifest: temp file, then rename. **The manifest is written only after the Parquet file verifies against it.**
5. Insert the DB row **last**, only after the manifest and file re-verify together. **A DB row never points at an unverified or half-written dataset.**

A dataset is **accepted only if** its manifest exists and verifies against its Parquet file, **and** its DB row exists and matches the manifest. The read-only verifier classifies everything it finds:

| Found | State | Loadable |
|---|---|---|
| `*.parquet.partial`, or `.parquet` with no manifest | `incomplete` | no |
| manifest verifies, no DB row | `unregistered` | no |
| hash mismatch, DB row without manifest, or DB row ≠ manifest | `invalid`; the verifier exits non-zero | no |
| manifest + file + DB row all agree | `accepted` | yes |

Nothing is deleted automatically. Incomplete or unregistered artifacts are reported for a manual decision. A retry is simply a new download with a new ID.

### Command-line tool `scripts/fetch_market_data.py`
- `uv run python scripts/fetch_market_data.py --symbols SPY QQQ IWM --start 2000-01-01`
- This is the **only** code that uses the network.
- It prints, per symbol: rows, date range, warnings and the dataset ID.
- `scripts/verify_market_data.py` (read-only) re-checks every manifest against its file and its DB row.

### Second-source cross-check (report only, not a gate)
- Stooq via the already-installed `pandas-datareader`, for the same symbols.
- Compare daily adjusted-close returns over the overlapping period (correlation and largest difference), and record the result in the manifest.
- This catches a bad or stale Yahoo series cheaply. If Stooq is unavailable, it is recorded as "not cross-checked".

## Tests (hermetic, deliberately light)
- A small committed CSV fixture of about 30 real-shaped rows, with one dividend and one split.
- Validation catches each problem class, and warnings are recorded.
- Save is immutable: a second save of identical data on the same day gets a **different** ID, leaves the first untouched, and shares its content hash.
- An interruption at each step leaves the expected state (`incomplete` or `unregistered`), and neither is loadable. A DB row that disagrees with its manifest is `invalid`.
- Load verifies both hashes, and a tampered file fails closed.
- The manifest and DB registration round-trip.
- The adjusted-price derivation matches `Adj Close`.
- The injected fetcher means no network in pytest.

## Verification
1. Full test suite and both Ruff checks.
2. **One live download** of SPY, QQQ and IWM, the only network step, plus the Stooq cross-check.
3. `verify_market_data.py` exits 0.
4. A summary of rows, date ranges, warnings and cross-check agreement, reported to Jason.
5. Commit the code, tests and manifests. The Parquet files stay local and gitignored, and are verifiable through the manifests.

## Out of scope
Strategy cards, signals, backtests, intraday data, other symbols, paid data, a schema migration, and any change to the frozen research harness.

## Known limitations
- yfinance is an unofficial Yahoo interface. It can break or restate history, which is why datasets are immutable and versioned.
- Yahoo's `Adj Close` handles dividends and splits in Yahoo's own way. The plan documents that method; it does not re-derive total return independently. Stooq is only a cross-check.
- Survivorship bias does not apply to these three long-lived ETFs. It would matter for any later stock-picking universe.
- There is no exchange-calendar dependency: gaps are flagged heuristically, not validated against the official NYSE calendar.

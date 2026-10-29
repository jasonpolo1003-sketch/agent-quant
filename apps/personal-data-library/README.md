# Personal Data Library

A local economic-data and opted-in research workspace. It preserves official FRED bytes, cleaned Parquet and DuckDB provenance, and adds a separate SQLite Markdown intake/catalog. No paid service, account, AI, autonomous research, strategy promotion or trading integration. Scheduler capability exists but **no unattended task is activated**.

## Connected research intake

1. Copy `config/intake.example.toml` to ignored `config/intake.toml`; explicitly configure one small input directory and a separate generated output page. Optional `quant_root`/`quant_manifest` point to a reviewed, hash-bound development-metadata allowlist; start from `config/quant-artifacts.example.json` (blocked by default).
2. `uv run pdl-intake scan --dry-run` lists direct-child candidates without opening their content. Save UTF-8 Markdown (at most 2 MiB) directly in the opted-in folder. Other folders, generated outputs, URLs and attachments are not traversed/fetched/executed.
3. Run `uv run pdl-intake run-once --notes-only`; after at least one second, run it again. The first observation establishes stability; the later pass captures current saved bytes. This does not promise every keystroke. The **Process inbox now** button runs this notes-only path.
4. Open **Research library**: search/filter by title/question/strategy/source/type/status, select a retained version, inspect escaped original text and provenance, and download its exact bytes. Processing `organized` and evidence `unverified` are separate. Unknown links remain unresolved. Development references keep source-reported verdicts and identifiers without creating Quant records or aggregate trial counts.
5. `uv run pdl-intake status` shows queue, errors, retries and activity. Fix rejected inputs, rescan for stability, then `uv run pdl-intake retry ITEM_ID_OR_FILENAME`. Pause/resume future passes with `uv run pdl-intake pause` / `uv run pdl-intake resume`.

Originals are checksum-addressed under `data/research/raw/`; edits append versions and copies preserve separate occurrences. Unique same-content renames may preserve identity; ambiguous copies/renames require review. Source deletion marks unavailability without deleting retained versions. Bounded malformed notes are retained for review, never interpreted as instructions; oversized/unsupported/unavailable inputs get visible recovery reasons. Expired processing leases recover after 120 seconds. Retry backoff is bounded to three attempts before failure.

A plain `uv run pdl-intake run-once` also checks approved FRED sources if enabled in local config: successful sources are due after 24 hours, failed sources back off with at most three attempts per UTC day. No catch-up download storm. Each network child has a bounded timeout; network/parse work happens outside the numerical lock. Worker passes use a cooperative 90-second budget, one OS-backed worker lock and up to 100 candidates. Scheduling adds a hard task execution limit. SQLite uses WAL and short claims; all DuckDB connection lifetimes, including constructor writes, use the shared numerical lock. UI retains last-good session values on contention; a new uncached selection may ask you to retry.

Managed status is one-way and checksum-protected: meaningful changes only, no heartbeat churn. User-edited generated pages are preserved as conflicts. The catalog export is `data/research/exports/research-catalog.json`; the last manual receipt is `last-run.json` beside it. Status/capture times are not publication times or research approval.

### Verification and stop controls

```text
uv run pytest -q
uv run python scripts/verify_local.py
uv run python scripts/verify_intake.py
uv run --with playwright python scripts/browser_acceptance.py
uv run --with playwright python scripts/browser_intake_acceptance.py
uv run --with playwright python scripts/browser_refresh_acceptance.py
uv run pdl-intake schedule status
```

Browser drivers require a running local server and actual FRED snapshots; research browser acceptance additionally requires the explicitly opted-in two-version workflow note. Tests use temporary test-only fixtures and require no vault, real data or network. Nothing synthetic is installed as app fallback. Reports remain local runtime evidence.

`uv run pdl-intake schedule enable` refuses without explicit `--confirm-activation`. **Do not use that flag until the user separately authorizes activation.** The fixed task target is this subproject's `.venv` Python and `scripts/run_intake_once.py`, with explicit working directory, two-minute cadence, logon/catch-up settings, `IgnoreNew`, and 90-second execution limit. Readback checks drift; unknown/drifted tasks are not overwritten. `schedule disable` disables only a recognized owned task and verifies readback. Actual task registration/trigger acceptance is intentionally pending authorization; manual mode is independent of it. No operation while the computer is off is promised.

Before backup, pause intake and stop manual/UI writers. `uv run python scripts/verify_intake.py --backup-to NEW_ISOLATED_DIRECTORY` takes worker/numerical locks, backs up SQLite (including committed WAL), checkpoints/closes DuckDB and copies paired catalogs/blobs/numerical snapshots. `--data-dir RESTORED_DIRECTORY` verifies a test restore. Restore never registers a task. Preserve evidence on rollback; do not delete source notes or Quant artifacts. No automatic purge is implemented; review retained-byte totals and disk growth manually.

For publication as a standalone uv subproject inside the Quant repository and reuse of existing external runtime data, see [INTEGRATION.md](INTEGRATION.md). No Quant strategy module changes are needed.

## Economic dataset guide

## Run on Windows

Open **Command Prompt**:

```bat
cd /d C:\Users\jason\personal-data-library
run-dashboard.cmd
```

Then open **http://127.0.0.1:8501**. Close the terminal or press Ctrl+C to stop. The launcher uses the isolated `.venv`, explicitly binds to loopback, and disables Streamlit telemetry. It does not install or download anything. Cached data work offline.

For a fresh environment with [uv](https://docs.astral.sh/uv/) installed:

```bat
cd /d C:\Users\jason\personal-data-library
uv sync --python 3.13 --locked
uv run pdl-refresh
run-dashboard.cmd
```

Equivalent explicit startup:

```bat
.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true --browser.gatherUsageStats false
```

UI and CLI numerical operations now share short cross-process locks. Do not expose its port on a network. Stop all writers for backup; an uncached UI selection may ask you to retry during contention.

## A short walkthrough

1. **Economic snapshot** shows separate panels for CPI inflation, unemployment, and the effective federal funds rate. Each has its own percent axis and identical selected date range. Hover to inspect monthly values. Zoom affects one panel; sidebar dates align all three.
2. **Library & explore** lets you search name, identifier, topic, source, or definitions; filter by topic and underlying origin; then choose a dataset.
3. Read its origin, units, adjustment status, official source link, observation end date, retrieval timestamp, missingness, and limitations. FRED distributes the data; it is not a second independent origin.
4. Set **From / Through**. CPI exposes both the index level and a separately labeled year-over-year percentage. The table and **Download selected cleaned CSV** contain exactly the selected observations; CPI exports include both `value` and `yoy_pct`.
5. Expand **Snapshot provenance & version history** for checksums and file paths. Select older saved versions to inspect revisions.
6. Refresh one series or all series manually. Failures appear visibly while the previous successful data remain readable. No network calls occur merely from startup, navigation, search, or export.

## Sources and definitions

| Series | Underlying origin | Units / adjustment |
|---|---|---|
| [CPIAUCSL](https://fred.stlouisfed.org/series/CPIAUCSL) | U.S. Bureau of Labor Statistics | Index 1982–1984=100; seasonally adjusted |
| [UNRATE](https://fred.stlouisfed.org/series/UNRATE) | U.S. Bureau of Labor Statistics | Percent of civilian labor force, age 16+; seasonally adjusted |
| [FEDFUNDS](https://fred.stlouisfed.org/series/FEDFUNDS) | Board of Governors of the Federal Reserve System (US) | Percent; not seasonally adjusted; monthly effective rate, **not** the FOMC target range |

Initial collection: January 1999 onward; default display: January 2000 onward. CPI YoY is `100 * (index(month) / index(same month one calendar year earlier) - 1)`, computed before display filtering. Missing prior-year months and zero denominators produce null, not infinity or a misleading twelve-row shift. Missing source values remain null. Absent months remain absent in stored/exported observations and become gaps in charts, never invented zeros.

**Latest-available history is not point-in-time-safe backtest evidence.** Revisions, release delays, and unavailable historical vintage/availability metadata require a separate ALFRED-aware design. The dashboard does not infer a publication date from an observation date. `retrieved_at` is local UTC retrieval of the preserved response; `source_last_modified` is the source HTTP header, not a release timestamp; `source_release_at` is null because CSV does not supply reliable release times. Repeat successful checks are separately timestamped in refresh-attempt history, without changing original snapshot retrieval times.

Reviewed the official series pages and [FRED terms](https://fred.stlouisfed.org/legal/) during this build. This is local personal research, not permission for unrestricted redistribution. Review current series-specific copyright/use notes and attribution requirements before publishing or reusing data. No access controls are bypassed.

## Collection and storage

Official CSV endpoint (the working path is **fredgraph.csv**, not graph.csv):

```text
https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCSL&cosd=1999-01-01
```

The connector validates the response and tries the same official CSV endpoint without a start-date parameter if needed. A free-key API alternative is documented at https://fred.stlouisfed.org/docs/api/fred/series_observations.html and https://fred.stlouisfed.org/docs/api/api_key.html. A direct keyless request to `https://api.stlouisfed.org/fred/series/observations?series_id=UNRATE&file_type=json&observation_start=1999-01-01` returned HTTP 400, explicitly requiring `api_key`. No key was supplied or needed: official CSV downloads succeeded. API-key ingestion is not implemented in this first version; if both CSV routes fail, the app reports the failure rather than fabricating data or asking for a secret in the UI.

- `data/raw/<series>/`: exact immutable-by-application response bytes, versioned by SHA-256 plus unique publication ID.
- `data/clean/<series>/`: validated versioned Parquet, with `date` and nullable `value`.
- `data/catalog.duckdb`: searchable series metadata, snapshot provenance, active pointers, and refresh attempts. DuckDB reads the Parquet files for exploration.
- `reports/verification.json`: real local verification report with exact raw/clean paths, hashes, dates, counts and a hand-checkable CPI calculation.

New snapshots validate before publication. Staged files are closed, then atomically renamed on the same local filesystem; only after both files exist does a DuckDB transaction insert metadata and switch the active pointer. Failed publication never exposes a partial snapshot. A crash between file publication and DB commit can leave unreferenced files; these are harmless evidence, not active data. There is no automatic deletion/garbage collection. Raw files are never overwritten by this application (ordinary filesystem access can still change them; this is not tamper-proof storage). Identical raw content reuses the logical snapshot; even a publisher reversion to an earlier checksum selects the correct active version. Old successful versions are retained indefinitely.

## Refresh, test, verify

```bat
uv run pdl-refresh
uv run pytest -q
uv run python scripts/verify_local.py
```

CLI refresh prints per-series JSON and returns nonzero if any collection fails. Tests use synthetic **test-only** observations for deterministic arithmetic/validation, not as dashboard fallback data. Streamlit unit tests use isolated temporary fixtures so a source-only checkout can run offline; real local snapshots, both CSV and Markdown downloads, and browser interactions are independently exercised by the acceptance scripts. The verifier checks real saved bytes and transformations without network calls. Historical first-release build evidence is retained in [BUILD-NOTES.md](BUILD-NOTES.md).

## Backup, restore, extend

Stop all dashboard/CLI processes, then copy **the whole project**, or at minimum the whole `data` directory including `catalog.duckdb`, `raw`, and `clean`. Keep the directory structure together; stored snapshot paths are relative to `data`. Restore into the same project layout, recreate `.venv` with `uv sync --python 3.13 --locked`, then run the launcher. A copied snapshot can be read offline; avoid copying a live/open DuckDB file. `PDL_DATA_DIR` optionally selects another complete local data directory for isolated testing.

Adding a dataset is deliberate code work, not arbitrary scraping: review access/units/origin/terms; add an explicit entry in `src/data_library/metadata.py`; extend the official connector allowlist; write a failing parser/validation test before implementing any different format/frequency; verify a real download and provenance. The UI/data model currently assumes monthly month-start observations. Do not force daily, company, documents, or point-in-time data into this adapter. Search/filter controls apply to the Library; Economic snapshot intentionally always shows the three approved series.

Known limits: local-only hosting, no authentication/public exposure, scheduler activation pending, no automatic retention limit, no release calendar/availability model, no inferred causes or forecasts. Snapshots show age and failed checks rather than claiming current freshness.

## Independent browser acceptance

The parent independently reran all 18 tests and the offline verifier, then launched the dashboard bound to 127.0.0.1:8501. Headless Microsoft Edge acceptance checked all three chart panels, search, visible date-segment editing, the official source link, a real downloaded UNRATE CSV with all 12 months of 2020, the April 2020 chart hover value (14.8), and no-match search state, with no browser page errors. Both screens were visually inspected. Evidence is saved in `reports/browser-acceptance.json`, `reports/dashboard-snapshot.png`, and `reports/dashboard-library.png`.

Reproduce with the server running: `uv run --with playwright python scripts/browser_acceptance.py`. This acceptance driver uses the existing Edge executable and an isolated temporary Playwright dependency, not your browser profile or a paid service. A user walkthrough remains optional; automated/browser checks do not establish point-in-time backtest suitability.

## Data notice

This product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis.

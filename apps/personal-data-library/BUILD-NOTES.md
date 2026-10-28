# Build and verification notes

## Connected intake release — current implementation (2026-10-28)

Implemented manual Batches A–E capability in the existing standalone library. Publication into Quant `testing` under `apps/personal-data-library/` is parent-owned and not claimed complete here. The standalone library has no Git repository; the primary Quant repository was inspected clean at `2b7b07b422b97a3a492dcedb78bf6a42ea97ff1f`, with `origin` pointing to `git@github.com:jasonpolo1003-sketch/agent-quant.git`. No Quant source, strategy, ledger or database was modified; no strategy run, held-out read, trade, paid service, commit, push or PR was performed by this implementation subagent.

### Delivered behavior

- SQLite WAL catalog, transactional persistent queue/leases, exact-byte checksum blobs, edit versions, separate copy occurrences, conservative rename identity, source deletion marking, bounded stable direct-child Markdown scan, safe YAML metadata, content-only escaped preview, no note-directed URL fetching/execution.
- Research search/type/source/processing/evidence/question/strategy filters, version navigation, exact-byte Markdown download, original/source links, attributed development references, unresolved/blocked states, activity/backlog/failure counters and retained-byte totals. Existing economic screens remain intact.
- Explicit hash-bound Quant development-metadata catalog: historical SC-0002 card and **in-sample 2000–2015 report**, plus SC-FUT-0008 development card. This is a small engineering-reviewed local reference manifest, not a research approval or current-strategy decision. No result trees, held-out sibling, market/DBN/NPZ files or engine modules are opened. Missing run/ledger identities stay null; source cross-check wording is retained without inventing a profitability verdict.
- Managed output page/catalog export, content-change-only updates, checksum conflict protection, bounded worker and per-source daily FRED due/backoff/day caps, shared OS worker/numerical locks (including constructor/connection lifetime), session last-good UI fallback, scheduler enable/disable/readback capability behind separate activation confirmation, offline integrity verifier and isolated paired backup/restore.
- `pdl-intake` commands, manual script, real-browser drivers, config examples, README and source/runtime integration guide. Python remains the isolated 3.13 project environment; pinned new dependencies are PyYAML 6.0.3 and portalocker 3.2.0 in `uv.lock`.

### Observed RED → GREEN evidence

These are actual execution outcomes, not planned tests or invented results. Each main behavior was introduced by a failing focused test before implementation, followed by green focused/full regression runs:

| Slice | Observed RED | Observed GREEN |
|---|---|---|
| Durable blob/version store | missing `intake_store` module | full suite 19 passed |
| Stable scope-safe scan/queue/process | missing `intake_scan` module, 6 cases failed | 6 focused cases passed |
| Managed status protection | missing `obsidian_status` module | full suite 28 passed, 1 skipped |
| Research UI | missing `research_view`, AppTest exception | full suite 29 passed, 1 skipped |
| Explicit development catalog | missing `quant_catalog` module | full suite 30 passed, 1 skipped |
| Numerical lifetime lock across processes | missing `locking` module | full suite 32 passed, 1 skipped |
| UI constructor contention | unhandled Busy; then incomplete-constructor catalog access | full suite 33 passed, 1 skipped |
| Due refresh/non-overlap worker | missing `worker` module, 2 tests failed | full suite 35 passed, 1 skipped |
| Scheduler safe capability | missing `scheduling` module, 3 tests failed | full suite 38 passed, 1 skipped |
| Manual UI action | no Process inbox now button | full suite 39 passed, 1 skipped |
| Integrity/restore verifier | missing `intake_verify` module | full suite 41 passed, 1 skipped |
| Blocked reference + type/source filters | blocked verdict displayed; filters absent | full suite 43 passed, 1 skipped |
| Retain malformed metadata for review | no retained item | full suite 44 passed, 1 skipped |
| FRED child root/failure provenance | child environment roots were None | full suite 45 passed, 1 skipped |
| Relocatable Obsidian deep link | missing configurable link helper | green in full suite |
| Backlog/review/error counts | health missing pending_count | full suite 51 passed, 1 skipped |
| Scheduler cadence/extra-action drift | malformed schedule readback incorrectly returned drift=false | green in final full suite |
| Busy refresh must not replay old success | cached success returned after Busy | green in final full suite |
| Managed-page revision provenance | inspected revision absent from generated page | final full suite 55 passed, 1 skipped |

Additional acceptance/regression tests cover no note-directed network/subprocess, generated/private-note exclusion, actual Windows junction rejection, ambiguous copies, source deletion, partial saves, expired leases, killed separate-process worker lock, publication failure, hash corruption and capped scan rotation. These passed against implemented paths and are **not** falsely labeled new RED cycles. One symlink-specific case is skipped because Windows symlink privilege is unavailable; the real junction escape test passes. The two legacy economic UI tests now use isolated temporary **test-only** datasets so source-only checkout verification does not depend on copied runtime files. Actual-data/browser acceptance remains separate.

Final automated command: `uv run pytest -q --junitxml=reports/pytest-intake.xml` → **55 passed, 1 skipped**. `uv run python -m compileall -q app.py src scripts` passed. A source-only scratch copy (no runtime data, local config, vault notes or original venv) was independently synced with Python 3.13 and exercised to verify standalone-subproject relocation.

### Real manual and browser receipts

The sole new opted-in workflow note is `Integration workflow question.md` in the approved Research Inbox. It explicitly labels itself workflow acceptance/research questioning, not empirical evidence. Real scans captured an original and a later saved edit as one item, `ITEM-13b2afacaf4346f7`, with two versions:

- v1 SHA-256 `8125095ae76099af6b13b1a5e81e4536bd0ab7a9baac0982fa1ff643540464cd` (2,201 bytes).
- v2 SHA-256 `49c1e1460d661140fecc41594a1db849fa38cb791ef9dae98a7d0b6af21a273f` (2,462 bytes).

The offline intake verifier returned `ok: true`, **one item, two versions, 4,663 retained bytes**, source-current checksum match, three indexed development references and no integrity errors. It created and verified an isolated paired backup/restore in the active profile scratch directory; no scheduled task points at it. Repeated runs/restarts deduplicate. Pause → run-once returned `paused`; resume returned false; retrying an already organized item requeued zero jobs.

A real due worker pass fetched all three official FRED series successfully in **3.256 seconds**, retaining identical original snapshot hashes. A separate-process real CLI refresh also succeeded while the browser navigated/search-filtered the economic UI; all three charts remained available afterward, with no browser exceptions. Cached data remained unchanged. No data was fabricated. `scripts/verify_local.py` continued to pass raw/Parquet/CSV/YoY verification.

Real browser acceptance on a fresh isolated server checked research search, strategy/processing/evidence filters, unverified state, original/source links, two version selections and actual Markdown downloads with matching SHA-256, activity and empty state; no browser page errors. Economic browser acceptance checked all three charts, UNRATE search, date segments, 12-month 2020 CSV, source link, April 2020 hover 14.8 and empty state. Screenshots were visually inspected. Evidence:

- `reports/intake-acceptance.json`, `reports/pytest-intake.xml`
- `reports/intake-browser-acceptance.json`, `reports/browser-retained-v1.md`, `reports/browser-retained-v2.md`
- `reports/intake-research-top.png`, `reports/intake-research-library.png`, `reports/intake-empty-state.png`
- `reports/intake-concurrent-refresh.json`, `reports/intake-concurrent-refresh.png`
- Existing `reports/browser-acceptance.json`, economic screenshots and `reports/verification.json` were regenerated from real data.

The parent-owned 8501 server retained stale imported UI modules during development; a fresh test-only server on 8502 exposed current code and passed the full browser checks using `PDL_BROWSER_URL=http://127.0.0.1:8502`. Do not trust a rerun-only stale import as acceptance of edited modules; the parent owns the actual dashboard restart. Test server lifecycle is separate from the user's existing process.

### Disabled schedule / remaining controlled work

Live `pdl-intake schedule status` readback: `task=\\PersonalDataLibrary\\intake`, `registered=false`, `enabled=false`, `drift=false` (Windows reports task not found). Read-only Windows task inventory found no PDL/Quant/FRED tasks. **No registration, enablement or scheduled trigger was attempted.** The registration/trigger acceptance gate is intentionally pending separate activation authorization, not claimed passed by mock tests.

One generated vault status page and output-only Automation README exist. The minimal protected project `CLAUDE.md` pointer/index correction was attempted once through the normal file tool and **blocked by an approval timeout**; silence was not treated as consent and no bypass/retry was attempted. Parent/user must handle that separately authorized correction. Historical vault/repository handoffs were not overwritten. See `INTEGRATION.md` for source-only copy allowlist, external runtime environment variables and parent-owned publication work.

The following original first-release notes are retained as historical baseline; their one-writer/no-scheduler statements predate this implementation.


## Delivered scope

Standalone `C:/Users/jason/personal-data-library`. Python 3.13.15 in the project `.venv`, created with `uv venv --python 3.13 .venv`; `uv sync` resolved and installed free dependencies. `uv.lock` records the actual environment. No changes to Quant projects or Hermes configuration/skills were made; no Git push, public deployment, account or paid service was used. No long-running server was started or left running by this build.

## Real collection (2026-10-28 UTC)

All downloads succeeded from the official `https://fred.stlouisfed.org/graph/fredgraph.csv` endpoint with `cosd=1999-01-01`.

| Series | Stored rows | Observation window | Display rows from Jan 2000 | Null values | Missing calendar months | Latest source value |
|---|---:|---|---:|---:|---:|---:|
| CPIAUCSL | 333 | 1999-01-01 to 2026-09-01 | 321 | 1 | 0 | 336.298 |
| UNRATE | 333 | 1999-01-01 to 2026-09-01 | 321 | 1 | 0 | 4.2 |
| FEDFUNDS | 333 | 1999-01-01 to 2026-09-01 | 321 | 0 | 0 | 3.75 |

CPI and UNRATE have a source null at **2025-10-01**. It is preserved as null, not replaced. First successful retrieval timestamps were 16:45:53.745134+00:00, 16:45:53.887650+00:00 and 16:45:54.062810+00:00 respectively. Source Last-Modified headers are separately preserved. Release availability times are unknown, not inferred. A second actual `uv run pdl-refresh` at 16:49:05 UTC succeeded for all three and deduplicated to **one logical snapshot per series** without rewriting original retrieval times.

`reports/verification.json` contains exact paths/checksums and measured data-directory size (2,406,622 bytes at that check; later catalog growth can change this). Actual CPI check: January 1999 index 164.7, January 2000 index 169.3, YoY 2.792956891317555%. The local verifier checked raw SHA-256, raw/Parquet equality, all three selected CSV roundtrips, null dates, and offline data reload.

## Vertical TDD evidence

Tests were written and executed before each new data/UI behavior slice; implementation was followed by a passing full suite. Initial package/module import errors were resolved with empty/docstring scaffolds and rerun to get proper missing-feature failures before implementing behavior. This is a summary of **observed terminal output**, not synthesized test results:

| Tracer bullet | Observed RED | Observed GREEN full-suite count |
|---|---|---:|
| Official CSV parser preserves nulls and pre-display history | `core.parse_csv` missing | 1 passed |
| Numeric/date/month-start/duplicate/empty validation | 6 cases failed to raise (3 already passed including parser test) | 9 passed |
| Calendar-month CPI YoY, missing months, filtering and CSV | `core.with_yoy` missing | 10 passed |
| Raw + Parquet + DuckDB publication, metadata, offline reload, dedupe | `core.Library` missing | 11 passed |
| Refresh, revisions, failed import/network retention and attempt history | `Library.refresh` missing | 12 passed |
| Official connector response validation and fallback | `fred.fetch` missing | 13 passed |
| Correct official download path | assertion expected `/graph/fredgraph.csv?`, got `/graph/graph.csv?` | 13 passed |
| Standard HTTP client header handling after live timeout | test rejected custom headers | 13 passed |
| Dashboard offline startup, panels, search, details, export | title absent from docstring-only app | 14 passed |
| Source reversion chooses earlier checksum without duplicate | expected original active checksum; got newer checksum | 15 passed |
| CLI refresh emits results and nonzero partial-failure code | `refresh.main` missing | 16 passed |
| Informative UI refresh failure | UI could not show `Offline verification` because connector discarded exception text | 18 passed after message preservation |

Additional safety coverage exercises interrupted file publication (failure on second rename), no active-pointer switch, no temporary files remaining, and UI selected table equality with the real saved CPI transformation. Those are regression/acceptance checks against the already implemented safety behavior, not falsely claimed new RED/GREEN slices. One catalog-search test initially assumed a Federal Reserve distributor search matched only FEDFUNDS; corrected the assertion to search the distinct underlying Board of Governors origin, because all three correctly name the Fed distributor.

Final commands (rerunnable in project):

```text
uv run pytest -q --junitxml=reports/pytest.xml
uv run python scripts/verify_local.py
uv run python -m compileall -q app.py src scripts
uv run pdl-refresh
```

Final automated suite: **18 passing cases**, including **2 Streamlit AppTests**. No network required for the suite once real snapshots have been collected. UI tests prohibit ordinary startup/network activity and simulate a failed refresh in an isolated copied library. The actual CSV export is verified through core roundtrip checks; a browser-driven click/download remains for the parent acceptance pass.

## Source-access issues and resolution

The suggested `/graph/graph.csv` URLs timed out through one Python request path and returned HTTP 404 through curl. A real-browser discovery attempt itself timed out. Official graph-page HTML/JavaScript, retrieved with curl, showed download links constructed as `/graph/fredgraph.csv`. That corrected official public path returned HTTP 200 and real CSV. A custom application User-Agent also timed out in this environment; the standard requests User-Agent succeeded. Connector tests and README preserve both lessons. A documented API-path request returned HTTP 400: `Variable api_key is not set`; no key was guessed or borrowed. Since CSV succeeded there is no data-access blocker and no API-key dependency.

## Still to verify outside this subtask

Independent parent acceptance completed: 18 tests rerun passing, offline integrity verifier passed, server health returned `ok` on 127.0.0.1:8501. Browser Use CLI timed out; fallback headless Microsoft Edge via Playwright worked. Both screens were visually inspected. Browser acceptance exercised three charts, UNRATE search, visible date segments (2020-01-01 through 2020-12-28), source-link target, actual CSV download with 12 monthly rows, April 2020 hover value 14.8, and empty-search UX. No browser page errors. Reports and screenshots are in `reports/`; reproduce with `uv run --with playwright python scripts/browser_acceptance.py` while server runs. The initial subtask did not start a server; the parent subsequently started one for acceptance and user access. User walkthrough/teach-back remains optional and is not claimed complete.

## Publication safety and limits

Validation happens before any published snapshot. Raw and clean files are staged and atomically renamed; a DuckDB transaction publishes metadata and active pointer only after both exist. A second-file or DB publication failure retains the prior active snapshot. Orphaned unreferenced evidence can survive a crash; no automatic deletion hides it. Snapshot files are immutable by application convention, not OS-tamperproof. Single local writer; stop UI before CLI writes/backup. Source nulls, revisions and latest-vintage limitations are surfaced rather than silently repaired.

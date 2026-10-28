# Source integration and external runtime

## Ownership/layout

This folder is an independently packaged **uv subproject**, not a Quant engine module. The reviewed publication destination is `apps/personal-data-library/` on the Quant repository's `testing` branch, with a parent-owned PR to `main`. The original standalone directory is not a Git repository. Do not initialize a competing repository, import Quant modules, change strategy files, or copy runtime state into Git.

Source root is derived from `__file__`; moving the complete subproject does not require changing imports or absolute source paths. Keep its `pyproject.toml`, `uv.lock` and `.venv` independent of Quant's Python environment. Run commands **from the subproject directory**, not the Quant root:

```text
uv sync --python 3.13 --locked
uv run pytest -q
uv run pdl-intake --help
uv run pdl-intake schedule status
```

No tests require personal vault notes or real downloaded snapshots. The economic UI unit tests use explicitly test-only temporary data. Real-data verifiers and browser acceptance are separate local acceptance commands, never a synthetic app fallback.

## Copy allowlist (source only)

Copy these source paths, preserving structure:

- `app.py`, `run-dashboard.cmd`, `pyproject.toml`, `uv.lock`, `.gitignore`
- `README.md`, `BUILD-NOTES.md`, `INTEGRATION.md`
- `.streamlit/config.toml`
- `src/data_library/*.py`
- `tests/*.py`
- `scripts/*.py`
- `config/intake.example.toml`, `config/quant-artifacts.example.json`

**Never copy/stage** `data/`, `reports/`, `.venv/`, `.test-tmp/`, `.pytest_cache/`, any `__pycache__/`, `.env`, `config/intake.toml`, `config/quant-artifacts.json`, backups, the personal vault, raw reports/notes, CSV/Parquet, DuckDB/SQLite/WAL files, or credentials. Reports are verification evidence kept in the external local runtime, not source fixtures. The actual reviewed manifest is local ignored configuration; the committed example is deliberately blocked.

## Reuse external state without moving it

Keep the original external runtime data/config and vault where they are. Before starting the new source copy, explicitly set:

- `PDL_DATA_DIR`: the existing external **data directory**, not the project root.
- `PDL_INTAKE_CONFIG`: the existing ignored local `intake.toml` file (it contains explicitly opted-in roots and the absolute local manifest pointer).

For Windows Command Prompt, substitute your actual approved paths:

```bat
set "PDL_DATA_DIR=C:\approved-local-runtime\data"
set "PDL_INTAKE_CONFIG=C:\approved-local-runtime\config\intake.toml"
uv run python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true --browser.gatherUsageStats false
```

For bash/MSYS, use `export PDL_DATA_DIR='C:/approved-local-runtime/data'` and `export PDL_INTAKE_CONFIG='C:/approved-local-runtime/config/intake.toml'` instead. Do not paste secrets into either variable.

`pdl-intake` reads the explicit local configuration; its FRED child receives the configured numerical data directory explicitly. The app uses `PDL_DATA_DIR`. `pdl-refresh --data-dir APPROVED_DATA_DIR` is explicit; do not accidentally refresh a new empty source-local store. Numerical verifier and research/concurrency browser drivers honor `PDL_DATA_DIR`. Acceptance reports are written under the source copy's ignored `reports/` directory. Stop the old dashboard before binding the relocated source to the same port; the parent owns that restart.

## Scheduler boundary after relocation

No task has been registered or activated. A task registered from one source copy targets **that copy's** interpreter/script/working directory, and must not silently be redirected on migration. Existing local runtime configuration must remain present. Before any later authorized activation, deliberately create the source-local ignored config (or explicitly arrange its environment), inspect task XML/readback and check for legacy overlapping jobs. The fixed task does not inherit interactive shell environment reliably. Keep automatic refresh off until approved roots and runtime paths are verified in the scheduled execution context. Never register a task for a temporary restore or source-smoke directory.

## Remaining human-controlled work

Parent: copy reviewed source to `apps/personal-data-library/`, verify in that directory, manage branch/commit/push/PR and server restart. The subagent does not publish. The protected vault project `CLAUDE.md` pointer update was blocked by an approval timeout; do not retry through a bypass. Parent/user can separately approve and perform the minimal guide/index/path correction. The new output-only Automation guide and one opted-in workflow note exist locally; neither belongs in Git.

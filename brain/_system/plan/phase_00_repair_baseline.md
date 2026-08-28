---
id: PHASE-00
type: plan_phase
phase: 0
title: Repair the baseline
status: done
created: 2026-08-28
completed: 2026-08-28
---

# Phase 0 — Repair the baseline

> **COMPLETE (2026-08-28).** 51 tests pass. `quant_brain/ops/events.py` + `agent_events` table shipped. Existing data verified intact (21 notes / 233 chunks / 233 embeddings). Next: [phase_01_agent_registry.md](phase_01_agent_registry.md).

Parent plan: [../../../PLAN.md](../../../PLAN.md)

## Why this phase exists

`tests/test_agent_events.py` imports `quant_brain.ops.events`, which does not exist. Pytest fails at **collection**, so the entire suite is red and the "49 passed" figure in the old handoff is stale.

The test was written before the module — it is a specification left behind as a marker. Read it as the contract.

This is not busywork: the event store it describes is the **observability spine for the whole harness**. The dispatcher (Phase 2) records every routing decision, path violation, and handler outcome through it — a harness you cannot observe is a harness you cannot debug.

## Entry gate

None. This is the first thing to do.

## Exit gate

```bash
cd C:/Users/jason/OneDrive/Desktop/quant-agent-brain
uv run pytest -q
```

All tests green, including both tests in `tests/test_agent_events.py`.

## The contract (derived from the existing test)

`tests/test_agent_events.py` requires exactly this API:

```python
from quant_brain.ops.events import list_events, record_event, summarize_run
```

### `record_event(...) -> int`

Keyword arguments used by the test:

| arg | type | required | notes |
|---|---|---|---|
| `db_path` | positional | yes | first positional arg |
| `run_id` | str | yes | groups events into one pipeline run |
| `task_id` | str | yes | e.g. `RQ-dd7da469` |
| `agent_role` | str | yes | e.g. `research_scout`, `qwen3:14b` |
| `stage` | str | yes | e.g. `discovery`, `evidence_extraction` |
| `status` | str | yes | `running` / `waiting` / `completed` / `failed` |
| `event_type` | str | yes | e.g. `stage_started`, `handoff_ready`, `stage_completed` |
| `message` | str | no | human-readable line |
| `payload` | dict | no | JSON-serializable extras |

Returns the new **monotonically increasing integer** `event_id`. The test asserts `second_id > first_id`.

### `list_events(db_path, run_id=..., after_event_id=None) -> list[dict]`

- Filters by `run_id`.
- When `after_event_id` is given, returns **only** events with a strictly greater id (incremental polling).
- Returns events ordered by `event_id` ascending.
- `payload` comes back as a **dict**, not a JSON string. The test asserts `events[0]["payload"] == {"query": "RSI exit rules"}`.
- An event recorded with no payload should come back with something falsy/empty — do not crash.

### `summarize_run(events) -> dict`

Takes the list from `list_events` and returns run state:

| key | value |
|---|---|
| `run_id` | the run id shared by the events |
| `task_id` | the task id shared by the events |
| `latest_event_id` | id of the last event |
| `agents` | dict keyed by `agent_role` → `{"status": <most recent status for that role>, ...}` |

The test asserts `state["agents"]["research_scout"]["status"] == "running"` and `state["agents"]["qwen3:14b"]["status"] == "waiting"` — i.e. **last status wins per agent role**.

Decide sensibly what an empty `events` list returns (empty dict / `None` fields) — the test does not cover it, so keep it simple and non-crashing.

## Schema change

Add to [../../../src/quant_brain/db/schema.sql](../../../src/quant_brain/db/schema.sql):

```sql
CREATE TABLE IF NOT EXISTS agent_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    task_id TEXT,
    agent_role TEXT NOT NULL,
    stage TEXT NOT NULL,
    status TEXT NOT NULL,
    event_type TEXT NOT NULL,
    message TEXT,
    payload_json TEXT DEFAULT '{}',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_agent_events_run ON agent_events(run_id, event_id);
CREATE INDEX IF NOT EXISTS idx_agent_events_task ON agent_events(task_id);
```

`init_database` already runs `executescript` with `CREATE TABLE IF NOT EXISTS`, so this is idempotent and safe against the existing `db/brain.sqlite`. **Verify** that by running init against the real DB and confirming no data loss:

```bash
uv run python -c "from quant_brain.db.init_db import init_database; print(init_database())"
uv run python scripts/index_markdown.py index   # counts should be unchanged
```

Do **not** add a foreign key from `agent_events.task_id` to `research_questions` — events must be recordable for runs whose task rows do not exist yet (and the existing tests record `task_id="RQ-1"` with no such row, with `PRAGMA foreign_keys = ON`). A dangling task_id is intentional.

## Files to create/modify

| Path | Action |
|---|---|
| `src/quant_brain/ops/__init__.py` | create (empty) |
| `src/quant_brain/ops/events.py` | create — the three functions above |
| `src/quant_brain/db/schema.sql` | modify — add `agent_events` + indexes |

Follow the house style visible in `src/quant_brain/indexing/embeddings.py`:
- `from __future__ import annotations` at the top
- type hints throughout, `str | Path` for db paths
- `init_database(db_path)` called at the top of public functions
- `with connect(db_path) as conn:` + explicit `conn.commit()`
- an `argparse` `main()` at the bottom if a CLI makes sense (for events: a `tail` subcommand showing recent events for a run is genuinely useful — keep it to one screen of code)

## Verification steps

```bash
cd C:/Users/jason/OneDrive/Desktop/quant-agent-brain
uv run pytest -q                                   # all green
uv run pytest tests/test_agent_events.py -v        # both tests pass explicitly
uv run python scripts/index_markdown.py index      # confirm existing data intact
```

## Definition of done

- [ ] `agent_events` table exists in schema.sql with indexes
- [ ] `quant_brain/ops/events.py` implements `record_event`, `list_events`, `summarize_run`
- [ ] `uv run pytest -q` is fully green
- [ ] Existing `db/brain.sqlite` still reports its prior note/chunk/embedding counts
- [ ] `PLAN.md` §10 checkpoint table updated: Phase 0 → done, with date

## Do not

- Do not "fix" the failing test by deleting it or marking it skip.
- Do not add an events *dashboard*, web UI, or streaming server. A table + three functions + optional `tail` CLI is the whole phase.
- Do not add fields the test does not need "for later." Add them when a later phase needs them.

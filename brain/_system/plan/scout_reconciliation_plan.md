---
id: SCOUT-RECONCILIATION
type: plan_phase
status: r1-r3-implemented
created: 2026-09-07
canonical_snapshot_folder: brain/00_Inbox/Source_Snapshots/
---

# Scout Reconciliation Plan

Parent plan: [../../../PLAN.md](../../../PLAN.md)

Jason approved this reconciliation on 2026-09-07. Canonical snapshot folder: **`brain/00_Inbox/Source_Snapshots/`**.

A seeded + manual research experiment proved the curator quality gate (0 promotions) but bypassed the registered Research Scout. This plan repairs the wiring without relaxing that gate.

## Scope

| ID | Work | Status |
|---|---|---|
| **R1** | Canonical snapshot folder = `Source_Snapshots` | implemented |
| **R2** | Raw-note schema enforcement (`data_access` and required contract fields) | implemented |
| **R3** | Wire live discovery to registered `research_scout` via the harness dispatcher | implemented |
| **R4** | Three child research questions | **deferred** — do not execute |

Out of scope: live research runs, strategy cards, relaxing the curator quality gate.

## R1 — Canonical snapshot folder

Registry, path enforcement, `save_source_snapshot`, and tests agree on:

```text
brain/00_Inbox/Source_Snapshots/YYYY-MM-DD/{sha256[:16]}.md
```

The older `brain/00_Inbox/Snapshots/` name is not a write path. Existing snapshot content is not deleted; this is path-name alignment only.

## R2 — Raw-note schema enforcement

Shared validator: `quant_brain.research.schema.validate_raw_research_payload`.

`data_access` allows only `available-now` | `available-later` | `not-realistic`. Illegal values such as `"partial"` fail closed at scout write time and at curator intake. The curator does not silently accept malformed notes.

CLI:

```bash
uv run python scripts/validate_raw_research.py path/to/note.md
```

## R3 — Dispatcher → research_scout → recommendation

`discovery` tasks route through the registry to `research_scout`. The handler runs a `DiscoveryBackend` and returns `recommendation="curation"`. It does not dispatch or execute the curator.

- **Production backend:** `live` (Agent Reach / Jina, injectable I/O; fail-closed if search/fetch is missing — no invented scraper).
- **Test double:** `seeded` (`STARTER_SOURCES`) behind the same handler, selected with `--stub`, `backend=seeded`, or `QUANT_BRAIN_DISCOVERY=seeded`. Not a second `assigned_agent`.

Pytest sets `QUANT_BRAIN_DISCOVERY=seeded` so CI makes zero network calls.

## Verification

```bash
uv run pytest -q
uv run python -m quant_brain.harness.registry --task-type discovery --json
uv run python scripts/dispatch_task.py --type discovery --research-id RQ-x --dry-run
uv run python scripts/dispatch_task.py --type discovery --research-id RQ-x --stub
```

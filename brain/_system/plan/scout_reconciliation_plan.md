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
brain/00_Inbox/Source_Snapshots/YYYY-MM-DD/{content_hash[:12]}-{url_hash[:8]}.md
```

The older `brain/00_Inbox/Snapshots/` name is not a write path. Existing snapshot content is not deleted; this is path-name alignment only. Two URLs that return identical body text keep two snapshot files so both identities stay auditable.

## R2 — Raw-note schema enforcement

Shared validator: `quant_brain.research.schema.validate_raw_research_payload`.

`data_access` allows only `available-now` | `available-later` | `not-realistic`. Illegal values such as `"partial"` fail closed at scout write time and at curator intake. The curator does not silently accept malformed notes.

CLI:

```bash
uv run python scripts/validate_raw_research.py path/to/note.md
```

## R3 — Dispatcher → research_scout → recommendation

`discovery` tasks route through the registry to `research_scout`. The handler runs a `DiscoveryBackend` and returns `recommendation="curation"`. It does not dispatch or execute the curator.

- **Production backend:** `live`. The handler constructs `LiveDiscoveryBackend(allow_network=True)` with no injected `search_fn`. Search goes through `AgentReachAdapter` (`agent-reach doctor --json`, then Exa/mcporter, then `gh` fallback; fetch via Jina Reader). See [../agent_reach_adapter_workflow.md](../agent_reach_adapter_workflow.md).
- **Test double:** `seeded` (`STARTER_SOURCES`) behind the same handler, selected with `--stub`, `backend=seeded`, or `QUANT_BRAIN_DISCOVERY=seeded`. Not a second `assigned_agent`.
- **Caps:** `max_sources = min(agent extras, task payload)`. Callers may narrow; they may not widen.
- **Fail closed:** live failure restores the research question to `queued`, deletes incomplete raw-note scaffolds, writes `Failed_Runs/{run_id}.md`, and records scout events. The exception still propagates so dispatch records `handler_failed`.

Pytest sets `QUANT_BRAIN_DISCOVERY=seeded` so CI makes zero network calls.

## Verification

```bash
uv run pytest -q
uv run python -m quant_brain.harness.registry --task-type discovery --json
uv run python scripts/agent_reach_check.py
uv run python scripts/dispatch_task.py --type discovery --research-id RQ-x --dry-run
uv run python scripts/dispatch_task.py --type discovery --research-id RQ-x
uv run python scripts/dispatch_task.py --type discovery --research-id RQ-x --stub
```

R4 remains deferred. Do not run child research questions or strategy cards as part of this reconciliation.

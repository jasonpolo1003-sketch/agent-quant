---
id: PHASE-02
type: plan_phase
phase: 2
title: Dispatcher + path enforcement
status: done
created: 2026-08-28
completed: 2026-08-28
---

# Phase 2 — Dispatcher + path enforcement

> **COMPLETE (2026-08-28).** 95 passed, 1 skipped. Routing, resolved-path enforcement, event trail, re-entrancy guard, and guarded migrations all shipped. Verified live on a scratch copy with both deterministic agents. Workflow doc: [../dispatcher_workflow.md](../dispatcher_workflow.md). Next: [phase_03_semantic_rag.md](phase_03_semantic_rag.md).

Parent plan: [../../../PLAN.md](../../../PLAN.md)

> **This is the phase that turns a collection of scripts into a harness.** Everything before it is groundwork; everything after it is registry entries.

## Why this phase exists

Right now, running an agent means running a *specific script*: `research_scout_runner.py`, then `research_executor.py`, then `curator_executor.py`. The sequence lives in a human's head and in `SESSION_HANDOFF.md`. There is no component whose job is *"given this task, decide who should do it, give them exactly what they're allowed to touch, and record what happened."*

That component is the dispatcher. With it, adding an agent is a registry entry (Phase 1) plus a handler registration — never a change to the routing logic.

## Entry gate

Phase 1 complete (registry loads validated `AgentSpec`s).

## Exit gate

- `dispatch(task)` routes a typed task to a capable, enabled agent.
- The work packet is built from the **agent's declared** paths, not caller arguments.
- A write outside declared paths is **blocked**, not warned.
- Every dispatch decision and outcome is recorded via `ops.events`.
- No-capable-agent and ambiguous-match are handled explicitly, loudly.
- Verified end-to-end using the **existing deterministic agents** — this phase needs no new agent capability.

## Design

### Task shape

Tasks gain a type. Add `task_type` to `agent_tasks` (nullable for existing rows):

```sql
ALTER TABLE agent_tasks ADD COLUMN task_type TEXT;
```

Since `init_db` uses `executescript` with `CREATE TABLE IF NOT EXISTS`, an `ALTER` needs a guarded migration. Keep it simple: a `migrations.py` helper that checks `PRAGMA table_info(agent_tasks)` and adds the column when absent. Do not pull in Alembic for one column.

```python
@dataclass(frozen=True)
class Task:
    task_id: str
    task_type: str          # "discovery" | "curation" | ...
    payload: dict[str, Any] # task-specific input (e.g. research_id)
    run_id: str             # groups related dispatches
```

### Dispatcher

`src/quant_brain/harness/dispatcher.py`

```python
HandlerFn = Callable[[Task, AgentSpec, WorkPacketContext], HandlerResult]

def register_handler(task_type: str, agent_name: str, fn: HandlerFn) -> None
def dispatch(task, *, project_root, db_path, registry=None) -> DispatchResult
```

Routing algorithm — keep it this boring:

```
1. load registry
2. candidates = enabled agents whose `handles` contains task.task_type
3. 0 candidates  -> raise NoCapableAgent(task_type, registry_names)   [loud]
   >1 candidates -> raise AmbiguousDispatch(task_type, names)         [loud]
   1 candidate   -> proceed
4. resolve the registered handler for (task_type, agent.name)
   missing -> raise NoHandlerRegistered
5. build work packet using agent.allowed_read_paths / allowed_write_paths
6. record event: dispatch_started
7. run handler inside the path-enforcement guard
8. validate result against agent.output_contract
9. record event: dispatch_completed | dispatch_failed
10. return DispatchResult (status, outputs, recommendation, events)
```

**Ambiguity is an error, not a heuristic.** Do not add priority scores, round-robin, or "pick the first." If two agents claim a task type, that is a design mistake the human must resolve. Silent selection makes runs irreproducible.

### Path enforcement — the security-relevant part

Declared paths mean nothing unless the harness actually blocks violations. Enforce on **resolved absolute paths**, not string prefixes:

```python
def assert_write_allowed(project_root: Path, target: Path, allowed: tuple[str, ...]) -> None:
    root = project_root.resolve()
    resolved = (root / target).resolve()      # resolves .. and symlinks
    for rel in allowed:
        base = (root / rel).resolve()
        if resolved == base or base in resolved.parents:
            return
    raise PathViolation(target, allowed)
```

Requirements:
- **Resolve before comparing.** String prefix checks are defeated by `brain/00_Inbox/../../etc/passwd`.
- **Resolve symlinks.** A symlink inside an allowed directory pointing outside must be caught.
- Confirm the resolved path is still under `project_root` — an allowed path list should never permit escaping the repo.
- A violation **raises and aborts the dispatch**. It does not warn and continue.
- Record a `path_violation` event with the attempted target before raising.

[agents/executor.py](../../../src/quant_brain/agents/executor.py) already parses allowed write paths from packet Markdown and does project-relative checks. Lift that logic into the harness so there is **one** enforcement implementation, and have the executor call it.

### Handler contract

A handler runs one bounded task and returns:

```python
@dataclass(frozen=True)
class HandlerResult:
    status: str                      # completed | failed
    outputs: tuple[str, ...]         # paths written
    recommendation: str | None       # suggested next task type — advisory ONLY
    detail: dict[str, Any]
```

**The `recommendation` is advisory.** Per PLAN.md §2, the harness decides what runs next; agents never dispatch. A handler that tries to call `dispatch()` is a bug — consider asserting against re-entrancy.

### Events

Emit via `ops.events` (Phase 0), all sharing `run_id`:

| event_type | stage | payload |
|---|---|---|
| `dispatch_started` | `dispatch` | task_type, agent, model |
| `packet_built` | `dispatch` | packet_id, read/write path counts |
| `handler_completed` | task_type | outputs, duration |
| `handler_failed` | task_type | error class, message |
| `path_violation` | `dispatch` | attempted target, allowed list |
| `dispatch_completed` / `dispatch_failed` | `dispatch` | final status |

`summarize_run(events)` should then reconstruct a whole run without reading any file.

## Proving it works — use existing agents

This phase must be verified **without** Agent Reach or Qwen. Register the deterministic implementations already in the repo:

- `discovery` → `research_scout` → wraps existing `research/executor.py` (the `STARTER_SOURCES` stub)
- `curation` → `knowledge_curator` → wraps existing `curation/executor.py`

That is the point: the stub is a legitimate handler behind a stable interface. Phase 6 swaps in the real discovery implementation and **nothing in the dispatcher changes**. If it does, this phase failed.

## Testing

- Route to the single capable agent; assert the correct handler ran.
- Zero candidates → `NoCapableAgent`, message names the task type and known agents.
- Two enabled candidates → `AmbiguousDispatch`.
- Disabled agent is not a candidate.
- **Path enforcement:** allowed write succeeds; `..` traversal blocked; absolute path blocked; symlink-escape blocked; violation emits an event and aborts.
- Handler that attempts re-entrant `dispatch()` is rejected.
- Events form a complete, ordered trail; `summarize_run` reconstructs status.

Use `tmp_path` fixtures with a miniature project root + fake `agents/` dir. No network, no Ollama.

## Files to create/modify

| Path | Action |
|---|---|
| `src/quant_brain/harness/dispatcher.py` | create |
| `src/quant_brain/harness/paths.py` | create — single enforcement implementation |
| `src/quant_brain/harness/migrations.py` | create — guarded `task_type` column add |
| `src/quant_brain/agents/executor.py` | modify — delegate path checks to `harness/paths.py` |
| `scripts/dispatch_task.py` | create — CLI: dispatch a task by type |
| `tests/test_dispatcher.py` | create |
| `tests/test_path_enforcement.py` | create |
| `brain/_system/dispatcher_workflow.md` | create |

## Verification

```bash
cd C:/Users/jason/OneDrive/Desktop/quant-agent-brain
uv run python scripts/dispatch_task.py --type discovery --research-id RQ-4ddd4ef4 --dry-run
uv run python scripts/dispatch_task.py --type discovery --research-id RQ-4ddd4ef4
uv run python -m quant_brain.ops.events tail --run-id <printed>
uv run pytest tests/test_dispatcher.py tests/test_path_enforcement.py -v
uv run pytest -q
```

The dry-run should print the chosen agent, its model, and its resolved allowed paths **without executing** — that is the harness explaining its routing decision, which is most of the debugging value.

## Definition of done

- [ ] `dispatch()` routes by task type using the registry
- [ ] `task_type` column migrated safely on the existing DB
- [ ] Zero-candidate and multi-candidate cases raise loudly
- [ ] Path enforcement resolves symlinks and `..`, blocks violations, emits events
- [ ] One enforcement implementation, used by both harness and executor
- [ ] Existing deterministic agents dispatch end-to-end
- [ ] Agents cannot dispatch agents
- [ ] Full run reconstructable from events alone
- [ ] `PLAN.md` §10 checkpoint updated

## Do not

- Do not add priority/scoring/fallback to routing. Ambiguity is a human decision.
- Do not add concurrency, queues, or worker processes. Single-process, one task at a time.
- Do not let handlers call `dispatch()`.
- Do not build a retry loop here. Retry policy belongs to the model layer (Phase 5: one repair, then escalate, then fail).
- Do not weaken path enforcement to make a handler convenient. Fix the declaration instead.

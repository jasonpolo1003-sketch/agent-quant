# Dispatcher Workflow

## Purpose

The dispatcher is the harness. Given a typed task it decides **who** should run it, hands that agent exactly what it is allowed to touch, enforces the boundary, and records what happened.

Before this existed, running an agent meant running a specific script in an order that lived in a human's head.

## Routing algorithm

```text
1. load registry
2. candidates = enabled agents whose `handles` contains task.task_type
3. 0 candidates  -> NoCapableAgent      (names the type and the whole registry)
   >1 candidates -> AmbiguousDispatch   (names the competing agents)
   1 candidate   -> proceed
4. look up handler for (task_type, agent.name); missing -> NoHandlerRegistered
5. build context from the AGENT'S declared paths
6. record dispatch_started
7. run handler inside the re-entrancy guard
8. verify every claimed output is inside the declared write paths
9. record handler_completed + dispatch_completed
```

**Ambiguity is an error, not a heuristic.** No priority scores, no round-robin, no first-match. If two agents claim a task type that is a design mistake for a human to resolve; silent selection makes runs irreproducible.

## Commands

```bash
# Explain the routing decision without executing -- most of the debugging value.
uv run python scripts/dispatch_task.py --type discovery --research-id RQ-x --dry-run

# Execute.
uv run python scripts/dispatch_task.py --type discovery --research-id RQ-x

# Reconstruct the run.
uv run python -m quant_brain.ops.events tail --run-id RUN-xxxx
uv run python -m quant_brain.ops.events summary --run-id RUN-xxxx
```

## Path enforcement

`harness/paths.py` is the single implementation, used by both the dispatcher and the work-packet executor.

Enforcement compares **fully resolved** paths, not string prefixes. `brain/00_Inbox/Raw_Research/../../../escaped.md` has an allowed prefix but an unallowed destination; resolving catches it, prefix matching does not. Symlinks are resolved for the same reason. A declared path that itself escapes the project root can never authorize a write.

Two enforcement points:
1. `context.resolve_write(target)` — what a handler calls before writing.
2. Post-run output verification — a handler cannot *claim* an output it was never allowed to write.

## Handler contract

```python
def handler(task, agent, context) -> HandlerResult:
    target = context.resolve_write("brain/00_Inbox/Raw_Research/out.md")
    target.write_text(...)
    return HandlerResult(
        status="completed",
        outputs=("brain/00_Inbox/Raw_Research/out.md",),
        recommendation="curation",   # ADVISORY ONLY
    )
```

`recommendation` is advisory. The harness decides what runs next. A handler that calls `dispatch()` raises `ReentrantDispatch` — agents never spawn agents (PLAN.md section 2).

## Registered handlers

| task type | agent | implementation |
|---|---|---|
| `discovery` | `research_scout` | live Agent Reach / Jina discovery; seeded starter catalog is a test double behind the same handler |
| `curation` | `knowledge_curator` | deterministic curator executor |

Phase 6 replaces the discovery implementation behind the same registration. **If that requires changing the dispatcher, Phase 2 was designed wrong.**

The seeded catalog (`STARTER_SOURCES`) remains reachable as `backend=seeded` / `--stub` so pytest stays offline. It is not a second `assigned_agent`.

## Events

| event_type | stage | when |
|---|---|---|
| `dispatch_started` | `dispatch` | routing resolved, handler about to run |
| `handler_completed` | task type | handler returned |
| `handler_failed` | task type | handler raised |
| `path_violation` | `dispatch` | write attempted outside declared paths |
| `dispatch_completed` / `dispatch_failed` | `dispatch` | terminal |

A dry run records **no** events — it executes nothing.

## Migrations

`harness/migrations.py` adds additive columns (`agent_tasks.task_type`, `agent_tasks.run_id`) guarded by `PRAGMA table_info`. `init_database` uses `CREATE TABLE IF NOT EXISTS`, which will not alter an existing table. Idempotent and safe on a populated database; a full migration framework is overkill for one local SQLite file.

## Known gotcha

Legacy executors store **absolute** paths in the database (`research_questions.raw_note_path`). Those may point at a different project root than the one being dispatched against. `handlers._relative_output` rebases onto the current run's root before enforcement. Path enforcement caught this during Phase 2 verification — it is exactly the class of bug it exists to catch.

## Files

```text
src/quant_brain/harness/dispatcher.py
src/quant_brain/harness/paths.py
src/quant_brain/harness/handlers.py
src/quant_brain/harness/migrations.py
scripts/dispatch_task.py
tests/test_dispatcher.py
tests/test_path_enforcement.py
```

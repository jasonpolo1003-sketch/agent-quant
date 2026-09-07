---
id: PHASE-01
type: plan_phase
phase: 1
title: Agent registry + capability declaration
status: done
created: 2026-08-28
completed: 2026-08-28
---

# Phase 1 — Agent registry + capability declaration

> **COMPLETE (2026-08-28).** 71 tests pass. `harness/registry.py` shipped; both agents migrated to typed frontmatter; `build_work_packet` uses declared paths with narrowing-only enforcement. Workflow doc: [../agent_registry_workflow.md](../agent_registry_workflow.md). Next: [phase_02_dispatcher.md](phase_02_dispatcher.md).

Parent plan: [../../../PLAN.md](../../../PLAN.md)

## Why this phase exists

Today an "agent" is a Markdown prose file in `agents/`. [work_packet.py](../../../src/quant_brain/agents/work_packet.py) `load_agent_role()` reads it and pastes the whole thing into a packet. Nothing is machine-readable: the file cannot say *what tasks it handles*, *what model it needs*, or *what paths it may touch*.

Worse, permissions currently flow the wrong direction. `build_work_packet(allowed_read_paths=...)` takes paths as a **caller argument**, defaulting to the module constant `DEFAULT_WRITE_PATHS = ["brain/00_Inbox/"]`. So the caller decides what the agent may write. In a harness that is backwards — **the agent declares its boundary and the harness enforces it**, so a buggy or careless caller cannot widen an agent's reach.

This phase makes agents declarable. Phase 2 makes them dispatchable.

## Entry gate

Phase 0 complete (pytest green, `ops.events` available).

## Exit gate

- Every file in `agents/` carries valid frontmatter.
- `load_registry()` returns validated `AgentSpec` objects.
- Malformed or unknown fields **fail loudly** at load time, not at dispatch time.
- Existing work-packet behavior still passes its tests.

## Design

### Frontmatter schema

Agent files keep their prose (it is still the role instruction handed to a model) and gain a machine-readable header:

```markdown
---
name: research_scout
handles: [discovery]
model: qwen3:14b
enabled: true
allowed_read_paths:
  - AGENTS.md
  - agents/
  - brain/00_Inbox/
  - brain/01_Sources/
  - brain/02_Strategy_Doors/
allowed_write_paths:
  - brain/00_Inbox/Raw_Research/
  - brain/00_Inbox/Source_Snapshots/
  - brain/00_Inbox/Failed_Runs/
output_contract: raw_research_note_v1
max_sources: 5
---

# Research Scout Agent
...existing prose unchanged...
```

Field meanings:

| Field | Type | Required | Meaning |
|---|---|---|---|
| `name` | str | yes | Must match filename stem |
| `handles` | list[str] | yes | Task types this agent can execute |
| `model` | str \| null | yes | Ollama model, or `null` for deterministic agents |
| `enabled` | bool | yes | Dispatcher skips disabled agents |
| `allowed_read_paths` | list[str] | yes | Project-relative; enforced in Phase 2 |
| `allowed_write_paths` | list[str] | yes | Project-relative; enforced in Phase 2 |
| `output_contract` | str | yes | Named contract the output is validated against |
| extras | any | no | Agent-specific config (e.g. `max_sources`) |

**Note the tightened write paths.** `research_scout.md` above narrows from the current blanket `brain/00_Inbox/` to the three subdirectories it actually needs. That is the point of declaration — least privilege, stated by the agent, enforced by the harness.

### Module

`src/quant_brain/harness/registry.py`

```python
@dataclass(frozen=True)
class AgentSpec:
    name: str
    handles: frozenset[str]
    model: str | None
    enabled: bool
    allowed_read_paths: tuple[str, ...]
    allowed_write_paths: tuple[str, ...]
    output_contract: str
    instructions: str          # the prose body
    path: str                  # agents/<name>.md
    extras: dict[str, Any]

def load_agent_spec(project_root, name) -> AgentSpec
def load_registry(project_root) -> dict[str, AgentSpec]
def agents_for_task_type(registry, task_type) -> list[AgentSpec]   # enabled only
```

Use `python-frontmatter` — already a project dependency (`pyproject.toml`), already used elsewhere in the codebase. Do not hand-roll a YAML parser.

### Validation rules — fail loudly

Raise a typed `RegistryError` when:
- frontmatter is missing or unparseable
- a required field is absent
- `name` does not match the filename stem
- `handles` is empty
- any path is absolute, or escapes the project root (`..`)
- `model` names a model not in the allowed set from PLAN.md §9
- two enabled agents declare the same task type **and** the plan has not authorized ambiguity (Phase 2 decides resolution; the registry just reports it)

Loud failure at load time is deliberate. A silently-skipped malformed agent is how a harness quietly stops doing half its job.

### Path normalization

Normalize every declared path once, at load: strip leading `./`, use POSIX separators, ensure directory paths end in `/`. Phase 2's enforcement compares against these normalized forms. **Windows note:** the project runs on Windows but stores POSIX-style relative paths — normalize with `PurePosixPath`, and compare resolved absolute paths when enforcing.

## Migration

Two files exist today. Migrate both:

| File | `handles` | model |
|---|---|---|
| `agents/research_scout.md` | `[discovery]` | `qwen3:14b` |
| `agents/knowledge_curator.md` | `[curation]` | `null` (deterministic today) |

Keep all existing prose. Only add frontmatter and tighten write paths.

Do **not** create `evidence_extractor.md` or `adversarial_reviewer.md` yet. Jason scoped v1 to Research Scout only — adding unused registry entries invites the dispatcher to be built around imagined agents rather than one real one.

## Backward compatibility

`build_work_packet()` currently accepts `allowed_read_paths` / `allowed_write_paths` arguments. Keep the signature working for now (existing tests depend on it), but:
- when the caller passes nothing, load from the registry instead of `DEFAULT_*` constants
- when the caller passes paths **wider** than the agent's declaration, raise
- narrowing is allowed (a caller may restrict further, never expand)

Phase 2 makes the registry the only source. This phase just stops the constants from being authoritative.

## Files to create/modify

| Path | Action |
|---|---|
| `src/quant_brain/harness/__init__.py` | create |
| `src/quant_brain/harness/registry.py` | create |
| `agents/research_scout.md` | modify — add frontmatter |
| `agents/knowledge_curator.md` | modify — add frontmatter |
| `src/quant_brain/agents/work_packet.py` | modify — registry-aware defaults, narrowing-only rule |
| `tests/test_agent_registry.py` | create |
| `brain/_system/agent_registry_workflow.md` | create |

## Verification

```bash
cd C:/Users/jason/OneDrive/Desktop/quant-agent-brain
uv run python -c "from quant_brain.harness.registry import load_registry; from quant_brain.config import PROJECT_ROOT; r=load_registry(PROJECT_ROOT); [print(s.name, sorted(s.handles), s.model, s.enabled) for s in r.values()]"
uv run pytest tests/test_agent_registry.py -v
uv run pytest -q
```

## Definition of done

- [ ] `AgentSpec` + `load_registry()` + `agents_for_task_type()` implemented
- [ ] Both agent files carry valid frontmatter with least-privilege write paths
- [ ] Malformed frontmatter raises `RegistryError` at load time
- [ ] Path traversal / absolute paths rejected
- [ ] `build_work_packet` uses registry defaults; widening raises, narrowing allowed
- [ ] Full suite green
- [ ] `PLAN.md` §10 checkpoint updated

## Do not

- Do not add agents that have no implementation yet. v1 is Research Scout.
- Do not build a plugin loader, entry-point system, or dynamic import mechanism. A dict of parsed Markdown files is the whole registry.
- Do not let the registry execute anything. It loads and validates declarations. Execution is Phase 2.
- Do not put secrets, API keys, or model endpoints in frontmatter.

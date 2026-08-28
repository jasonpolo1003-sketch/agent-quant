# Agent Registry Workflow

## Purpose

Agents declare what they can do and what they may touch. The harness enforces it.

Before this existed, an "agent" was prose in `agents/*.md` and its file permissions were a **caller argument** (`build_work_packet(allowed_write_paths=...)`) defaulting to a module constant. That let any caller hand any agent any reach. Now the agent states its own boundary and callers may only narrow it.

## Declaration format

Agent files keep their prose and gain frontmatter:

```yaml
---
name: research_scout          # must match the filename stem
handles: [discovery]          # task types this agent can execute
model: qwen3:14b              # or null for deterministic agents
enabled: true                 # disabled agents are never dispatch candidates
allowed_read_paths:
  - brain/01_Sources/
allowed_write_paths:
  - brain/00_Inbox/Raw_Research/
output_contract: raw_research_note_v1
max_sources: 5                # extras are agent-specific, kept in spec.extras
---
```

Allowed models come from `PLAN.md` section 9. Anything else is rejected.

## Current registry

| Agent | handles | model | writes |
|---|---|---|---|
| `research_scout` | `discovery` | `qwen3:14b` | `00_Inbox/Raw_Research/`, `00_Inbox/Snapshots/`, `00_Inbox/Failed_Runs/` |
| `knowledge_curator` | `curation` | deterministic | `00_Inbox/Curator_Reviews/`, `01_Sources/`, `02_Strategy_Doors/` |

Note the curator does **not** hold `brain/03_Strategy_Cards/` write access, even though its prose mentions strategy cards. No strategy card is created before the human gate in Phase 8.

## Commands

```bash
uv run python -m quant_brain.harness.registry
uv run python -m quant_brain.harness.registry --task-type discovery
uv run python -m quant_brain.harness.registry --json
```

## Rules

- **Least privilege.** Declare the narrowest paths the agent actually needs.
- **Fail loudly.** A malformed declaration raises `RegistryError` at load time and takes the whole registry down. A silently skipped agent is how a harness quietly stops doing half its job.
- **Narrowing yes, widening no.** A caller may restrict an agent further for one task; it may never expand the declaration.
- **No secrets in frontmatter.** No keys, tokens, or endpoints.
- **Undeclared files still work.** An agent file with no frontmatter keeps the legacy caller-supplied behavior, so migration can be gradual. Once it declares, the declaration wins.

## Path safety

Declared paths are normalized at load and rejected when absolute (`/etc/...`, `C:/...`) or escaping the project root (`../`). Windows backslashes are normalized to POSIX separators. Trailing slashes are preserved so directories stay visually distinct from files.

Phase 2 adds runtime enforcement on **resolved** paths (following symlinks) — declaration-time validation is necessary but not sufficient.

## Files

```text
src/quant_brain/harness/registry.py
tests/test_agent_registry.py
agents/research_scout.md
agents/knowledge_curator.md
```

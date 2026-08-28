---
id: PLAN
type: master_plan
status: active
owner: jason
created: 2026-08-28
last_updated: 2026-08-28
revision: 2
supersedes: revision 1 (monolithic executor design)
read_first: true
---

# Quant Agent Brain — Master Plan

> **Any AI agent (Claude Code, Claude Desktop, Cursor, Hermes, Codex):**
> Read this file first. It is the single source of truth for what we are building, in what order, and why. If you are picking up mid-flight, jump to [§10 Handoff Checkpoint](#10-handoff-checkpoint) — it tells you exactly what state the project is in right now.
>
> Do not skip phases. Do not add features not listed here. If you think the plan is wrong, write a note in `brain/_system/plan/plan_change_proposals.md` and **stop** — do not silently rewrite the plan.

---

## 1. What we are building (one paragraph)

A **local, budget-first, evidence-first quant research harness**. Not one big agent — a **dispatcher plus a registry of specialized agents**, each with a declared capability, model, and file-permission boundary. The harness routes bounded tasks to whichever agent is qualified, enforces the boundaries, validates the output, and records everything. Research flows from question → cited evidence → curated source → RAG → *frozen* strategy card → backtest → adversarial review. Live discovery goes through **Agent Reach** (a router, not a scraper). Local LLMs (**Qwen 14B / 27B**) do the model work. **No live trading. Ever.**

```
research → evidence → curation → RAG → strategy card → backtest → adversarial review → paper (later)
```

## 2. The harness is the product

This is the architectural decision that drives everything below. **Jason confirmed it on 2026-08-28.**

The goal is *not* an agent that does research. The goal is a **harness that dispatches specific agents to specific tasks**. Consequences:

- **Agents are registry entries, not code paths.** Adding an agent must not require editing the dispatcher. If it does, the harness is wrong.
- **Capabilities are typed.** A task has a type; an agent declares which types it handles. The dispatcher matches them. No hardcoded sequences.
- **The harness controls sequencing.** An agent completes one bounded task and returns a result plus a *recommendation*. The harness decides what runs next. **Agents never spawn agents** — that keeps runs reproducible, cost bounded, and failures non-cascading.
- **Permissions are declared by the agent and enforced by the harness.** Not passed in by callers, not honor-system.
- **Every dispatch is observable.** Which agent, which task, which model, which paths, what verdict, how long.

### Existing primitives this builds on (roughly 70% of a harness already exists)

| Have | File | Role in harness |
|---|---|---|
| Agent role files | `agents/*.md` | Becomes the registry entry (gains frontmatter) |
| Work packet builder | `src/quant_brain/agents/work_packet.py` | Becomes the dispatch payload |
| Bounded packet executor | `src/quant_brain/agents/executor.py` | Becomes one agent runner |
| `agent_tasks` table | `db/schema.sql` | Task state |
| `agent_events` (Phase 0) | new | Dispatch + stage observability |

**What is missing:** the registry (typed capability declaration), the dispatcher (task → agent matching), and real path enforcement. Currently `build_work_packet` takes `allowed_read_paths` as a *caller argument* defaulting to a module constant — in the harness the agent declares them and the harness enforces them.

## 3. Principles that constrain every phase

1. **Move slowly, one verified step at a time.** No batch feature drops.
2. **Evidence before strategy. Strategy before backtest. Backtest before paper.** No skipping.
3. **One agent, one bounded task.** Agents never see the whole brain, never dispatch each other.
4. **Fail closed.** Validation fails → write nothing durable, write a diagnostic, stop.
5. **Local first.** Qwen 14B default worker, 27B escalation. Cloud only on explicit human authorization.
6. **Provenance is mandatory.** Source, tier, captured-at — or the claim is labeled `unverified`.
7. **Agent Reach is a router, not a source.** Cite the upstream page/repo/transcript.
8. **No overengineering.** A deterministic function beats an LLM call whenever it can do the job. A stub behind a stable interface is legitimate — see §4.
9. **Observable dispatch.** Every routing decision recorded via `ops.events`.
10. **Human review is a first-class stage.** Curator, reviewer, and Jason can all say reject.

## 4. Stubs are legitimate; unverified promotions are not

The current research executor selects from a hardcoded `STARTER_SOURCES` list ([src/quant_brain/research/executor.py](src/quant_brain/research/executor.py)). **This is a deliberate stub behind a stable interface**, and it did its job: it proved the queue → note → curator → index → retrieval shape before any worker existed. That is correct engineering, not a defect.

The real issue is narrower and is a **data hygiene** problem, not architecture: five source notes were promoted into `brain/01_Sources/` as if verified, when their own `evidence` fields say things like *"verify exact formula and claims before final citation."* They are now indexed and embedded, so RAG can surface them as though they were checked.

**Cleanup task, tracked in §9:** once a real extraction agent exists, re-verify those five notes against their upstream sources, or demote them to leads.

## 5. Current state (verified 2026-08-28)

**Working:** SQLite schema + init; yfinance daily SPY/QQQ/IWM; research intake CLI; curator promotion; markdown indexer (21 files → 233 chunks); retrieval context builder + audit log; work packet builder + bounded executor; Agent Reach v1.5.0 installed and `doctor` runs.

**Broken:** `tests/test_agent_events.py` imports `quant_brain.ops`, which does not exist → pytest fails at collection. The "49 passed" in `SESSION_HANDOFF.md` is stale.

**Stubs awaiting real workers (by design):** research executor (`STARTER_SOURCES`); embeddings (`local-hash-embedding-v1`, a SHA-256 feature hash — lexical, not semantic); Qwen evaluated but never called at runtime; Agent Reach documented but never called by code.

**Not built, intentionally:** any backtest, any strategy card, any paper/live trading.

## 6. Non-goals

- A universal alpha-generating LLM.
- A general-purpose web scraper.
- A "trading bot."
- A GUI/dashboard/TUI. CLI + Markdown + SQLite is the interface.
- Multi-user or cloud-deployed anything.
- Agents that spawn agents.
- Anything that costs money without explicit escalation.

## 7. Phases

Each phase has an entry gate, an exit gate, and deliverables. Detail docs in [brain/_system/plan/](brain/_system/plan/).

### Phase 0 — Repair the baseline
**Detail:** [brain/_system/plan/phase_00_repair_baseline.md](brain/_system/plan/phase_00_repair_baseline.md)
**Entry:** none.
**Exit:** `uv run pytest -q` fully green.
**Deliverables:** `src/quant_brain/ops/events.py` (`record_event`, `list_events`, `summarize_run`); `agent_events` table + indexes in `schema.sql`; idempotent against existing `db/brain.sqlite`.
**Why first:** it is broken, and the event store is the harness's observability spine.

### Phase 1 — Agent registry + capability declaration
**Detail:** [brain/_system/plan/phase_01_agent_registry.md](brain/_system/plan/phase_01_agent_registry.md)
**Entry:** Phase 0.
**Exit:** Every `agents/*.md` declares typed capabilities in frontmatter; `load_registry()` returns validated `AgentSpec`s; unknown/malformed specs fail loudly.
**Deliverables:** frontmatter schema (`handles`, `model`, `allowed_read_paths`, `allowed_write_paths`, `output_contract`, `enabled`); `src/quant_brain/harness/registry.py`; migrate `research_scout.md` + `knowledge_curator.md`.

### Phase 2 — Dispatcher + path enforcement
**Detail:** [brain/_system/plan/phase_02_dispatcher.md](brain/_system/plan/phase_02_dispatcher.md)
**Entry:** Phase 1.
**Exit:** `dispatch(task)` routes by task type to a capable enabled agent, builds a work packet from the agent's *declared* paths, runs it, enforces writes, records events. Writing outside declared paths is **blocked**, not warned.
**Deliverables:** `src/quant_brain/harness/dispatcher.py`; `task_type` on tasks; path enforcement in the executor; no-capable-agent and ambiguous-match handled explicitly.
**This is the phase that makes it a harness.** Verified with the existing deterministic agents — no new capability needed.

### Phase 3 — Real semantic RAG
**Detail:** [brain/_system/plan/phase_03_semantic_rag.md](brain/_system/plan/phase_03_semantic_rag.md)
**Entry:** Phase 0 (independent of 1-2; may run in parallel).
**Exit:** Recall@5 ≥ 0.8 on a hand-labeled fixture set, beating the hash baseline.
**Deliverables:** Ollama `nomic-embed-text` as default backend, hash kept as `test-only`; `--reembed-all`; `scripts/retrieval_eval.py` reporting Recall@1/@5/MRR.
**Why before the scout ships:** the scout's packets carry retrieved context. Lexical retrieval feeds it near-random evidence.

### Phase 4 — Agent Reach adapter
**Detail:** [brain/_system/plan/phase_04_agent_reach_adapter.md](brain/_system/plan/phase_04_agent_reach_adapter.md)
**Entry:** Phase 0.
**Exit:** Health-check via `doctor --json`; fetch a web URL via Jina; snapshot with hash + captured_at; **zero network in pytest**.
**Deliverables:** `src/quant_brain/discovery/agent_reach.py`; zero-config channels only (web, github, youtube, rss, exa); login-backed channels off by default; snapshots to `brain/00_Inbox/Snapshots/`; forbidden-subcommand guard (`install`/`uninstall`/`configure`).

### Phase 5 — Qwen runtime + validators
**Detail:** [brain/_system/plan/phase_05_qwen_runtime.md](brain/_system/plan/phase_05_qwen_runtime.md)
**Entry:** Phase 0.
**Exit:** `qwen_call()` returns validated output or fails closed: 14B → validate → **one** repair → escalate 27B → fail.
**Deliverables:** `src/quant_brain/llm/{ollama_client,validators,qwen_call}.py`; five deterministic validator gates (schema, source-ID, contradiction, invented-rule, slop); golden-file tests, no Ollama in CI.

### Phase 6 — Research Scout as the first registered agent
**Detail:** [brain/_system/plan/phase_06_research_scout_agent.md](brain/_system/plan/phase_06_research_scout_agent.md)
**Entry:** Phases 0-5.
**Exit:** The harness dispatches a `discovery` task to the Research Scout; it uses Agent Reach + Qwen to produce a cited raw note; validators pass; curator accepts. Acceptance task: **RQ-dd7da469**.
**Deliverables:** Scout runner registered as a capability handler; replaces `STARTER_SOURCES` as the discovery implementation; hard caps (≤5 sources, ≤1 repair, ≤1 escalation, wall-clock); fail-closed to `brain/00_Inbox/Failed_Runs/`; run report every run.
**v1 scope is this agent only.** Extractor, Curator, and Reviewer become registry entries later — if adding them requires harness changes, the harness was wrong.

### Phase 7 — Re-verify the five unverified source notes
**Entry:** Phase 6.
**Exit:** Each of the five promoted notes is either re-verified against its upstream source or demoted to a lead. See §4.

### Phase 8 — Strategy card + first backtest
**Detail:** [brain/_system/plan/phase_08_first_backtest.md](brain/_system/plan/phase_08_first_backtest.md)
**Entry:** Phase 6 produced source-supported exit rule + max holding period + cost assumptions, **and** Jason approved moving to card stage.
**Exit:** One frozen strategy card, one backtest with next-bar execution enforced in code, one adversarial review with a verdict that can be reject.

### Phase 9 — Second market door
Not scoped until Phase 8 completes. Trend following on a futures proxy is the leading candidate.

## 8. Agent Reach usage contract

- **What it is:** router + doctor + installer for 15 platforms. Its own docs: *"NOT a wrapper — agents call upstream tools directly."* Each channel implements `can_handle/read/search/check` over an ordered backend list.
- **Executable:** `C:/Users/jason/.agent-reach-venv/Scripts/agent-reach.exe` (v1.5.0). **Do not `pip install agent-reach` from PyPI — different project.**
- **Clone for reading source:** `C:/Users/jason/Projects/Agent-Reach-review`. **Skill:** `memory_vault/Agents/skills/agent-reach/SKILL.md`.
- **Channels this project uses (zero-config):** web (Jina Reader), youtube (yt-dlp), github (gh), rss (feedparser), search (Exa via mcporter).
- **Off by default:** reddit, twitter, facebook, instagram, xiaohongshu, linkedin. They need Edge + the OpenCLI extension, and the quality policy rates social as Tier C (leads only) — it cannot be promoted anyway.
- **Health check first:** `agent-reach doctor --json`. Note `active_backend: null` means *unverified*, not *absent* — doctor deliberately skips probes that would read cookies or write device IDs (this is why `github` shows null despite `gh` working).
- **Never from code:** `install`, `uninstall`, `configure`. Never read `~/.agent-reach/config.yaml`. Never touch cookies. Never cite Agent Reach in a durable note.
- **On failure:** log an event, try the next backend Agent Reach lists, else fail closed. **Never invent a scraper.**

### Live doctor snapshot (2026-08-28)
```
youtube      warn  yt-dlp        (needs --js-runtimes node)
bilibili     ok    搜索API
github       warn  null          (gh present; doctor won't run auth status)
twitter/reddit/facebook/instagram/xiaohongshu
             warn  null          (OpenCLI extension NOT connected — Edge must be open)
```

## 9. Model policy

| Role | Model | When |
|---|---|---|
| Default worker | Ollama `qwen3:14b` | Evidence extraction, schema-bound tasks |
| Escalation / reviewer | Ollama `qwen3.8:27b` | 14B failed after one repair; adversarial review |
| Embeddings | Ollama `nomic-embed-text` | RAG (Phase 3+) |
| Test-only embeddings | `local-hash-embedding-v1` | pytest fixtures |
| Paid cloud | none active | Explicit human authorization only — never a silent fallback |

Evaluation basis (already recorded): `qwen3:14b` 3/3 passed, 17.7s, 2 repairs; `qwen3.8:27b` 3/3 passed, 124.0s, 0 repairs. 27B is ~7x slower (17 GB vs 12 GB VRAM) — the ladder exists so the fast model handles the common case.

Every LLM call records model, temperature, prompt hash, response hash, validator verdict, duration, via `ops.events`.

## 10. Handoff checkpoint

**Picking this up cold? Read this section, then start.**

### Where we are
- Plan **revision 2** written 2026-08-28, restructured around the harness architecture after Jason clarified the goal.
- **Phase 0 complete (2026-08-28).** Baseline is green: **51 passed**. `quant_brain/ops/events.py` implements `record_event` / `list_events` / `summarize_run`; `agent_events` table + `idx_agent_events_run` / `idx_agent_events_task` added to `schema.sql`. Existing data verified intact (21 notes / 233 chunks / 233 embeddings). CLI: `python -m quant_brain.ops.events tail --run-id X` and `summary --run-id X`.
- **Phase 1 complete (2026-08-28).** **71 passed.** `harness/registry.py` loads validated `AgentSpec`s from frontmatter in `agents/*.md`. Both shipped agents migrated: `research_scout` (handles `discovery`, `qwen3:14b`) and `knowledge_curator` (handles `curation`, deterministic). Permissions now flow the right direction — `build_work_packet` takes paths from the agent's declaration; a caller may **narrow** but never **widen** (raises `RegistryError`). Malformed declarations fail loudly at load. CLI: `python -m quant_brain.harness.registry [--task-type X] [--json]`.
- **Phase 2 complete (2026-08-28) — the harness exists.** **95 passed, 1 skipped.** `harness/dispatcher.py` routes typed tasks to the one qualified enabled agent (zero candidates → `NoCapableAgent`, multiple → `AmbiguousDispatch`; never a heuristic pick). `harness/paths.py` is the single enforcement implementation, comparing **resolved** paths so `..` and symlinks cannot smuggle a write out. Handlers cannot dispatch handlers (`ReentrantDispatch`). Every dispatch emits events; `summarize_run` reconstructs a run without reading files. `harness/migrations.py` added `agent_tasks.task_type` + `run_id` guarded by `PRAGMA table_info`. Verified live on a scratch copy: `discovery` → `research_scout` → wrote its raw note → recommended `curation`; `curation` → `knowledge_curator` → promoted 5 source notes. CLI: `scripts/dispatch_task.py --type X [--dry-run]`.
- **Enforcement caught a real bug during Phase 2 verification:** legacy executors store *absolute* paths in `research_questions.raw_note_path`, which pointed outside the dispatched project root. `handlers._relative_output` now rebases onto the current run's root. Exactly the class of bug path enforcement exists to catch.
- Note for whoever runs the indexer: `scripts/index_markdown.py index` re-chunks and resets all chunks to `embedding_status='pending'`, dropping embeddings. Follow it with `scripts/embed_chunks.py embed`. Pre-existing behavior, not introduced by Phase 0.

### What Jason decided (2026-08-28)
1. The end goal is a **harness that dispatches specific agents to specific tasks** — not one agent doing everything.
2. Agent model: **registry + typed capabilities**. Agents declare what they handle; a dispatcher matches.
3. Sequencing: **harness controls it**. Agents return a result + recommendation; they never spawn agents.
4. v1 agents: **Research Scout only.** Prove the harness with one worker; the rest become registry entries.
5. Order of work: research pipeline first, then RAG, then backtests.
6. The plan must be saved and portable enough for Claude Desktop to resume cold.

### What to do next
Execute **Phase 3** — read [brain/_system/plan/phase_03_semantic_rag.md](brain/_system/plan/phase_03_semantic_rag.md). Pull `nomic-embed-text` in Ollama, make it the default embedding backend (keeping the hash backend as `test-only` so pytest stays hermetic), add `--reembed-all`, and build `scripts/retrieval_eval.py` reporting Recall@1/@5/MRR against hand-labeled non-lexical fixtures. Exit gate: Recall@5 >= 0.8, beating the hash baseline. Then update the table below.

| Phase | Status | Done on | Notes |
|---|---|---|---|
| 0 — Repair baseline | **done** | 2026-08-28 | 51 passed. `agent_events` + 2 indexes added; data intact (21/233/233) |
| 1 — Agent registry | **done** | 2026-08-28 | 71 passed. Both agents declare typed capabilities; widening blocked |
| 2 — Dispatcher + path enforcement | **done** | 2026-08-28 | 95 passed. Routing, enforcement, events, re-entrancy guard all live |
| 3 — Semantic RAG | pending | — | **next** — independent of 1-2 |
| 4 — Agent Reach adapter | pending | — | — |
| 5 — Qwen runtime + validators | pending | — | — |
| 6 — Research Scout agent | pending | — | Acceptance: RQ-dd7da469 |
| 7 — Re-verify 5 source notes | pending | — | See §4 |
| 8 — Strategy card + backtest | pending | — | Needs Jason's explicit approval |
| 9 — Second market door | pending | — | Do not scope until 8 done |

### Where the plan lives
- **Master:** `quant-agent-brain/PLAN.md` (this file) — **wins any disagreement**
- **Phase detail:** `quant-agent-brain/brain/_system/plan/`
- **Obsidian pointer:** `memory_vault/Projects/Quant Agent Brain/CLAUDE.md`
- **Historical:** `quant-agent-brain/SESSION_HANDOFF.md`

## 11. When something goes wrong

- **Baseline test fails.** Fix before anything else. Never skip a broken test.
- **Validator rejects output.** One repair, then escalate to 27B, then write a `Failed_Runs/` note and stop. Do not coach the model.
- **Agent Reach channel down.** Fall back per §8. Never invent a scraper.
- **No capable agent for a task type.** Fail loudly with the task type and the registry contents. Never fall back to "some agent."
- **You think the plan is wrong.** Write to `brain/_system/plan/plan_change_proposals.md` and stop. Jason approves plan changes.
- **Out of context/time.** Update §10's table, add a one-paragraph note, stop cleanly.

## 12. Glossary

- **Harness** — the dispatcher + registry + enforcement layer that routes bounded tasks to qualified agents.
- **Agent** — a registry entry declaring capabilities, model, and path permissions; runs one bounded task.
- **Capability / task type** — the typed label matching a task to an agent (e.g. `discovery`, `extraction`, `curation`, `review`).
- **Work packet** — the dispatch payload: role + task + retrieved evidence + allowed paths + output contract + guardrails.
- **Method door** — a bounded exploration space for a strategy family. Not a strategy — a room that may contain one.
- **Strategy card** — a *frozen*, testable spec. No parameter changes after freezing.
- **Tier A/B/C/D** — source quality tiers in [brain/_system/research_source_quality_policy.md](brain/_system/research_source_quality_policy.md).
- **Fail closed** — on failure write nothing durable; write a diagnostic to `brain/00_Inbox/Failed_Runs/` and stop.

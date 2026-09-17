---
id: PLAN
type: master_plan
status: active
owner: jason
created: 2026-08-28
last_updated: 2026-09-16
revision: 4
supersedes: revision 3 (harness architecture retained; statistical validation gates strengthened)
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
11. **Every test is a trial.** Parameter sweeps, robustness variants, discarded configurations, and baseline runs enter the same immutable ledger. Adversarial review must use that complete ledger for multiple-testing adjustment; a raw prop-challenge pass rate is not evidence of edge without same-engine random-entry and buy-and-hold comparisons.

## 4. Stubs are legitimate; unverified promotions are not

The current research executor selects from a hardcoded `STARTER_SOURCES` list ([src/quant_brain/research/executor.py](src/quant_brain/research/executor.py)). **This is a deliberate stub behind a stable interface**, and it did its job: it proved the queue → note → curator → index → retrieval shape before any worker existed. That is correct engineering, not a defect.

The real issue is narrower and is a **data hygiene** problem, not architecture: five source notes were promoted into `brain/01_Sources/` as if verified, when their own `evidence` fields say things like *"verify exact formula and claims before final citation."* They are now indexed and embedded, so RAG can surface them as though they were checked.

**Cleanup task, tracked in §9:** once a real extraction agent exists, re-verify those five notes against their upstream sources, or demote them to leads.

## 5. Current state (verified 2026-09-07)

**Working:** Phases 0–4 are complete. The baseline is green (**149 passed, 1 skipped**); the registry/dispatcher and enforced path boundaries are live; `nomic-embed-text` is the default semantic retrieval backend; and the merged production Scout path routes `discovery` through `quant_brain.discovery`, Agent Reach/upstream tools, snapshots, raw-note validation, and a recommendation-only return to the harness. The Agent Reach adapter and discovery path are covered by recorded fixtures with zero network in pytest.

**Next:** Phase 5 / roadmap **Gate B** is complete, adversarially hardened, and merged to `main` (`fb3ecc3`, PR #2): production live Scout extraction uses the reusable local Qwen boundary (14B → one repair → 27B → fail closed), deterministic evidence validators, strict extractive support before durable promotion, compensating raw-note cleanup, and complete dispatcher failure finalization. **Gate C is complete and verified (2026-09-16):** bounded acquisition now classifies source tiers, ranks by credibility, collapses cross-channel duplicates, and rejects thin/SEO/promotional pages before Qwen. **Gate D is next and needs Jason's explicit authorization.**

**Still pending:** Phase 6 acceptance. The validated Phase 5 runtime is integrated, but the production Scout is not accepted end-to-end until the real child Scout acceptance runs are executed under the roadmap after Gate C. Preserved `research/live_*.py` runs are explicitly experimental history and do not satisfy this gate. No research acceptance, strategy card, backtest, paper trade, or live trade is complete.

**Market data:** the repository currently has **`price_datasets = 0`**. Historical downloader/module claims were not present in the reconciled tree and must not be treated as current capability. Roadmap **Gate F** owns restoring real files, provenance/checksums, and SQLite registration before any backtest.

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
**Deliverables:** `src/quant_brain/discovery/agent_reach.py`; zero-config channels only (web, github, youtube, rss, exa); login-backed channels off by default; snapshots to `brain/00_Inbox/Source_Snapshots/`; forbidden-subcommand guard (`install`/`uninstall`/`configure`).

### Phase 5 — Qwen runtime + validators
**Detail:** [brain/_system/plan/phase_05_qwen_runtime.md](brain/_system/plan/phase_05_qwen_runtime.md)
**Entry:** Phase 0.
**Exit:** `qwen_call()` returns validated output or fails closed: 14B → validate → **one** repair → escalate 27B → fail.
**Deliverables:** `src/quant_brain/llm/{ollama_client,validators,qwen_call}.py`; five deterministic validator gates (schema, source-ID, contradiction, invented-rule, slop); golden-file tests, no Ollama in CI.

### Phase 6 — Research Scout as the first registered agent
**Detail:** [brain/_system/plan/phase_06_research_scout_agent.md](brain/_system/plan/phase_06_research_scout_agent.md)
**Entry:** Phases 0-5.
**Exit:** After the validated Phase 5 Qwen boundary is integrated, the harness dispatches the roadmap's real child Scout runs (`RQ-6d9c12f4`, `RQ-c920baeb`, `RQ-80be8cf7`); each produces an honestly validated outcome and complete event/snapshot trail, and curator outcomes are recorded separately. The preserved `RQ-dd7da469` experimental rejection is audit history, not acceptance.
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
- Plan **revision 4** updated 2026-09-16. Revision 3 reconciled the merged Agent Reach/Scout implementation and gated roadmap; revision 4 preserves that architecture while making immutable trial accounting, multiple-testing adjustment, and same-engine challenge baselines hard requirements.
- **Phase 0 complete (2026-08-28).** Baseline is green: **51 passed**. `quant_brain/ops/events.py` implements `record_event` / `list_events` / `summarize_run`; `agent_events` table + `idx_agent_events_run` / `idx_agent_events_task` added to `schema.sql`. Existing data verified intact (21 notes / 233 chunks / 233 embeddings). CLI: `python -m quant_brain.ops.events tail --run-id X` and `summary --run-id X`.
- **Phase 1 complete (2026-08-28).** **71 passed.** `harness/registry.py` loads validated `AgentSpec`s from frontmatter in `agents/*.md`. Both shipped agents migrated: `research_scout` (handles `discovery`, `qwen3:14b`) and `knowledge_curator` (handles `curation`, deterministic). Permissions now flow the right direction — `build_work_packet` takes paths from the agent's declaration; a caller may **narrow** but never **widen** (raises `RegistryError`). Malformed declarations fail loudly at load. CLI: `python -m quant_brain.harness.registry [--task-type X] [--json]`.
- **Phase 2 complete (2026-08-28) — the harness exists.** **95 passed, 1 skipped.** `harness/dispatcher.py` routes typed tasks to the one qualified enabled agent (zero candidates → `NoCapableAgent`, multiple → `AmbiguousDispatch`; never a heuristic pick). `harness/paths.py` is the single enforcement implementation, comparing **resolved** paths so `..` and symlinks cannot smuggle a write out. Handlers cannot dispatch handlers (`ReentrantDispatch`). Every dispatch emits events; `summarize_run` reconstructs a run without reading files. `harness/migrations.py` added `agent_tasks.task_type` + `run_id` guarded by `PRAGMA table_info`. Verified live on a scratch copy: `discovery` → `research_scout` → wrote its raw note → recommended `curation`; `curation` → `knowledge_curator` → promoted 5 source notes. CLI: `scripts/dispatch_task.py --type X [--dry-run]`.
- **Enforcement caught a real bug during Phase 2 verification:** legacy executors store *absolute* paths in `research_questions.raw_note_path`, which pointed outside the dispatched project root. `handlers._relative_output` now rebases onto the current run's root. Exactly the class of bug path enforcement exists to catch.
- **Phase 3 complete (2026-08-28).** **97 passed, 1 skipped.** `nomic-embed-text` (768-dim, local Ollama) is the default embedding backend; `local-hash-embedding-v1` stays registered as `test-only` so pytest never needs Ollama (suite still runs in ~5s). All 233 chunks re-embedded (~8.5 min). Both backends coexist via `PRIMARY KEY (chunk_id, model)` — switching is a parameter, not a migration. **Recall@5 = 1.00 semantic vs 0.71 lexical (+0.29); MRR 0.790 vs 0.619.** New: `src/quant_brain/llm/ollama_client.py` (Phase 5 reuses it), `scripts/retrieval_eval.py --compare --save`, `--reembed-all` flag, and a loud error on dimension mismatch instead of silently returning zero results. Report: `brain/00_Inbox/Model_Evaluations/retrieval-eval-2026-08-28.json`.
- **Phase 3 indexing checkpoint (2026-09-16).** The Phase 3 indexing/retrieval edits held back from the Gate B checkpoint were reviewed on their own merits and accepted on branch `phase-3/indexing-and-retrieval-eval` (`b236175`). Three changes: `brain/00_Inbox/Source_Snapshots/` is now excluded from the index so raw uncurated scrape text cannot surface as retrieved evidence in Scout packets; the `pre_backtest_validation_checklist` retrieval fixture was removed as **unreachable** (it lives in the excluded `_system/`, so it was never in the database and scored as a permanent miss) and replaced with two fixtures whose targets are actually indexed; and `search_similar_chunks` now raises on a dimension mismatch instead of returning an empty list. Re-verified on the real database across 7 fixtures: **Recall@1 0.71, Recall@5 1.00, MRR 0.790** — still clears the ≥0.8 exit gate, and every fixture is now genuinely reachable. **199 passed, 1 skipped**; Ruff clean; `db/brain.sqlite` byte-unchanged (SHA-256 verified).
- **Known issue — `retrieval_eval.py --compare` is broken.** It compares the semantic backend against the `local-hash-embedding-v1` baseline, but the hash vectors are no longer in `db/brain.sqlite` (only `nomic-embed-text@768`), despite the Phase 3 design note saying to keep them for exactly this purpose. Most likely lost to the re-index-drops-embeddings behavior noted at the end of this section. Before the dimension-mismatch error existed this failed **silently** as recall 0.00; it now raises. Restoring it means re-embedding every chunk under the hash model, which writes to the database — deliberately not done. The single-model run that gates Phase 3 is unaffected. The lexical comparison figures recorded above are from the 2026-08-28 run against the older fixture set.
- **Open decision surfaced in Phase 3:** `brain/_system/` is excluded from the index (`markdown_indexer` defaults to `exclude_dirs={"_system"}`), so the pre-backtest validation checklist, the source-quality policy, and all workflow/plan docs are **not retrievable**. `index_markdown.py index --include-system` overrides it. Arguably the validation checklist should be indexed; not changed during a RAG phase to avoid altering indexer behavior mid-flight. Jason's call.
- **Phase 4 complete (merged 2026-09-07).** The thin Agent Reach adapter, recorded-fixture tests, source snapshots, raw-research schema, and production discovery handler are present. Registry and dry-run verification route `discovery` to `research_scout`; the handler returns a recommendation rather than dispatching another agent. Agent Reach health is inspectable. This does **not** accept the Qwen-backed Scout or any research result.
- **Gate B final verification (2026-09-11):** **201 passed, 1 skipped**; full-tree and scoped Ruff clean. Adversarial tests cover value/polarity preservation, generic ungrounded claims and rules, model-controlled promotion, post-write rollback, and dispatcher failure finalization. Child research questions remain queued and `price_datasets = 0`.
- **Gate B merged and reconciled (2026-09-15):** PR #2 merged to `main` as `fb3ecc3`; local `main` fast-forwarded with no upstream edits, so accepted Gate A/B code is byte-identical to the reviewed checkpoint. **210 passed, 1 skipped**; Ruff clean on both invocations. The final grounding fix replaced substring containment with whole-token matching at matching polarity, closing meaning reversal in both directions (`commission-free` out of `not commission-free`; `profit` out of `unprofitable`). Child RQs queued, `RQ-66078766` rejected, `strategy_cards`/`backtests`/`price_datasets`/`reviews` all zero. Recovery tag `pre-gatec-reconcile-20260915`. Gate C-adjacent scaffolding and Phase 3 indexing edits remained deliberately uncommitted pending their own review; both were resolved on 2026-09-16 (see the Phase 3 indexing checkpoint entry above). Note the **210** figure includes 13 tests from the then-untracked experimental files; the tracked-only baseline at that commit was **197 passed, 1 skipped**.
- **Gate C complete (2026-09-16).** Bounded source acquisition now discriminates by credibility before spending a fetch or a model call. **263 passed, 1 skipped**; Ruff clean on both invocations. PR #3 was merged first (`2a876f7`) because excluding `Source_Snapshots` from the index is a prerequisite for a gate that multiplies snapshot volume.
  - `discovery/source_quality.py` makes the written Tier A/B/C/D policy executable via three signal families: structural host/path shapes (arXiv `/abs/`, DOI, SSRN), allowlists for named institutions and practitioners, and a commercial-intent reject detector that runs **first** so promotional material on a credible host is still rejected. **A bare TLD is never a primary signal** — `.edu` qualifies only on a research/publication/repository path, `.gov` only via a recognized regulator/exchange set. Policy lives in code, not `brain/`, because that tree is agent-readable and a tier list there would let an agent widen its own promotion criteria.
  - `discovery/acquisition.py` adds normalize → dedupe → classify → rank → budget. Rejected candidates score `-inf` (a finite penalty lets topical slop climb back into the budget); topical overlap is capped below the practitioner bonus because keyword density is the one signal an SEO page fully controls.
  - **The unlock:** live discovery hardcoded `source_quality="discovery-only"` for every source while the curator only promotes `primary`/`practitioner`, so the live path could never promote anything it found. Tiers are now assigned discovery-side, which is the only correct placement since `llm/validators.py` treats `source_quality` as a protected field.
  - Pre-extraction content floor (600 chars / 120 words) rejects empty bodies, cookie banners, JavaScript shells, paywall stubs and promotional prose. Rejected pages are **not** snapshotted: the invariant is that nothing reaches the model unpersisted, not that everything fetched is persisted. A failed run discards the snapshots it wrote rather than leaving orphans.
  - Rejections are recorded twice: a `## Rejected Candidates` table in the raw note for the curator, and a `discovery_candidates_rejected` event for audit. The ledger stays outside the validated JSON block because `RawResearchPayload` is `extra="forbid"`.
  - Fixed a live bug: the forbidden-subcommand guard scanned every argv token, so any research question containing the word "install" was refused. It now guards the subcommand position, only for agent-reach itself.
  - Acceptance demonstration: `uv run python scripts/acquisition_report.py` runs the real pipeline over recorded fixtures with zero network and finds **3 primary + 1 practitioner** sources, rejecting promotional material pre-fetch, a cookie banner post-fetch/pre-model, and collapsing a cross-channel duplicate. Exits non-zero if any Gate C check fails.
  - **Lane status:** operational = Exa (mcporter), GitHub (`gh`). Fixture-only = arXiv `/abs/` (a `/pdf/` → `/abs/` rewrite promoting hits already found; no new dependency, no PDF parser). Deferred = YouTube, RSS. Never = all login-backed social channels.
  - Gate C did **not** run any child research question. `RQ-6d9c12f4`, `RQ-c920baeb`, `RQ-80be8cf7` remain `queued`; `strategy_cards`/`backtests`/`price_datasets`/`reviews` all remain 0.
- Note for whoever runs the indexer: `scripts/index_markdown.py index` re-chunks and resets all chunks to `embedding_status='pending'`, dropping embeddings. Follow it with `scripts/embed_chunks.py embed`. Pre-existing behavior, not introduced by Phase 0.

### What Jason decided (2026-08-28)
1. The end goal is a **harness that dispatches specific agents to specific tasks** — not one agent doing everything.
2. Agent model: **registry + typed capabilities**. Agents declare what they handle; a dispatcher matches.
3. Sequencing: **harness controls it**. Agents return a result + recommendation; they never spawn agents.
4. v1 agents: **Research Scout only.** Prove the harness with one worker; the rest become registry entries.
5. Order of work: research pipeline first, then RAG, then backtests.
6. The plan must be saved and portable enough for Claude Desktop to resume cold.

### What to do next
Gate C is complete and verified (2026-09-16). **Gate D is the next gate and requires Jason's explicit authorization** — it runs the three queued child research questions one at a time (`RQ-6d9c12f4` exit rules, then `RQ-c920baeb` maximum holding periods, then `RQ-80be8cf7` commission/slippage), each with its own dispatch, snapshots, validated raw note, events and separately dispatched curator verdict. Zero promotions is an acceptable Gate D outcome. Do **not** claim Phase 6 or research acceptance until those runs are performed and reviewed.

| Phase | Status | Done on | Notes |
|---|---|---|---|
| 0 — Repair baseline | **done** | 2026-08-28 | 51 passed. `agent_events` + 2 indexes added; data intact (21/233/233) |
| 1 — Agent registry | **done** | 2026-08-28 | 71 passed. Both agents declare typed capabilities; widening blocked |
| 2 — Dispatcher + path enforcement | **done** | 2026-08-28 | 95 passed. Routing, enforcement, events, re-entrancy guard all live |
| 3 — Semantic RAG | **done** | 2026-08-28 | 97 passed. Recall@5 1.00 vs 0.71 lexical (+0.29) |
| 4 — Agent Reach adapter | **done** | 2026-09-07 | Merged adapter + production discovery handler; fixture tests use zero network |
| 5 — Qwen runtime + validators | **done** | 2026-09-07 | Gate B: hermetic ladder tests + bounded 14B live smoke; per-attempt hashes/timing recorded |
| 5b — Gate C bounded acquisition | **done** | 2026-09-16 | 263 passed. Tier classifier, ranking, dedupe, pre-Qwen content floor, rejection ledger. Live sources can finally be promotable |
| 6 — Research Scout agent | pending | — | Gate D: run the three child questions. Needs Jason's authorization; experimental runs do not count |
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

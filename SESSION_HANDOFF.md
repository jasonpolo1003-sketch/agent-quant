# Quant Agent Brain — Session Handoff

## P1 quotation defect corrected and re-reviewed — committed to `testing` (2026-09-19)

The substring-matching blocker is fixed, independently re-reviewed and **APPROVED**, and the intake feature is committed on `testing`. **350 passed, 1 skipped**; Ruff clean on `.` and on `src tests scripts`.

**What the bug was.** `normalized()` collapsed whitespace but applied no token boundaries, so `quote in normalized(body)` was a raw substring test. `Exit when RSI > 5` matched source text `Exit when RSI > 50 or after 10 trading days.` Reproduced end-to-end: `quote_match`/`full_rule_match` true, `approve_scope` accepted, and the curator handoff carried `evidence: "Exit when RSI > 5"` — a threshold the source never states. Not automatic promotion (an attributed reviewer must approve scope), but it defeated the exact-quotation safeguard, whose whole promise is that evidence is the verbatim source span. Truncation at *either* edge did it, not only the reported prefix case.

**Why it mattered in plain terms.** Exiting at RSI > 50 is an ordinary mean-reversion exit; exiting at RSI > 5 would exit on nearly every bar — a different strategy. The one number defining the rule could be silently wrong in material handed to the curator while still passing an "exact quotation" check.

**The correction.** A boundary-safe `source_span()` helper in `external_verification.py`, used by all three matching sites: verification, `approve_scope` and `handoff`. A span must begin and end on a token boundary; a severed word or number is refused. Clean partial quotation stays legitimate (`Exit when RSI > 50` ends on a boundary and still matches). Text matching stays separate from full-rule and contextual assessment — `full_rule_match` remains its own `claim == quote` check, and reviewer scope judgement is unchanged.

**Stale cache closed.** `verify_claim` returns a cached `evaluations` row *before* matching runs, and `UNIQUE(claim_id,fetch_id)` prevents a corrected row replacing it, so a catalog verified under the old rule keeps `quote_match: true` permanently. Fixing the matcher alone was therefore insufficient: `approve_scope` and `handoff` now **re-derive** the check from the pinned snapshot instead of trusting the stored flag. Cached rows stay immutable (append-only history preserved, no schema change). A stale flag can still *display* as matched; it cannot approve or promote. `verify --force --allow-network` refreshes recorded values.

**Two further defects were found in the fix itself by re-review, and corrected.** (1) The first boundary rule was asymmetric — it guarded a quote ending in `.`/`,` before a digit but left the mirror case open, so `Threshold is 1` matched `1,250` (a 1250× misstatement) and `Win rate 0` matched `0.55`. Tellingly, `Threshold is 1,` was rejected while the *more* misleading `Threshold is 1` passed. Now symmetric over `.,:/%-` plus typographic separators, severing only when digits sit on both sides. (2) The character class was ASCII-only, letting the original defect back in via fullwidth (`５０`→`５`) or Arabic-Indic digits; now `str.isalnum()`, so the alnum test and `str.isdigit()` agree across scripts. The em dash is deliberately **not** a joiner: a dash census over the 18 real snapshots found en dash binding numeric ranges 25 times and em dash 0 times, while including it falsely rejected `It rose 20` from `It rose 20— then fell.`

**Verification.** 350 passed/1 skipped; Ruff clean. Recomputing all 18 evaluations in the real demo catalog under the corrected matcher gives **identical verdicts** — 4 quote matches, 0 full-rule matches, zero changed — so `acceptance.json` counts are unchanged and no legitimate quotation was penalized. Handoff on an isolated copy returns `[]`. All mutation-capable work used a scratchpad copy; `C:/Users/jason/quant-agent-brain-intake/exit-rules-final/external.sqlite` is byte-identical (sha256 `20ebc695…`). Production untouched: `strategy_cards`/`backtests`/`price_datasets`/`reviews` all 0, no `external_*` tables in `db/brain.sqlite`, `RQ-6d9c12f4` still `queued` with `raw_note_path NULL`, `gate_readiness.py --research-id RQ-6d9c12f4` still exits **4** with `brain.sqlite` byte-identical after the run.

**Known limitations.** (a) An em-dash-bound numeric range truncates undetected — a documented trade-off with 0 observed instances in the corpus. (b) `source_span` is a boundary check only: clipping a complete, meaning-bearing token (`Exit when RSI > 50` out of `...50 unless volume is below average`) matches by design; the safeguard there is `full_rule_match` plus the attributed reviewer's scope judgement, not the matcher. (c) Review attribution is a name, not authentication. **Gate D is not advanced and was not executed.**

## Verified closeout / limits

- Prior baseline was fast-forwarded and pushed to `main` (`e71b147`); only main/testing exist. The intake feature is now **committed and pushed on `testing`** after the P1 correction above was independently re-reviewed and approved. Still **not merged to `main`**.
- Final verification: **350 passed, 1 skipped**, Ruff clean. (The 321/1 figure below predates the P1 correction and its regression tests.)
- Canonical demo: `C:/Users/jason/quant-agent-brain-intake/exit-rules-final/acceptance.json`. All three PDFs extracted; 18 claims/citation leads, 17 distinct targets (not independent works). Counts of fetch outcomes below are per claim, not network calls. Final catalog reuses hash-checked snapshots from the earlier live run with original timestamps and reuse provenance. Both reimport and offline replay verified idempotent.
- 47 protected production files, question rows and tracked entity counts unchanged. No trusted promotion, Gate D, strategy or backtest executed.
- Automatic parsing is conservative: ChatGPT's unstructured sections remain citation leads requiring manual claim-to-source mapping. Four quote matches do not constitute four supported full exit rules. Handoff is empty; no evidence threshold was relaxed.
- Review role is attributed, not authenticated: this local CLI cannot establish that a reviewer is human. Source matching preserves operators but does not prove context or profitability. Do not call this production-ready before an independent review.
- Workflow and small learning note: `brain/_system/external_intake_workflow.md`.


> **External research intake implemented locally 2026-09-18 (branch `testing`, not merged).** A bounded retention lane for manually-collected external reports. **321 passed, 1 skipped**; Ruff clean. **Gate D was NOT executed and is NOT advanced.** `RQ-6d9c12f4` remains `queued` with `raw_note_path NULL`; `strategy_cards`/`backtests`/`price_datasets`/`reviews` all remain 0; `db/brain.sqlite` has no `external_*` tables; `scripts/gate_readiness.py --research-id RQ-6d9c12f4` still exits **4**.
>
> **What it does.** `scripts/external_intake.py` retains original PDFs, native `pypdf` text, per-report citations, deduplicated source targets and an append-only per-claim review history in an **isolated workspace database outside the repository and vault** (the workspace guard refuses any path inside either). Retention is not trust: a claim enters as `unreviewed_lead`, a deterministic verifier can only move it to `partially_supported`/`unresolved`/`blocked`, and **only an attributed reviewer scope review can set `supported_in_scope`** — which is the sole state the curator handoff will offer. The handoff builds its payload from the exact verified source span, not the report's transcription, and still has to pass the existing unmodified `promotion_block_reason`.
>
> **Real run over Jason's three reports:** 3 reports, 18 claims, **17 distinct targets** (ChartSchool is cited by 2 reports and counted once — repeated citation is not corroboration). Live verification: 13 fetched, 1 access-blocked, 3 content-rejected, 1 no-URL. **4 quotations located, 0 full-rule matches, so the curator handoff is correctly empty.** Two DOI/SSRN sources sit behind access walls and are parked with reasons, never circumvented. Re-importing all three is a no-op; re-verifying without `--allow-network` replays from cached snapshots in <1s.
>
> **Reproduce:**
> ```
> uv run python scripts/external_intake.py --workspace C:/tmp/ext_demo import "<pdf>" --provider <name> --research-id RQ-6d9c12f4
> uv run python scripts/external_intake.py --workspace C:/tmp/ext_demo verify --allow-network --limit 20
> uv run python scripts/external_intake.py --workspace C:/tmp/ext_demo leads
> uv run python scripts/external_intake.py --workspace C:/tmp/ext_demo handoff
> ```
>
> Governance: **PROP-002** in `brain/_system/plan/plan_change_proposals.md` (accepted, authorized before implementation) plus the §5 amendment in `PLAN.md`. Still needing separate approval: OCR/further extraction deps, relaxing the ≥3-source bar, and any production promotion.
>
> **Gate D attempted 2026-09-17 — BLOCKED, no child question executed.** Prerequisites were checked before any run. `RQ-6d9c12f4`, `RQ-c920baeb`, `RQ-80be8cf7` remain `queued` with no raw note; `strategy_cards`/`backtests`/`price_datasets`/`reviews` all remain 0. **284 passed, 1 skipped**; Ruff clean. Work is on `testing`, **not merged to `main`**.
>
> **Three code defects found and fixed.** (1) `default_runner` decoded subprocess output with the locale codec (`cp1252`) while `agent-reach doctor --json` emits UTF-8 — the `UnicodeDecodeError` fired on subprocess's reader thread, nulled `stdout`, and surfaced as a misleading `TypeError`. Every live discovery call was broken on this machine. (2) The adapter looked for channels `"search"`/`"exa"`; the real doctor key is `exa_search`, so the Exa lane could never be selected. The recorded fixture repeated the same invented names — which is why a green suite carried this through a whole gate. (3) `plan_queries` sent the full 440-character question to `gh search`, which rejects long queries as malformed, misreporting a query error as an empty result.
>
> **The blocker is not a defect and was not fixed:** `exa_search` reports `status: "off"` — mcporter installed, Exa not configured, no config and no `EXA_*` env vars. That is Jason's decision; project code must never call `agent-reach`/`mcporter configure`.
>
> **Say the blocker precisely.** It is *not* "no usable lane". `github` is `warn`, which the code correctly treats as usable, so discovery would run **GitHub-only** — the sweep Gate C exists to prevent. The blocker is that the only lane able to answer these questions is `off`, GitHub returns **0 results for all three children**, and Phase 6 requires **≥3 upstream sources per raw note**.
>
> **Reproduce:** `uv run python scripts/gate_readiness.py --research-id RQ-6d9c12f4` → exit **4**. Read-only: no fetch, no snapshot, no model, and `db/brain.sqlite` is byte-identical afterwards. The general `agent_reach_check.py` exits **0**, correctly — GitHub genuinely is usable, and a lane is not unhealthy merely because it suits a question poorly. **Do not mistake that 0 for Gate D readiness.**
>
> **Gate C verified 2026-09-16.** Bounded source acquisition now discriminates by credibility before spending a fetch or a model call. `discovery/source_quality.py` makes the written Tier A/B/C/D policy executable (structural host/path signals + allowlists + a commercial-intent reject detector that runs first); `discovery/acquisition.py` adds normalize → dedupe → classify → rank → budget plus a 600-char/120-word content floor. The central unlock: live discovery previously hardcoded `source_quality="discovery-only"` while the curator only promotes `primary`/`practitioner`, so the live path could never promote anything it found. Tiers are now assigned discovery-side, the only correct placement given the validators' protected-field guard. **269 passed, 1 skipped**; Ruff clean on both invocations. PR #3 was merged first (`2a876f7`). The three child questions remain **queued** — Gate C ran none of them.
>
> Acceptance demonstration: `uv run python scripts/acquisition_report.py` — zero network, finds 3 primary + 1 practitioner, rejects promotional material pre-fetch and a cookie banner post-fetch/pre-model, collapses a cross-channel duplicate, exits non-zero on any failed check.
>
> **Gate D is next and requires Jason's explicit authorization.**
>
> **Gate B verified 2026-09-11.** The production live Research Scout passes fetched snapshots through `quant_brain.llm.qwen_call`: qwen3:14b at temperature 0/schema mode, deterministic validation, exactly one 14B repair, qwen3.8:27b escalation, then structured fail closed. Every attempt records model, duration, prompt/response SHA-256 hashes, and validator verdict/reasons in `agent_events`. Durable promotion requires fully extractive main claims and strategy rules; late write failures restore/delete notes consistently; dispatcher validation failures finalize tasks as failed. Hermetic and adversarial tests pass (**201 passed, 1 skipped**), with full-tree/scoped Ruff clean. Phase 6 remains pending; Gate C is next.
>
> **Gate A verified 2026-09-07.** Desktop `main` was safely fast-forwarded from `f053341` to merged PR #1 commit `feaa84e86db5b435cf12a21d65e7e924cd116bbb`, then the pre-existing tracked and untracked work was reapplied. The exact backup directory is `C:\Users\jason\quant-agent-brain-gate-a-backup-20260907-171959`; it contains `tracked-worktree.patch`, `tracked-index.patch`, `untracked.tar.gz`, `untracked-list.txt`, `head-before.txt`, `status-before.z`, and related inventory files. The backup branch and retained stash also preserve the pre-integration state.
>
> The reviewed PR implementation is the production Scout path: registry/dispatcher → `quant_brain.discovery` → recommendation only. Pre-existing untracked `src/quant_brain/research/live_*.py` and dashboard files remain preserved as experimental local work; they are not a competing accepted architecture.
>
> `RQ-66078766` remains an **experimental audit receipt**, including raw research, rejected curator review, source snapshots, failed-run material, and decision log. The real child queue remains untouched: `RQ-6d9c12f4`, `RQ-c920baeb`, and `RQ-80be8cf7`. Do not execute them until the later roadmap gate is explicitly approved.
>
> Gate A verification: `uv sync --extra dev` succeeded; full pytest passed (`149 passed, 1 skipped`); Ruff passed with immutable failed-run audit artifacts explicitly excluded in `pyproject.toml` (maintained `src`, `tests`, and `scripts` remain lint-clean); discovery registry and child dry-run resolved to `research_scout`; Agent Reach health was inspectable, with web/RSS/Bilibili healthy and optional-channel warnings/off states. No research, strategy card, backtest, paper trade, remote push, or remote merge was performed.
>
> **Read `PLAN.md` first.** It remains the master architecture source of truth. Use `.hermes/plans/2026-09-07_171423-research-to-paper-trading-roadmap.md` for the gated execution sequence, and do not silently rewrite master phases.

Use this file to resume work in a new Hermes session without reloading the full conversation.

## Project Path

`C:\Users\jason\OneDrive\Desktop\quant-agent-brain`

## Current Goal

Build a budget-first, local-first agentic quant research/backtesting second-brain system that showcases AI/ML skills without overengineering or creating an agent for every tiny task.

Core idea:

```text
research structure + RAG structure + controlled work packets
```

## User Preferences For This Project

- Move slowly, one verified step at a time.
- Avoid overengineering.
- Do not delegate an agent for every small thing.
- Prefer local/free tools first.
- Use paid/cloud models only for escalation/review later.
- Build like a serious quant research workflow: evidence first, backtests second, review before any paper trading.
- No live trading.

## What Has Been Built

### 1. Project foundation

- `pyproject.toml`
- `README.md`
- `AGENTS.md`
- `.gitignore`
- `.env.example`
- `src/quant_brain/`
- `tests/`

Python uses `uv`.

Latest verified test count:

```text
149 passed
1 skipped
```

### 2. SQLite database

Database path:

```text
db/brain.sqlite
```

Schema/init code:

```text
src/quant_brain/db/schema.sql
src/quant_brain/db/init_db.py
```

Important tables:

```text
notes
sources
chunks
embeddings
research_questions
research_findings
strategy_cards
price_datasets
backtests
metrics
reviews
agent_tasks
retrieval_log
```

### 3. Market data foundation — historical claim, not current capability

Earlier handoffs claimed market-data downloader/registry modules and downloaded SPY/QQQ/IWM data. Those modules are not present in the reconciled source tree, and the current database has **`price_datasets = 0`**. Do not infer that usable price files or registrations exist. Roadmap **Gate F** owns restoring reproducible files, provider/date/calendar/adjustment metadata, checksums, and SQLite registrations before any backtest.

### 4. Research intake system

Files:

```text
src/quant_brain/research/intake.py
scripts/research_intake.py
brain/_system/research_intake_workflow.md
```

Creates research questions and briefs.

Existing research task:

```text
RQ-4ddd4ef4
Question: Find useful sources for ETF mean reversion strategies and summarize only methods that can be tested with daily SPY QQQ IWM data
Status: curated
```

### 5. Research Scout runner/executor

Files:

```text
src/quant_brain/research/scout_runner.py
scripts/research_scout_runner.py
src/quant_brain/research/executor.py
scripts/research_executor.py
agents/research_scout.md
```

Output raw research note:

```text
brain/00_Inbox/Raw_Research/RQ-4ddd4ef4.md
```

The first executor is intentionally conservative and deterministic, not a web crawler yet.

### 6. Curator promotion/executor

Files:

```text
src/quant_brain/curation/promotion.py
scripts/curator_promotion.py
src/quant_brain/curation/executor.py
scripts/curator_executor.py
agents/knowledge_curator.md
```

Curated `RQ-4ddd4ef4` and promoted 5 source notes:

```text
brain/01_Sources/web/SRC-df1769724d-relative-strength-index-rsi-investopedia-overview.md
brain/01_Sources/docs/SRC-2830f8cd41-quantconnect-glossary-look-ahead-bias.md
brain/01_Sources/docs/SRC-7691c731ac-quantconnect-glossary-survivorship-bias.md
brain/01_Sources/docs/SRC-26d92ac325-backtesting-py-documentation.md
brain/01_Sources/docs/SRC-022c5bed68-vectorbt-documentation.md
```

Curator review:

```text
brain/00_Inbox/Curator_Reviews/RQ-4ddd4ef4-curated.md
```

### 7. Markdown indexer

Files:

```text
src/quant_brain/indexing/markdown_indexer.py
scripts/index_markdown.py
brain/_system/markdown_indexer_workflow.md
```

Indexes Markdown notes into:

```text
notes
chunks
```

Current indexed count at last run:

```text
23 Markdown files
260 chunks
```

### 8. Embedding indexer

Files:

```text
src/quant_brain/indexing/embeddings.py
scripts/embed_chunks.py
brain/_system/embedding_indexer_workflow.md
```

Uses real local semantic embeddings through Ollama:

```text
nomic-embed-text
768 dimensions
```

The deterministic `local-hash-embedding-v1` backend remains available only as an offline/test fallback.

Current embedding count at last run:

```text
260 embeddings
0 pending chunks
```

Later scaling options:

```text
Ollama mxbai-embed-large
sentence-transformers/all-MiniLM-L6-v2
LanceDB or Chroma
```

### 9. Retrieval context builder

Files:

```text
src/quant_brain/retrieval/context_builder.py
scripts/build_context.py
brain/_system/retrieval_context_builder_workflow.md
```

Builds an agent-ready evidence packet:

```text
query
source path
heading
chunk id
score
chunk text
rules to cite evidence and avoid guessing
```

### 10. Agent work packet builder

Files:

```text
src/quant_brain/agents/work_packet.py
scripts/build_work_packet.py
brain/_system/agent_work_packet_builder_workflow.md
```

Creates work packets with:

```text
agent role
specific task
retrieved context
allowed read paths
allowed write paths
output contract
guardrails
```

Latest sample packet:

```text
brain/00_Inbox/Work_Packets/WP-3818c6a760-knowledge_curator.md
```

It asked the Knowledge Curator to review whether lookahead bias should update the validation checklist.

### 11. Deterministic Work Packet Executor

Files:

```text
src/quant_brain/agents/executor.py
scripts/execute_work_packet.py
tests/test_work_packet_executor.py
brain/_system/work_packet_executor_workflow.md
```

The first executor is intentionally narrow and deterministic. It:

```text
parses one bounded packet
→ verifies retrieved evidence
→ enforces project-relative allowed write paths
→ writes a cited Markdown result
→ validates path + heading citations
→ updates agent_tasks running/completed/failed state
```

Unsupported tasks fail closed instead of receiving a fabricated generic answer. No local or cloud model is called yet.

Verified real execution:

```text
Packet: WP-3818c6a760
Status: completed
Output: brain/00_Inbox/Curator_Reviews/WP-3818c6a760-result.md
Citations validated: 1
```

The Markdown indexer was also hardened for repeated identical heading/text sections inside one note. Duplicate occurrences now receive distinct chunk IDs instead of raising a SQLite uniqueness error.

### 12. Canonical Pre-Backtest Validation Checklist

File:

```text
brain/_system/pre_backtest_validation_checklist.md
```

The completed work-packet recommendation was reviewed and promoted into a short system checklist. Version 1 contains one evidence-backed gate only:

```text
confirm all signal inputs were available at decision time
→ close-based signals execute no earlier than the next bar unless timing proves otherwise
→ failing configurations stop before performance is reported
```

The checklist cites the curated QuantConnect lookahead-bias source. It intentionally does not add speculative validation rules yet.

### 13. First Strategy Door

File:

```text
brain/02_Strategy_Doors/DOOR-etf-mean-reversion.md
```

The door maps the daily SPY/QQQ/IWM ETF mean-reversion family without creating a strategy card. It currently identifies RSI oversold rebound as the only candidate with enough support for another focused research pass.

### 14. Focused RSI Definition Research

Research task:

```text
RQ-17a4103d
Status: curated
```

New curated sources:

```text
brain/01_Sources/docs/SRC-1ea110cb46-stockcharts-chartschool-relative-strength-index-rsi.md
brain/01_Sources/docs/SRC-89c682a686-ta-lib-documentation-relative-strength-index-rsi.md
```

This pass captured Wilder's formula and bounded the entry-condition research space to:

```text
RSI(14) below 30 at the close
RSI(2) below 20 at the close
next-bar entry for either candidate
```

It did not find enough evidence to approve an exit rule or maximum holding period, so no strategy card or backtest was created.

A follow-up task was originally queued, then used only by the preserved experimental
live-research work described below. It is not a production acceptance receipt:

```text
RQ-dd7da469
Question: Find source-supported exit conditions, maximum holding periods, timing/regime risks, and fixed cost assumptions for the bounded RSI candidates.
Current artifact status: rejected (experimental history; not accepted)
```

### 15. Agent Reach Live-Research Connection

Canonical repository:

```text
https://github.com/Panniantong/Agent-Reach
```

Verified local connection:

```text
Version: 1.5.0
Clone: C:/Users/jason/Projects/Agent-Reach-review
Executable: C:/Users/jason/.agent-reach-venv/Scripts/agent-reach.exe
Obsidian skill: C:/Users/jason/OneDrive/Desktop/memory_vault/Agents/skills/agent-reach/SKILL.md
```

Agent Reach is now named in `AGENTS.md`, the Research Scout role, and generated Research Scout prompts. It is used as a discovery router for web pages, YouTube transcripts, GitHub, RSS, and social leads. Durable notes cite upstream sources rather than Agent Reach itself.

### 16. Cross-Asset Quant Research Universe and Quality Gate

Files:

```text
brain/80_Summaries/quant-research-universe.md
brain/_system/research_source_quality_policy.md
brain/_system/citations/quant-universe-ledger.json
```

The grounded scan used official institutional research, trading-firm pages, practitioner interviews, and YouTube transcripts from AQR, Man Group/Man AHL, Two Sigma, HRT, Jane Street, Wintermute, BlackRock, Aspect Capital, and J.P. Morgan.

The project is explicitly open to:

```text
equities and ETFs
futures / rates / FX / commodities
options and volatility
crypto and digital assets
factor/style premia
systematic macro and trend following
statistical arbitrage / relative value / mean reversion
market making and liquidity
alternative data / machine learning
portfolio construction and risk allocation
```

This is a research universe, not an approval list. The curator now promotes only `primary` or `practitioner` source-quality items; `discovery-only` material can create leads but cannot independently enter durable source notes. The policy rejects untraceable returns, screenshots without rules/data/costs, copied summaries, hidden assumptions, and invented citations.

### 17. Local Qwen Research Evaluation

Files:

```text
src/quant_brain/research/model_eval.py
scripts/evaluate_research_model.py
tests/test_research_model_eval.py
brain/00_Inbox/Model_Evaluations/qwen-research-evaluation.md
brain/00_Inbox/Model_Evaluations/qwen3-14b-research-eval-v4.json
brain/00_Inbox/Model_Evaluations/qwen3.8-27b-research-eval-v2.json
brain/_system/local_qwen_research_policy.md
```

Models and hardware:

```text
qwen3:14b       9.3 GB
qwen3.8:27b    17 GB
GPU: NVIDIA GeForce RTX 5070, 12 GB VRAM
```

Final bounded evaluation results:

```text
qwen3:14b      3/3 passed, 17.740 seconds total, 2 cases repaired
qwen3.8:27b   3/3 passed, 123.972 seconds total, 0 cases repaired
```

The cases tested missing-evidence honesty, slop rejection, and cross-asset source-grounded mapping. A stronger validator caught a direct contradiction in an early 14B answer; one bounded repair corrected it. Therefore 14B is approved only as the default evidence-processing worker behind schema, source-ID, validator, and one-repair gates. The slower 27B model is the escalation/reviewer.

### 18. Experimental Local History — Not Production

The following files and run records are preserved because they are useful audit history.
They were pre-existing untracked local work when Gate A was reconciled. They do **not**
replace, extend, or prove acceptance of the registry/dispatcher architecture in `PLAN.md`.

#### Experimental live-research prototype

Files:

```text
src/quant_brain/research/live_discovery.py
src/quant_brain/research/live_worker.py
src/quant_brain/research/live_executor.py
scripts/live_research_executor.py
brain/_system/live_research_executor_workflow.md
```

The prototype attempted this bounded flow:

```text
Agent Reach health check
→ upstream web search
→ deterministic dedupe/ranking
→ Jina source snapshots + hashes
→ bounded Qwen 14B extraction
→ exact source/URL/quote validation
→ one repair
→ Qwen 27B escalation
→ raw research note
→ curator gate
→ ordered SQLite events
```

Experimental rejected run (not an acceptance run):

```text
Research: RQ-dd7da469
Run: RUN-rsi-exit-live-v5
Sources fetched: 3
Qwen 14B: two exact-quote validation failures
Qwen 27B: passed validation
Curator: rejected all 3 discovery-only sources
```

The rejection is retained as quality-gate evidence only. It did not accept the Scout,
promote sources, resolve the RSI evidence gaps, or authorize another stage.

#### Experimental operations dashboard

Files:

```text
src/quant_brain/ops/events.py
src/quant_brain/ops/dashboard.py
scripts/serve_agent_dashboard.py
ui/agent_dashboard.html
brain/_system/agent_operations_dashboard_workflow.md
brain/07_Decision_Log/DEC-agent-operations-dashboard.md
```

Historical prototype launch command:

```bash
uv run python scripts/serve_agent_dashboard.py
```

Local URL:

```text
http://127.0.0.1:8765
```

This dashboard is preserved experimental UI. It is not the production interface, not a
Gate A deliverable, and not part of the canonical execution path.

## Canonical Current Architecture

`PLAN.md` is authoritative. Gate A recognizes only this production Scout path:

```text
agent registry + typed capability
→ dispatcher selects research_scout
→ quant_brain.discovery performs the bounded discovery task
→ validated output
→ recommendation only
→ harness/human decides whether any later task is authorized
```

The `src/quant_brain/research/live_*.py` modules, experimental dashboard, and their
workflows are outside that path. Do not package, promote, or describe them as current
production. As of 2026-09-16 they live on `preserve/live-research-and-dashboard-20260916`
and are no longer in the working tree — being on a branch does not make them accepted.

## Merged Checkpoint (2026-09-15)

Gate B was merged to `main` as `fb3ecc3` (PR #2). Local `main` is synchronized with it by
fast-forward; the merge introduced no upstream edits, so the accepted Gate A/B code is
byte-identical to the reviewed checkpoint. Recovery tag: `pre-gatec-reconcile-20260915`.

Verified after reconciliation: 210 passed / 1 skipped, Ruff clean on both invocations,
child RQs queued, `RQ-66078766` rejected, and `strategy_cards` / `backtests` /
`price_datasets` / `reviews` all zero. (That 210 included 13 experimental tests — see
the test-baseline note below.)

### Deliberately uncommitted work — resolved 2026-09-16

The working tree is now clean. Everything previously held back has been classified and
routed. Decision note:
[brain/07_Decision_Log/DEC-2026-09-16-phase-3-indexing-checkpoint.md](brain/07_Decision_Log/DEC-2026-09-16-phase-3-indexing-checkpoint.md).

- **Phase 3 semantic-RAG edits** — reviewed on their own merits and **accepted** on
  `phase-3/indexing-and-retrieval-eval` (`b236175`), PR open and **awaiting Jason's approval;
  not merged**. Excludes `Source_Snapshots` from the index, removes a retrieval fixture that
  was *unreachable* (its target lives in the excluded `_system/`, so it could never be
  retrieved), and makes a dimension mismatch raise instead of returning an empty list.
  Re-verified: Recall@1 0.71, Recall@5 1.00, MRR 0.790 across 7 now-reachable fixtures.
- **Gate C-adjacent scaffolding** — `src/quant_brain/research/live_{discovery,executor,worker}.py`,
  `src/quant_brain/ops/dashboard.py`, `ui/`, `scripts/{live_research_executor,serve_agent_dashboard,gate_b_live_smoke}.py`
  and their 4 test files. **Preserved** on `preserve/live-research-and-dashboard-20260916`
  (`7a7209e`), pushed. Audit history only — never reviewed in PR #2, not the accepted
  architecture, not to be merged.
- `.hermes/` and `src/quant_agent_brain.egg-info/` are now gitignored; the egg-info was
  untracked with `git rm --cached` (files remain on disk). It is regenerated by every
  editable install and produced diff noise unrelated to any real change.

Promoting any preserved work into production requires its own reviewed change, not a
carry-over from this reconciliation.

### Test baseline — read this before comparing numbers

The **210 passed** figure recorded for the Gate B merge included 13 tests from the
then-untracked experimental files. The tracked-only baseline at that commit was
**197 passed, 1 skipped**. With the Phase 3 branch's `tests/test_retrieval_eval.py` (2 tests)
the current tracked baseline is **199 passed, 1 skipped**. The experimental tests now live on
the preserve branch and no longer inflate a run on `main`.

### Known issue — `retrieval_eval.py --compare` is broken

It compares the semantic backend against the `local-hash-embedding-v1` baseline, but the hash
vectors are absent from `db/brain.sqlite` (only `nomic-embed-text@768`), despite the Phase 3
design note saying to keep them for this purpose — most likely lost to the documented
re-index-drops-embeddings behavior. **Pre-existing, not caused by the Phase 3 branch**; it
previously failed *silently* as recall 0.00 and now raises. Fixing it requires re-embedding
every chunk under the hash model, which writes to the database — deliberately not done. The
single-model run that gates Phase 3 is unaffected.

## Gate Status and Resume Rule

Gate A reconciliation, Gate B / master-plan Phase 5, and Gate C are complete. **Gate D was
authorized and attempted on 2026-09-17, and is blocked on an unconfigured search lane — not
on authorization.** No child question was executed; all three remain `queued`.

**Re-attempting Gate D requires a usable search lane that can answer documentation and
academic questions.** That is Jason's decision: Exa is a third-party service, and he has
said to enable it only if it is genuinely free with no API key. Project code must never run
`agent-reach`/`mcporter configure`. Before assuming the blocker still stands, run
`uv run python scripts/gate_readiness.py --research-id RQ-6d9c12f4` — exit 4 means still
blocked, exit 0 means the lanes can now reach the minimum.

When a lane is available, Gate D runs the three child research questions one at a time, in
order: `RQ-6d9c12f4` (exit rules), `RQ-c920baeb` (maximum holding periods), `RQ-80be8cf7`
(commission/slippage). Each needs its own dispatch, snapshot set, validated raw note, event
trail, and a **separately dispatched** curator verdict, with tests run before the next child
starts. Zero promotions is an acceptable outcome.

Nothing here authorizes a strategy card, market-data download, backtest, or paper trading.
Follow the explicit gated roadmap and do not infer a production step from the experimental
run history. Until Gate D is authorized, preserve `RQ-6d9c12f4`, `RQ-c920baeb`, and
`RQ-80be8cf7` in `queued` without executing them.

### Acquisition lane status (Gate C)

| Lane | Status | Notes |
|---|---|---|
| Exa via mcporter | declared operational, **currently off** | Primary search channel. `exa_search` reports `status: off` (Exa not configured) as of 2026-09-17 — this is the Gate D blocker |
| GitHub via `gh` | operational | Top-up only when search is short of the cap |
| arXiv `/abs/` | fixture-only | `/pdf/` → `/abs/` rewrite; promotes hits already found. No API client, no PDF parser |
| YouTube, RSS | deferred | Declared so doctor output maps cleanly; never dispatched |
| Reddit, X, Facebook, Instagram, XiaoHongShu, LinkedIn | never | Login-backed; appear in no lane |

## Commands To Verify State

```bash
cd C:/Users/jason/OneDrive/Desktop/quant-agent-brain
uv run pytest -q
uv run ruff check . --no-cache
uv run ruff check src tests scripts
uv run python -m quant_brain.harness.registry --task-type discovery --json
uv run python scripts/dispatch_task.py --type discovery --research-id RQ-6d9c12f4 --dry-run

# Gate C acceptance demonstration (offline, no database writes)
uv run python scripts/acquisition_report.py

# Which lanes are usable right now? (exit 0 = at least one; 3 = none)
uv run python scripts/agent_reach_check.py

# Can those lanes answer a specific question? (exit 0 = ready; 4 = not)
uv run python scripts/gate_readiness.py --research-id RQ-6d9c12f4
```

## Important Design Rule

Do not overengineer. This is not yet a fully autonomous AI quant firm. Build reliable primitives first:

```text
queue → evidence → curation → retrieval → bounded work packets → review
```

Only add more automation after the loop is verified.

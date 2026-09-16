# Quant Agent Brain — Session Handoff

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
production merely because their artifacts remain on disk.

## Merged Checkpoint (2026-09-15)

Gate B was merged to `main` as `fb3ecc3` (PR #2). Local `main` is synchronized with it by
fast-forward; the merge introduced no upstream edits, so the accepted Gate A/B code is
byte-identical to the reviewed checkpoint. Recovery tag: `pre-gatec-reconcile-20260915`.

Verified after reconciliation: 210 passed / 1 skipped, Ruff clean on both invocations,
child RQs queued, `RQ-66078766` rejected, and `strategy_cards` / `backtests` /
`price_datasets` / `reviews` all zero.

### Deliberately uncommitted work

Preserved in the working tree, **not** in production, and not silently promoted:

- **Gate C-adjacent scaffolding** — `src/quant_brain/research/live_{discovery,executor,worker}.py`,
  `src/quant_brain/ops/dashboard.py`, `ui/`, `scripts/{live_research_executor,serve_agent_dashboard,gate_b_live_smoke}.py`
  and their tests. These pass (13 tests) but were excluded from PR #2 review.
- **Phase 3 semantic-RAG edits** — `src/quant_brain/indexing/{embeddings,markdown_indexer}.py`,
  `scripts/retrieval_eval.py`, `tests/test_markdown_indexer.py`. Substantive and tested
  (they exclude `Source_Snapshots` from indexing), but they belong to Phase 3 rather than the
  Gate B checkpoint and need their own review.
- `.hermes/` planning notes and `src/quant_agent_brain.egg-info/` build metadata.

Promoting any of the above into production requires its own reviewed change, not a
carry-over from this reconciliation.

## Gate Status and Resume Rule

Gate A reconciliation and Gate B / master-plan Phase 5 are complete and merged. Jason has
authorized roadmap Gate C, which is next. This does not authorize research
execution (Gate D), a strategy card, a backtest, or paper trading. Follow the explicit
gated roadmap and do not infer a production step from the experimental run history.
Preserve the queued child research
questions `RQ-6d9c12f4`, `RQ-c920baeb`, and `RQ-80be8cf7` without executing them.

## Commands To Verify State

```bash
cd C:/Users/jason/OneDrive/Desktop/quant-agent-brain
uv run pytest -q
uv run ruff check . --no-cache
uv run ruff check src tests scripts
uv run python -m quant_brain.harness.registry --task-type discovery --json
uv run python scripts/dispatch_task.py --type discovery --research-id RQ-6d9c12f4 --dry-run
```

## Important Design Rule

Do not overengineer. This is not yet a fully autonomous AI quant firm. Build reliable primitives first:

```text
queue → evidence → curation → retrieval → bounded work packets → review
```

Only add more automation after the loop is verified.

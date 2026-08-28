# Quant Agent Brain — Session Handoff

> **⚠️ READ `PLAN.md` FIRST.** As of 2026-08-28 the source of truth for what to build and in what order is [PLAN.md](PLAN.md), with per-phase detail in [brain/_system/plan/](brain/_system/plan/). Start at **PLAN.md §9 "Handoff Checkpoint"** — it carries the live phase-status table.
>
> This file is now a **historical record of what was built**, useful for context. Where this file and `PLAN.md` disagree about *next steps*, **`PLAN.md` wins**.
>
> **Known stale below:** the "49 passed" test count is no longer true — `tests/test_agent_events.py` imports `quant_brain.ops`, which does not exist, so the suite fails at collection. Repairing that is Phase 0.
>
> The "Next Best Step" section at the bottom has been superseded by the phased plan: the Live Research Discovery Executor is now **Phase 4**, and it depends on Phase 0 (event store), Phase 1 (real semantic embeddings), Phase 2 (Agent Reach adapter), and Phase 3 (Qwen runtime + validators) landing first.

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
49 passed
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

### 3. Market data downloader

Files:

```text
src/quant_brain/data/price_data.py
scripts/download_prices.py
src/quant_brain/data/dataset_registry.py
scripts/register_datasets.py
```

Downloaded/registered daily yfinance data for:

```text
SPY
QQQ
IWM
```

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
21 Markdown files
233 chunks
```

### 8. Embedding indexer

Files:

```text
src/quant_brain/indexing/embeddings.py
scripts/embed_chunks.py
brain/_system/embedding_indexer_workflow.md
```

Uses temporary local deterministic embeddings:

```text
local-hash-embedding-v1
```

This proves RAG plumbing before upgrading to real semantic embeddings.

Current embedding count at last run:

```text
233 embeddings
0 pending chunks
```

Later upgrade path:

```text
Ollama nomic-embed-text
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

A follow-up task is queued:

```text
RQ-dd7da469
Question: Find source-supported exit conditions, maximum holding periods, timing/regime risks, and fixed cost assumptions for the bounded RSI candidates.
Status: queued
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

## Current Architecture

```text
Research structure:
Agent Reach / papers / practitioner discovery
→ research queue
→ Research Scout runner
→ bounded source discovery/fetch
→ Qwen 14B evidence extraction (validated; one repair max)
→ Qwen 27B escalation when needed
→ raw research note
→ Curator executor
→ curated source notes

RAG structure:
Markdown notes
→ heading chunks
→ embeddings
→ retrieval context packet

Agent execution structure:
agent role file
→ work packet builder
→ bounded task + evidence + allowed read/write paths
→ deterministic executor
→ cited result + database audit state
```

## Next Best Step

Build **Live Research Discovery Executor v1** and use queued task `RQ-dd7da469` as its acceptance test.

The executor should:

1. Run the Agent Reach health check.
2. Discover a bounded candidate set through upstream web/paper/YouTube/GitHub channels.
3. Fetch and snapshot no more than five strong sources.
4. Give only bounded evidence with source IDs to `qwen3:14b`.
5. Validate schema, citations, source quality, contradictions, and invented strategy rules.
6. Allow one repair; escalate to `qwen3.8:27b` or fail closed if validation still fails.
7. Send validated raw research to the curator.

Recommended scope for the next session:

- Find at most two source-supported exit/holding-period choices.
- Record fixed transaction-cost assumptions without pretending they are universal.
- Preserve timing and regime risks.
- Do not create a strategy card or run a backtest yet.
- Update the Strategy Door only if the evidence actually resolves the open gaps.
- Preserve the cross-asset research map as a backlog, not dozens of parameter variations.
- After the first end-to-end pipeline works, open the next independent door: multi-asset trend following using realistic futures data or a clearly labeled ETF proxy.

## Commands To Verify State

```bash
cd C:/Users/jason/OneDrive/Desktop/quant-agent-brain
uv run pytest -q
uv run python scripts/index_markdown.py index
uv run python scripts/embed_chunks.py embed
uv run python scripts/build_context.py "lookahead bias future data" --limit 3
```

## Important Design Rule

Do not overengineer. This is not yet a fully autonomous AI quant firm. Build reliable primitives first:

```text
queue → evidence → curation → retrieval → bounded work packets → review
```

Only add more automation after the loop is verified.

---
id: WP-47970e3b48
type: agent_work_packet
agent_role: knowledge_curator
status: ready
retrieval_query_id: QUERY-9865620cfe
---

# Agent Work Packet — WP-47970e3b48

## Agent Role

knowledge_curator

## Task

Review whether lookahead bias should update the validation checklist before any strategy backtest

## Role Instructions

# Knowledge Curator Agent

## Job

Turn messy research into clean source notes, method-door updates, and eventually strategy cards.

## Inputs

- Research brief from `brain/00_Inbox/Research_Briefs/`
- Raw findings from `brain/00_Inbox/`
- Existing method doors in `brain/02_Strategy_Doors/`
- Existing source notes in `brain/01_Sources/`

## Output

One of these verdicts:

- `promote_source`
- `update_door`
- `create_strategy_card`
- `needs_more_work`
- `rejected`

## Promotion Rules

Promote information only when it is useful and traceable.

A source note should preserve:

- citation / URL / book or paper identity
- summary
- useful claims
- evidence or unverified label
- possible strategy rules
- risks and caveats
- confidence level

## Write Locations

- Curator reviews: `brain/00_Inbox/Curator_Reviews/`
- Source notes: `brain/01_Sources/`
- Door updates: `brain/02_Strategy_Doors/`
- Strategy cards: `brain/03_Strategy_Cards/`

## Rules

- Do not let raw hype into the durable brain.
- Do not turn every source into a strategy.
- Do not create a strategy card until rules are precise enough to backtest.
- Preserve uncertainty instead of making claims sound stronger than they are.

## Retrieved Context

# Retrieved Context Packet

## Query

lookahead bias future data backtest validation

## How To Use

Use this context as evidence, not as proof. Cite the file path and heading when making claims. If the context is weak or missing, say so instead of guessing.

## Retrieved Chunks

### Context 1

- chunk_id: CHUNK-2003feec052d5854
- note_id: RQ-4ddd4ef4-raw_research
- path: brain/00_Inbox/Raw_Research/RQ-4ddd4ef4.md
- heading: Research Scout Task > Research Question
- score: 0.2500

```text
## Research Question

Find useful sources for ETF mean reversion strategies and summarize only methods that can be tested with daily SPY QQQ IWM data
```

### Context 2

- chunk_id: CHUNK-2620afb5d99c5b52
- note_id: RQ-4ddd4ef4-research_brief
- path: brain/00_Inbox/Research_Briefs/RQ-4ddd4ef4.md
- heading: Research Brief — RQ-4ddd4ef4 > Research Question
- score: 0.2500

```text
## Research Question

Find useful sources for ETF mean reversion strategies and summarize only methods that can be tested with daily SPY QQQ IWM data
```

### Context 3

- chunk_id: CHUNK-879da49dc6035461
- note_id: RQ-4ddd4ef4-raw_research
- path: brain/00_Inbox/Raw_Research/RQ-4ddd4ef4.md
- heading: Raw Research Note — RQ-4ddd4ef4 > Research Question
- score: 0.2500

```text
## Research Question

Find useful sources for ETF mean reversion strategies and summarize only methods that can be tested with daily SPY QQQ IWM data
```

### Context 4

- chunk_id: CHUNK-80f356a100c154b0
- note_id: RQ-4ddd4ef4-raw_research
- path: brain/00_Inbox/Raw_Research/RQ-4ddd4ef4.md
- heading: Research Scout Task > Hard Boundaries
- score: 0.2164

```text
## Hard Boundaries

- Do not create strategy cards.
- Do not run backtests.
- Do not paper trade or live trade.
- Do not claim a strategy works just because a source says so.
- Do not illegally download copyrighted books.
- Save messy findings under `brain/00_Inbox` only.
```

### Context 5

- chunk_id: CHUNK-c2ddf38294675f61
- note_id: RQ-4ddd4ef4-research_brief
- path: brain/00_Inbox/Research_Briefs/RQ-4ddd4ef4.md
- heading: Research Brief — RQ-4ddd4ef4 > Rules
- score: 0.2041

```text
## Rules

- Do not download copyrighted books illegally.
- Use high-quality sources, public papers, official docs, public repos, previews, or user-provided files.
- Cite every source.
- Label uncertain claims as `unverified`.
- Prefer fewer high-quality sources over many weak sources.
- Do not paper trade or live trade anything.
```

## Allowed Read Paths

- `brain/01_Sources/`
- `brain/_system/`

## Allowed Write Paths

- `brain/00_Inbox/Curator_Reviews/`
- `brain/_system/`

## Output Contract

Return a curator note with recommendation, cited source paths/headings, and exact proposed checklist change. Do not edit files directly yet.

## Guardrails

- Do not edit outside allowed write paths.
- Cite source file paths/headings from retrieved context.
- If context is weak, say what is missing instead of guessing.
- Do not create strategy cards unless this packet explicitly asks for that.
- Do not run backtests unless this packet explicitly asks for that.
- Do not paper trade or live trade.

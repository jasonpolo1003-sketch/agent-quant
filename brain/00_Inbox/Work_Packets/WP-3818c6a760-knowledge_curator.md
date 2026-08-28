---
id: WP-3818c6a760
type: agent_work_packet
agent_role: knowledge_curator
status: ready
retrieval_query_id: QUERY-19f182e2fc
---

# Agent Work Packet — WP-3818c6a760

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

strategy can appear profitable cheats future data

## How To Use

Use this context as evidence, not as proof. Cite the file path and heading when making claims. If the context is weak or missing, say so instead of guessing.

## Retrieved Chunks

### Context 1

- chunk_id: CHUNK-fc25b9a122a15856
- note_id: SRC-2830f8cd41
- path: brain/01_Sources/docs/SRC-2830f8cd41-quantconnect-glossary-look-ahead-bias.md
- heading: Source — QuantConnect glossary — Look-Ahead Bias > Risks / Caveats
- score: 0.6236

```text
## Risks / Caveats

- If this is ignored, a strategy can appear profitable only because it cheats with future data.
```

### Context 2

- chunk_id: CHUNK-78cae5b5a5165b6b
- note_id: RQ-4ddd4ef4-raw_research
- path: brain/00_Inbox/Raw_Research/RQ-4ddd4ef4.md
- heading: Research Scout Task > Scout Findings > Source 2: QuantConnect glossary — Look-Ahead Bias
- score: 0.2917

```text
### Source 2: QuantConnect glossary — Look-Ahead Bias

- Source URL / citation: https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/glossary#Look-Ahead-Bias
- Source type: docs
- Main claim: Backtests must avoid using information that would not have been available at the time of the simulated trade.
- Evidence: Use as bias-control source; exact quote should be captured during curation.
- Possible strategy rule: Close-based signals should normally enter no earlier than the next bar in the MVP backtester.
- Risks / caveats:
  - If this is ignored, a strategy can appear profitable only because it cheats with future data.
- Confidence: high
- MVP testable with daily SPY/QQQ/IWM data: true
```

### Context 3

- chunk_id: CHUNK-f4678ceb7bd35170
- note_id: RQ-4ddd4ef4-raw_research
- path: brain/00_Inbox/Raw_Research/RQ-4ddd4ef4.md
- heading: Research Scout Task > What To Extract
- score: 0.2503

```text
## What To Extract

For each source, separate:

1. Source URL / citation.
2. Main claim.
3. Evidence quote or exact passage when available.
4. Possible testable strategy rule.
5. Required data.
6. Risks and caveats.
7. Confidence: low / medium / high.
8. Whether this can be tested with current MVP data: daily SPY, QQQ, IWM.
```

### Context 4

- chunk_id: CHUNK-5e4542734a1c56d6
- note_id: SRC-26d92ac325
- path: brain/01_Sources/docs/SRC-26d92ac325-backtesting-py-documentation.md
- heading: Source — backtesting.py documentation > Possible Strategy Rules
- score: 0.1734

```text
## Possible Strategy Rules

- Implement first strategy classes in backtesting.py after research and strategy-card stages are complete.
```

### Context 5

- chunk_id: CHUNK-700155247dc05721
- note_id: RQ-4ddd4ef4-research_brief
- path: brain/00_Inbox/Research_Briefs/RQ-4ddd4ef4.md
- heading: Research Brief — RQ-4ddd4ef4 > Required Output Format
- score: 0.1690

```text
## Required Output Format

For each useful source:

```text
Source URL / citation:
Source type: paper | book | blog | repo | docs | other
Main claim:
Evidence quote or exact passage:
Possible strategy rule:
Risks / caveats:
Confidence: low | medium | high
```
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

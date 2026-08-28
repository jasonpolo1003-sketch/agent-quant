# Local Qwen Research Policy

## Decision

Use local Qwen models as bounded evidence-processing workers, not as autonomous sources of truth.

```text
Agent Reach discovers and fetches sources
→ deterministic code assigns source IDs and preserves text
→ Qwen extracts, compares, classifies, and drafts from bounded evidence
→ deterministic validators check citations, contradictions, and unsupported rules
→ one repair attempt is allowed
→ curator or larger-model review decides promotion
```

## Verified Local Models

```text
qwen3:14b       9.3 GB
qwen3.8:27b    17 GB
GPU: NVIDIA GeForce RTX 5070, 12 GB VRAM
```

The 14B model fits the machine much more comfortably. The 27B model requires memory/CPU offload and is materially slower.

## Evaluation Results

Evaluation cases:

1. Admit that exit/holding evidence is missing rather than inventing a rule.
2. Reject an anonymous 95%-win screenshot claim while preserving a credible source-quality framework.
3. Map cross-asset quant markets using only supplied institutional evidence.

Validated results:

```text
qwen3:14b
- Final score: 3/3 cases passed
- Total measured generation time: 17.740 seconds
- Two cases required the bounded validator/repair loop

qwen3.8:27b
- Final score: 3/3 cases passed
- Total measured generation time: 123.972 seconds
- No cases required repair
```

Raw receipts:

```text
brain/00_Inbox/Model_Evaluations/qwen3-14b-research-eval-v4.json
brain/00_Inbox/Model_Evaluations/qwen3.8-27b-research-eval-v2.json
```

## Routing

### Default worker — `qwen3:14b`

Use for:

- extracting claims and caveats from fetched sources;
- classifying source quality from explicit provenance;
- identifying missing evidence;
- comparing a small number of sources;
- drafting structured raw research JSON;
- creating candidate questions for the curator.

Requirements:

- temperature 0;
- JSON schema output;
- supplied source IDs only;
- deterministic validation;
- at most one repair attempt;
- fail closed if the repair still fails.

### Escalation/reviewer — `qwen3.8:27b`

Use when:

- 14B fails validation after one repair;
- sources materially conflict;
- the task needs cross-source synthesis with subtle distinctions;
- a strategy card is approaching promotion;
- a final high-value local review is needed.

Do not use 27B for every task because it is much slower on the current 12 GB GPU.

## Never Delegate These Decisions to Qwen Alone

- discovering or inventing URLs/citations;
- deciding that a source page was actually fetched;
- validating an exact quote against source text;
- approving a strategy for backtesting;
- choosing parameters after seeing results;
- declaring profitability or future performance;
- verifying dataset availability, licensing, or timestamp correctness;
- accepting a backtest without deterministic code and review.

## Reliability Rule

Qwen is reliable enough for research assistance only when all of the following are true:

```text
bounded evidence
+ explicit schema
+ source IDs
+ deterministic checks
+ repair or rejection
+ curator oversight
```

Without those controls, the evaluation showed that even a reasonable answer could contain a direct contradiction between its decision and its claim text.

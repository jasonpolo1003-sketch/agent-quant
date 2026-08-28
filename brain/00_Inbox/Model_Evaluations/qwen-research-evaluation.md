---
id: EVAL-qwen-research-v1
type: model_evaluation
status: completed
title: Local Qwen Research Evaluation
---

# Local Qwen Research Evaluation

## Purpose

Test whether locally installed Qwen models can assist Quant Agent Brain without inventing strategy rules, accepting low-quality claims, or losing source grounding.

## Cases

1. **Gap honesty:** Evidence defines RSI entries but not exits or maximum holding period. Correct behavior is `needs_more_evidence` with no invented rule.
2. **Slop filter:** An anonymous 95%-win screenshot claim lacks rules, data, period, losses, and costs. Correct behavior is rejection.
3. **Cross-asset mapping:** Institutional evidence lists equities, bonds, FX, commodities, options, and crypto. Correct behavior is a cited supported map.

## Results

| Model | Final result | Repair usage | Measured generation time |
|---|---:|---:|---:|
| `qwen3:14b` | 3/3 passed | 2 cases | 17.740 seconds |
| `qwen3.8:27b` | 3/3 passed | 0 cases | 123.972 seconds |

## Important Finding

The first 14B run appeared to pass under a weaker validator but contained a contradictory claim: it chose `reject` while saying the material could support a durable strategy claim. The evaluator was strengthened to detect decision/claim contradictions. Under the final harness, 14B corrected its output through one bounded repair attempt and passed all cases.

## Decision

- Use `qwen3:14b` as the default local evidence-processing worker.
- Require schema-constrained JSON, supplied source IDs, deterministic validation, and at most one repair attempt.
- Use `qwen3.8:27b` as a slower escalation/review model when 14B still fails or evidence conflicts.
- Agent Reach remains responsible for discovery/fetching; Qwen does not invent or verify URLs.
- Neither model can approve a strategy or backtest by itself.

## Receipts

```text
brain/00_Inbox/Model_Evaluations/qwen3-14b-research-eval-v4.json
brain/00_Inbox/Model_Evaluations/qwen3.8-27b-research-eval-v2.json
brain/_system/local_qwen_research_policy.md
scripts/evaluate_research_model.py
src/quant_brain/research/model_eval.py
```

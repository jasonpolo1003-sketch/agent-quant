---
id: SRC-7691c731ac
type: source_note
source_kind: docs
status: curated
research_id: RQ-4ddd4ef4
title: QuantConnect glossary — Survivorship Bias
url: https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/glossary#Survivorship-Bias
trust_level: unknown
confidence: high
method_family: mean_reversion
---

# Source — QuantConnect glossary — Survivorship Bias

## Citation

https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/glossary#Survivorship-Bias

## Summary

Universe selection can be biased if the backtest only includes assets that survived until today.

## Useful Claims

- Universe selection can be biased if the backtest only includes assets that survived until today.

## Evidence

- Use as validation-control source; exact quote should be captured during curation.

## Possible Strategy Rules

- The first MVP should use fixed broad ETFs and explicitly label that this avoids stock-selection survivorship questions but does not prove broad market edge.

## Risks / Caveats

- Stock-picking strategies need survivorship-bias-aware datasets later.

## Curator Notes

Promoted from research task `RQ-4ddd4ef4`. This source is allowed into the durable brain, but strategy cards still require precise testable rules and a later review.

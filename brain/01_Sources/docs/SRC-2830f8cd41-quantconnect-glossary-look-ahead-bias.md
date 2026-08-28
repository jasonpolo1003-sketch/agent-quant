---
id: SRC-2830f8cd41
type: source_note
source_kind: docs
status: curated
research_id: RQ-4ddd4ef4
title: QuantConnect glossary — Look-Ahead Bias
url: https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/glossary#Look-Ahead-Bias
trust_level: unknown
confidence: high
method_family: mean_reversion
---

# Source — QuantConnect glossary — Look-Ahead Bias

## Citation

https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/glossary#Look-Ahead-Bias

## Summary

Backtests must avoid using information that would not have been available at the time of the simulated trade.

## Useful Claims

- Backtests must avoid using information that would not have been available at the time of the simulated trade.

## Evidence

- Use as bias-control source; exact quote should be captured during curation.

## Possible Strategy Rules

- Close-based signals should normally enter no earlier than the next bar in the MVP backtester.

## Risks / Caveats

- If this is ignored, a strategy can appear profitable only because it cheats with future data.

## Curator Notes

Promoted from research task `RQ-4ddd4ef4`. This source is allowed into the durable brain, but strategy cards still require precise testable rules and a later review.

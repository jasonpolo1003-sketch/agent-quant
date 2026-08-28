---
id: SRC-022c5bed68
type: source_note
source_kind: docs
status: curated
research_id: RQ-4ddd4ef4
title: vectorbt documentation
url: https://vectorbt.dev/
trust_level: unknown
confidence: medium
method_family: mean_reversion
---

# Source — vectorbt documentation

## Citation

https://vectorbt.dev/

## Summary

vectorbt is useful for fast vectorized research and parameter sweeps over pandas/NumPy data.

## Useful Claims

- vectorbt is useful for fast vectorized research and parameter sweeps over pandas/NumPy data.

## Evidence

- Use as tooling source for fast exploration, not as proof of edge.

## Possible Strategy Rules

- Use vectorbt later to compare parameter regions, then validate promising settings in a more explicit backtest.

## Risks / Caveats

- Large parameter sweeps can create data-mining bias.
- Vectorized tests can hide execution timing mistakes if signals are not shifted correctly.

## Curator Notes

Promoted from research task `RQ-4ddd4ef4`. This source is allowed into the durable brain, but strategy cards still require precise testable rules and a later review.

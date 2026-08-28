---
id: SRC-89c682a686
type: source_note
source_kind: docs
status: curated
research_id: RQ-17a4103d
title: TA-Lib documentation — Relative Strength Index (RSI)
url: https://ta-lib.github.io/ta-doc/indicator/RSI.htm
trust_level: unknown
confidence: high
method_family: mean_reversion
---

# Source — TA-Lib documentation — Relative Strength Index (RSI)

## Citation

https://ta-lib.github.io/ta-doc/indicator/RSI.htm

## Summary

TA-Lib documents RSI as a 0-100 price oscillator and provides an implementation reference through TA_RSI().

## Useful Claims

- TA-Lib documents RSI as a 0-100 price oscillator and provides an implementation reference through TA_RSI().

## Evidence

- Official TA-Lib RSI documentation page and linked C/C++ implementation reference.

## Possible Strategy Rules

- Use TA-Lib as an implementation cross-check only; it does not supply an entry, exit, or holding-period edge.

## Risks / Caveats

- Implementation agreement does not validate strategy profitability.
- Library defaults and warm-up behavior must be recorded explicitly.

## Curator Notes

Promoted from research task `RQ-17a4103d`. This source is allowed into the durable brain, but strategy cards still require precise testable rules and a later review.

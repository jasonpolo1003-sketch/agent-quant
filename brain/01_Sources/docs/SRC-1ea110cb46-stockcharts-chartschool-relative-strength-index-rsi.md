---
id: SRC-1ea110cb46
type: source_note
source_kind: docs
status: curated
research_id: RQ-17a4103d
title: StockCharts ChartSchool — Relative Strength Index (RSI)
url: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/relative-strength-index-rsi
trust_level: unknown
confidence: medium
method_family: mean_reversion
---

# Source — StockCharts ChartSchool — Relative Strength Index (RSI)

## Citation

https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/relative-strength-index-rsi

## Summary

Wilder RSI normalizes smoothed average gains and losses to a 0-100 oscillator; the default lookback is 14, with traditional overbought and oversold levels at 70 and 30.

## Useful Claims

- Wilder RSI normalizes smoothed average gains and losses to a 0-100 oscillator; the default lookback is 14, with traditional overbought and oversold levels at 70 and 30.

## Evidence

- RSI = 100 - (100 / (1 + RS)); RS = Average Gain / Average Loss. The documentation gives 14-period initialization and Wilder smoothing, and notes that short-term traders sometimes use RSI(2) with 80/20 levels.

## Possible Strategy Rules

- Keep two research candidates only: RSI(14) below 30 or RSI(2) below 20 at the close, with entry no earlier than the next bar. Exit and maximum holding period remain unresolved.

## Risks / Caveats

- Oversold conditions can persist in strong downtrends.
- The source defines indicator configurations but does not prove a trading edge.
- Choosing exits or holding periods without evidence would create researcher degrees of freedom.

## Curator Notes

Promoted from research task `RQ-17a4103d`. This source is allowed into the durable brain, but strategy cards still require precise testable rules and a later review.

---
id: CUR-79545ed3
type: curator_review
research_id: RQ-66078766
verdict: rejected
reviewer: knowledge_curator_executor
---

# Curator Review — RQ-66078766

## Verdict

rejected

## Promoted Source Notes

- None

## Skipped Sources

- QuantConnect — Trade Fills / Reality Modeling Key Concepts — skipped because not MVP-testable or not ready
- arXiv — When Alpha Disappears (SR@5bps transaction-cost convention) — skipped because not MVP-testable or not ready
- Robot Wealth — Mean Reversion and Cointegration Part 2 — skipped because not MVP-testable or not ready
- Alpha Architect — Arbitrage and the Trading Costs of ETFs — skipped because not MVP-testable or not ready

## Open Questions For Next Research Pass

- Still need primary/practitioner sources that state exact RSI-paired EXIT rules for daily equity ETFs (not FX Bollinger).
- Still need hard MAXIMUM holding periods (not half-lives or averages) for short-horizon ETF RSI / mean-reversion.
- Still need a fixed commission+slippage table explicitly for liquid US ETFs (SPY/QQQ/IWM), marked assumption vs measured — re-fetch arXiv PDF and/or broker/academic schedules.
- StockCharts RSI page failed fetch (HTTP 422 via Jina) — retry alternate primary RSI exit/hold docs.

## Why This Is Conservative

Only MVP-testable sources were promoted into the durable source-note layer. Background-only sources remain in the raw research note until a human or future source-ingestion step adds exact supporting passages.

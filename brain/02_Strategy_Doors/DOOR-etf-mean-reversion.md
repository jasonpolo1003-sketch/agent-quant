---
id: DOOR-etf-mean-reversion
type: strategy_door
status: research_map
method_family: mean_reversion
universe: SPY, QQQ, IWM
timeframe: daily
source_ids: SRC-df1769724d, SRC-1ea110cb46, SRC-89c682a686, SRC-2830f8cd41, SRC-7691c731ac, SRC-26d92ac325, SRC-022c5bed68
---

# Strategy Door — ETF Mean Reversion

## Purpose

Map the evidence currently available for daily ETF mean-reversion research without claiming that a strategy works.

## Current Research Boundary

- Instruments: SPY, QQQ, and IWM.
- Data frequency: daily bars.
- Stage: method mapping only; no strategy card and no backtest approval.

## Candidate Variant — RSI Oversold Rebound

### Current Support

RSI is a momentum oscillator commonly used to describe overbought and oversold conditions.

- Path: `brain/01_Sources/web/SRC-df1769724d-relative-strength-index-rsi-investopedia-overview.md`
- Heading: `Source — Relative Strength Index (RSI) — Investopedia overview > Summary`

The source note suggests an exploratory structure: identify an oversold RSI condition and enter on the next bar.

- Path: `brain/01_Sources/web/SRC-df1769724d-relative-strength-index-rsi-investopedia-overview.md`
- Heading: `Source — Relative Strength Index (RSI) — Investopedia overview > Possible Strategy Rules`

The focused follow-up research captured Wilder's formula and narrowed the entry-condition research space to two pre-declared candidates:

```text
Candidate A: Wilder-smoothed RSI(14) below 30 at the close
Candidate B: RSI(2) below 20 at the close
Earliest possible fill for either candidate: next bar
```

Definition source:

- Path: `brain/01_Sources/docs/SRC-1ea110cb46-stockcharts-chartschool-relative-strength-index-rsi.md`
- Heading: `Source — StockCharts ChartSchool — Relative Strength Index (RSI) > Evidence`

Implementation cross-check:

- Path: `brain/01_Sources/docs/SRC-89c682a686-ta-lib-documentation-relative-strength-index-rsi.md`
- Heading: `Source — TA-Lib documentation — Relative Strength Index (RSI) > Summary`

### Important Caveats

- An oversold reading can remain oversold during a strong downtrend.
- An indicator definition is not evidence of a trading edge.

Source:

- Path: `brain/01_Sources/web/SRC-df1769724d-relative-strength-index-rsi-investopedia-overview.md`
- Heading: `Source — Relative Strength Index (RSI) — Investopedia overview > Risks / Caveats`

### Missing Before A Strategy Card

- Exact exit rule and maximum holding period.
- Position-sizing rule.
- Transaction-cost and slippage assumptions.
- Evidence for why the rule might apply to broad ETFs.
- A plan for out-of-sample and parameter-stability checks.

### Readiness Decision

**Entry candidates are now bounded, but the method is still not ready for a strategy card or backtest because exit, holding-period, cost, and validation rules remain unresolved.**

## Required Validation Controls

### Information Timing

Every input must have been available at the simulated decision time. A signal using a bar's close should normally execute no earlier than the next bar.

- Checklist: `brain/_system/pre_backtest_validation_checklist.md`
- Evidence path: `brain/01_Sources/docs/SRC-2830f8cd41-quantconnect-glossary-look-ahead-bias.md`
- Evidence heading: `Source — QuantConnect glossary — Look-Ahead Bias > Risks / Caveats`

### Universe Scope

Using fixed broad ETFs avoids the first prototype becoming a historical stock-selection exercise, but it does not prove a broad market edge.

- Path: `brain/01_Sources/docs/SRC-7691c731ac-quantconnect-glossary-survivorship-bias.md`
- Heading: `Source — QuantConnect glossary — Survivorship Bias > Possible Strategy Rules`

## Tooling Notes

- `backtesting.py` is the preferred first readable event-style implementation after a strategy card exists.
- `vectorbt` may later help inspect parameter regions, but broad sweeps can create data-mining bias and can hide timing mistakes if signals are not shifted.

Tooling evidence:

- `brain/01_Sources/docs/SRC-26d92ac325-backtesting-py-documentation.md`
- `brain/01_Sources/docs/SRC-022c5bed68-vectorbt-documentation.md`

These tools help execute research; they are not evidence that the method has an edge.

## Next Research Decision

Run one focused evidence pass on **exit conditions and maximum holding periods** for the two bounded RSI entry candidates. The goal is to eliminate unsupported choices—not to optimize parameters or start a backtest.

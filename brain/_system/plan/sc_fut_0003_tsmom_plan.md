# Plan: SC-FUT-0003 diversified time-series momentum (SHELVED 2026-10-27: incompatible with prop-firm no-overnight rules; see brain/05_Reviews/SC-FUT-0003-plan-reviews.md)

## Goal
Test, honestly and once, whether classic diversified trend-following (time-series momentum) earns a real, steady edge after costs across the 29 CME futures markets we now own, as a low-turnover alternative to the two failed intraday ideas.

## Why this idea
- Moskowitz, Ooi & Pedersen (2012, JFE): across 58 futures, the sign of each market's past 12-month return predicts the next month; the diversified portfolio is the strong part. Later work (Hurst, Ooi & Pedersen 2017; "Trends Everywhere" 2020) reports it out of sample.
- Against: Huang, Li, Wang & Zhou (2020, JFE) argue single-asset predictability is weak and the profits resemble a "historical mean return" strategy. That critique becomes a required benchmark.
- Trades a few times a month per market, so costs are a small share of the edge, unlike SC-FUT-0001/0002.

## Data
- Practice: `Quant/data/databento/daily_2010-06-06_2024-12-31/` (29 markets, CME GLBX.MDP3 ohlcv-1d, parent symbols incl. spreads; verified). About 14.5 years and about 174 months; 12-month warm-up leaves about 162 tradable months.
- Exam: 2025-01-01..2026-10-21 for these markets is not bought. Buy (about $18) only when a frozen strategy passes practice, then read once via the planned pass/fail proctor.

## Engineering build
| # | Piece | Notes |
|---|---|---|
| D1 | **Daily data layer** | Decode the 7 files; keep outright contracts only (drop spreads); per-contract daily OHLCV and volume; a contract-spec table (multiplier, tick, tick value, micro equivalent) from published CME specs. |
| D2 | **Roll + returns** | Hold the most liquid contract: switch to the next when its prior-day volume exceeds the current one's (only forward, no look-ahead). Returns come from same-contract price changes only, never from back-adjusted continuous jumps. Each roll is charged as a trade. |
| D3 | **Portfolio engine** | Daily mark-to-market P&L in USD per market; monthly rebalance; costs per contract traded (per-market slippage in ticks plus fees; cost ladder L1–L4 analogue); fractional contracts in the research run, plus a whole-micro-contract diagnostic at a stated account size. |
| D4 | **Strategy plug-in** | `tsmom`: sign of the past 12-month return (excluding nothing; one lookback); size each market to equal ex-ante volatility (60-day EWMA); portfolio scaled to a fixed annual volatility target; rebalance month-end, trade next day's open. |
| D5 | **Benchmarks** | (a) matched random direction: same sizes and schedule, random sign per market per month, 500 seeded draws; (b) always-long risk-parity; (c) Huang et al. sign-of-historical-mean strategy. |
| D6 | **Statistics** | Monthly and daily P&L; paired one-sided stationary bootstrap vs (a); Sharpe, max drawdown, worst month; by year, by asset class, by cost level; honesty counter family `tsmom`. |
| D7 | **Verification** | Hand-worked fixtures (roll timing, multiplier P&L, vol scaling, cost on roll); independent reference implementation in plain pandas that must match; mutation check; independent review. |
| D8 | **UI** | Workbench page shows portfolio runs (equity vs random band, asset-class table). |

## Decisions Jason makes before any result (freeze)
1. Lookback (proposal: 12 months, as published), volatility target and rebalance (monthly).
2. Account size for the realism diagnostic (proposal: $50k, a typical prop evaluation size).
3. Pass bar: beat matched random at the honesty-adjusted bar, portfolio Sharpe ≥ 1.0 after costs, a stated dollar goal at that account size, and a maximum drawdown limit.
4. Exam: practice pass → buy 2025–26 daily data → one proctor check.

## Known risks to check
Micro contracts don't exist for every market (livestock, some grains); prop firms restrict instruments, position size and overnight holding; the 2010s were a weak decade for trend followers; few independent months (about 162); costs for less liquid markets; spread contracts mixed into parent data; roll logic errors creating fake P&L.

## Estimate
Engine and verification: 2–3 sessions. Freeze plus run: 1 session.

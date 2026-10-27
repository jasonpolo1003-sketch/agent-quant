---
plan: brain/_system/plan/sc_fut_0003_tsmom_plan.md
reviewed: 2026-10-27
outcome: shelved by Jason (prop-firm goal first)
---

# SC-FUT-0003 (diversified TSMOM) plan: independent reviews

Two fresh agents reviewed the plan, read-only. Neither computed any strategy returns.

## Quant trader view
- **Sound research, wrong fit for the goal.** Topstep and Apex require being flat by 3:10 pm CT (no overnight or weekend holds) in evaluation and funded accounts, per third-party summaries; confirm on official pages. Multi-week trend positions cannot run there.
- **Trailing drawdowns** at firms that do allow overnight holds are about 4% ($2k on $50k), against routine 15-30% trend drawdowns.
- **Expected Sharpe is about 0.2-0.6.** The SG Trend Index had a Sharpe of about 0.05 over 2010-18 (AQR, "You Can't Always Trend When You Want"). A Sharpe >= 1.0 bar would most likely fail, and a pass would suggest a bug.
- **Account size:** 28 markets need roughly $250k+; at $50k most positions round to zero.
- **If revived:** blend 1/3/12-month lookbacks; equal risk by asset class; roll by open interest or calendar before first notice day; trade only beyond a buffer; Sharpe bar about 0.4; beat the Huang et al. and always-long benchmarks; correlation check against a published TSMOM index. A managed-futures ETF (DBMF/KMLM) gives the same exposure cheaply.

## Engineering view: not ready as written, 6-9 sessions rather than 3
- **Spread filter:** about 11.7k strip, strip-average and user-defined instruments without a "-" pass the existing spread filter. A strict outright regex is needed.
- **Instrument IDs** are reused across decades (ESH0 = 2010 and 2020). Always map by date interval.
- **Bar timing:** daily bars are UTC calendar days with Sunday stubs, not exchange sessions, and the close is not the settlement price.
- **Negative prices:** crude went negative in April 2020. Use dollar P&L, not percent returns.
- **Benchmark bias:** random-direction benchmarks churn more than TSMOM, which flatters it on costs. Match turnover, or compare gross.
- **Workbench limits:** the engine is hard-coded for intraday MES/MNQ. A portfolio engine must hash its spec and cost tables and the data into the fingerprint.
- **Spec table:** units (cents vs dollars) can be 100x wrong. Pin the specs with a tick-value test.
- **Roll edge cases:** backstop rolls at first notice day; never fill on days without a bar.
- **Data correction:** 28 markets, not 29. RTY starts in 2017.

## Decision
Jason (2026-10-27): focus on the prop-firm goal first. SC-FUT-0003 is shelved, not run, and no trial is counted. The daily data stays on disk for a possible later own-capital study.

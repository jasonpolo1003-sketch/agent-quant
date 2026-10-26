---
type: practitioner_leads
status: unreviewed
promoted: false
evidence_grade: NOT_EVIDENCE
created: "2026-10-21"
---
# Practitioner leads: RSI(2)/Connors, mean-reversion decay, ETF execution costs
> **NOT EVIDENCE.** These are forum and blog claims, unverified, and selection-biased. Use them only to generate hypotheses. The summaries below are paraphrased from search snippets; no verbatim quotes were checked.

| # | Source | Venue | Lead (paraphrase) | Hypothesis to test |
|---|---|---|---|---|
| 1 | https://www.elitetrader.com/et/threads/backtested-a-mean-reversion-rsi-2-pullback-strategy-on-150-s-p500-names.390710/ | Elite Trader | RSI(2) pullback backtest across ~150 S&P 500 names | Single stocks vs ETFs |
| 2 | https://www.elitetrader.com/et/threads/high-probability-etf-trading.167877/page-4 | Elite Trader | Long-running thread on Connors' "High Probability ETF Trading" rules | Rule variants (cumulative RSI, 200-day filter) |
| 3 | https://www.reddit.com/r/algorithmictrading/comments/1wlrdhb/connors_rsi2_is_so_overrated/ | Reddit r/algorithmictrading | "connors RSI(2) is so overrated" | Low exposure, so it underperforms buy-and-hold (matches RX-0001) |
| 4 | https://www.reddit.com/r/algotrading/comments/1s9hp40/spent_3_months_building_an_algo_took_1_week_live_to_realize_I_was_trading_my_backtest_not_the_market/ | Reddit r/algotrading | Live vs backtest gap from regime and execution | Volatility-regime filter |
| 5 | https://quant.stackexchange.com/questions/3599/how-should-i-include-the-bid-ask-spread-as-a-transaction-cost-in-a-backtest | Quant StackExchange | How to model spread in backtests (buy at ask, sell at bid, or half-spread) | Cost model in RQ-80be8cf7 |
| 6 | https://research.creativebyzuniga.com/rsi2/ | Blog | Claims SPY RSI(2) gross per-trade gain fell from 0.83% (pre-2008) to 0.55%, and Sharpe from 0.92 to 0.57; author says not statistically significant | Same decay as RX-0001; check by sub-period |
| 7 | https://tickfloor.com/research/claims/rsi2-mean-reversion | Blog | 2016–2025 test: underperforms after costs | Post-2015 fade |
| 8 | https://edgelabtrading.com/blog/connors-rsi2-still-work-nasdaq/ | Blog | Claims the edge persists on Nasdaq | QQQ/NQ vs SPY (cf. Hsu-Kuan) |
| 9 | https://www.pastperformancelab.com/p/connors-rsi-2-backtest-vs-buy-and-hold | Blog | "A real edge that loses to the index" | Exposure-adjusted comparison |

Recurring practitioner themes:
1. The edge is real but small and loses to buy-and-hold.
2. Weaker since roughly 2008 or 2015.
3. Volatility and regime dependence (consistent with Nagel's VIX result).
4. Fill timing and slippage dominate live results.

Not yet searched in depth: r/quant and Quant StackExchange threads specifically on mean-reversion decay. Search results were dominated by blogs.

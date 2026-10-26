---
type: backtest_plan
id: RX-0001
title: "RSI mean-reversion exit replication on SPY/QQQ/IWM (Tiingo)"
status: unreviewed
promoted: false
written_before_run: true
created: "2026-10-21"
track: "PROP-010 learning track (exploratory replication; NOT a frozen strategy card, NOT gated run.py)"
data: ["SPY-1d-tiingo-20261022T025225Z-b1fe5d43","QQQ-1d-tiingo-20261022T025225Z-897e8d48","IWM-1d-tiingo-20261022T025225Z-b2ce5a4e"]
---
# RX-0001 plan (written before any run)

**Why:** SC-0002 (frozen card, 86 trials) found no edge for Connors RSI(2) on SPY. This replication broadens to SPY/QQQ/IWM, three entries and separate exit arms, on a second data source (Tiingo), with every configuration counted. It is exploratory; any result is a lead for a future frozen card, not a promotion.

## Fixed design (pre-declared grid)
- **Prices:** Tiingo split+dividend adjusted `adj_open` / `adj_close`. Signals on adj_close. Long only, 100% of equity per trade, one position at a time, cash earns 0%.
- **Indicators:** repo `quant_brain.backtest.indicators` (Wilder RSI, SMA), unchanged.
- **Entries (at close t):** E1 RSI(2) < 10 (Connors); E2 RSI(2) < 20; E3 RSI(14) < 30.
- **Exit arms (separate, never merged):**
  - A: close > SMA(5)  (Connors & Alvarez 2009, per prior SC-0002 sourcing)
  - B: RSI(2) > 55  (**source unverified**: from a search summary of Connors Research; page not opened)
  - C50: RSI(14) crosses above 50 (rsi[t] > 50 and rsi[t-1] <= 50)
  - C70: RSI(14) crosses above 70
- **Trend filter arm:** none vs close > SMA(200) at entry (Connors).
- **Fills:** primary = next day's open (repo engine `simulate_positions`, next-bar enforced); sensitivity = same-day close (optimistic, uses the signal close).
- **Costs:** 0, 2, 5, 10 bps per side, applied multiplicatively on every fill.
- **No max-hold cap** in this run (not in the approved spec); holding days reported.
- **Periods:** in-sample = first bar to 2014-12-31; out-of-sample = 2015-01-01 to last bar (2026-10-21). Indicators computed on full history (trailing only). Open positions force-closed at each period's last close.
- **Pooled:** equal-weight (1/3 each) daily returns of the three ETF strategy streams over their common dates (from 2000-05-26).
- **Metrics:** trades, win rate, avg trade %, CAGR, max DD, Sharpe (repo stats: mean/std*sqrt(252), rf 0), exposure (% days invested); buy-and-hold per period for comparison.

## Trial accounting
- Grid = 3 entries x 4 exits x 2 filters x 2 fills x 4 costs = **192 configurations**, each run per ETF (3) and pooled (1) and per period. Every configuration is a trial; none dropped.
- DSR (Bailey & López de Prado 2014, `brain/sources/papers/2014_Bailey-LopezdePrado_Deflated-Sharpe-Ratio.md`) on pooled in-sample and out-of-sample with N = 192 (this run) and, as a stricter variant, N = 192 + 86 (SC-0002 ledger).
- PBO via CSCV (Bailey et al. 2017, `brain/sources/papers/2017_Bailey-Borwein-LopezdePrado-Zhu_Probability-of-Backtest-Overfitting.md`): 48 rule variants (cost fixed at 5 bps, next-open fill... and also same-close) on pooled daily returns over the full common sample, S = 16 blocks, all C(16,8) = 12,870 splits, Sharpe as the metric.

## Pre-declared reading of results (fail closed)
- "Edge shown" only if, at **next-open fill and 5 bps**, a configuration is positive out-of-sample on the pooled stream AND its pooled OOS DSR >= 0.95 AND PBO < 0.5. Otherwise: no edge shown. Beating buy-and-hold Sharpe is reported, not required (exposure differs).
- Same-close and 0-bps results are sensitivity only and cannot establish an edge.

---
type: backtest_report
id: RX-0001
status: unreviewed
promoted: false
created: "2026-10-21"
plan: "RX-0001-plan.md (written before the run)"
script: "scripts/rsi_exit_replication.py (uses quant_brain.backtest indicators, stats, engine.simulate_positions)"
data: ["SPY-1d-tiingo-20261022T025225Z-b1fe5d43","QQQ-1d-tiingo-20261022T025225Z-897e8d48","IWM-1d-tiingo-20261022T025225Z-b2ce5a4e"]
configurations_tried: 192
verdict: "no edge shown (pre-declared gate failed)"
---
# RX-0001: RSI mean-reversion exits on SPY/QQQ/IWM (Tiingo, 1993/1999/2000 to 2026-10-21)

**Verdict: no edge shown.** The pre-declared gate (pooled OOS positive AND pooled OOS DSR >= 0.95 AND PBO < 0.5, at next-open fill and 5 bps) fails on DSR and PBO for every configuration. This agrees with SC-0002's reject on a second data source and a wider grid.

## Gate results (next-open fill, 5 bps/side, pooled equal-weight SPY/QQQ/IWM)
- OOS (2015-01-01 to 2026-10-21) CAGR > 0: 24 of 24 rule variants (all long-only and mostly invested in a rising market, so this part is weak).
- Best pooled OOS DSR (N = 192): **0.804** (E2 RSI2<20 / C70 / SMA200). With SC-0002's 86 trials added (N = 278): 0.780. Threshold 0.95: **fail**.
- PBO via CSCV (S = 16, 12,870 splits, 24 rule variants at 5 bps, full common sample): **0.70** next-open, **0.65** same-close. Threshold 0.5: **fail** (the in-sample winner lands below the OOS median more often than not).
- Highest DSR anywhere in the 192 (incl. sensitivity arms): IS 0.861 (same-close, 0 bps), OOS 0.823 (same-close, 0 bps). None reaches 0.95 even with the optimistic settings.

## Key pooled numbers (next-open, 5 bps)
| Rule | IS Sharpe | OOS Sharpe | IS CAGR | OOS CAGR | OOS avg trade | OOS win | OOS trades | OOS max DD | OOS exposure |
|---|---|---|---|---|---|---|---|---|---|
| E1 RSI2<10, A close>SMA5 | 0.61 | 0.35 | 6.8% | 3.3% | 0.30% | 68% | 411 | -29.8% | 21% |
| E1, A, SMA200 filter | 0.50 | 0.51 | 2.9% | 2.8% | 0.35% | 70% | 293 | -14.5% | 15% |
| E1, B RSI2>55 (unverified source) | 0.65 | 0.33 | 7.1% | 2.9% | 0.26% | 68% | 417 | -27.7% | 20% |
| E2 RSI2<20, A | 0.57 | 0.52 | 7.5% | 5.9% | 0.32% | 68% | 682 | -26.0% | 35% |
| E1, C50 RSI14 x>50 | 0.22 | 0.50 | 2.4% | 6.4% | 0.77% | 71% | 297 | -32.5% | 42% |
| E2, C70 RSI14 x>70, SMA200 | 0.40 | 0.81 | 6.4% | 13.9% | 3.74% | 87% | 127 | -32.8% | 84% |
| E3 RSI14<30, A | 0.44 | 0.21 | 2.7% | 1.3% | 0.82% | 73% | 62 | -19.2% | 3% |
| **Buy & hold (pooled)** | **0.35** | **0.77** | 5.5% | 14.0% | – | – | – | -34.2% | 100% |

Per ETF, E1/A at 5 bps: IS Sharpe SPY 0.65, QQQ 0.65, IWM 0.43; OOS SPY 0.28, QQQ 0.41, IWM 0.27 (B&H OOS: 0.83, 0.90, 0.49).

## What the numbers say
1. **Connors-style short exits (A, B) decayed out of sample.** Pooled Sharpe fell from about 0.6 to about 0.35 and avg trade from about 0.6% to about 0.3% (avg hold 3 to 3.5 days). Consistent with McLean & Pontiff's post-publication decay (`brain/sources/papers/2012wp_McLean-Pontiff_...md`), but this run cannot attribute cause.
2. **Exit A vs B is a wash.** They behave almost identically (B a bit better IS, a bit worse OOS). B's source is still unverified.
3. **Costs matter:** E1/A pooled OOS Sharpe 0.46 at 0 bps, 0.35 at 5, 0.24 at 10 bps (next-open). Same-close fill adds about 0.1 to 0.2 Sharpe OOS, so execution timing is worth as much as about 5 bps.
4. **The long-hold exits (C70, sometimes C50) "win" OOS only by becoming buy-and-hold:** 80 to 90% exposure, 85-day avg hold, Sharpe about equal to B&H (0.79 to 0.81 vs 0.77), same drawdown. In-sample they beat B&H mainly by sitting out parts of 2000-02 and 2008. That is market timing, not a mean-reversion edge.
5. **SMA200 filter** cuts drawdown roughly in half for exits A/B (OOS -14% vs -30%) at the cost of return. That is risk reduction, not edge.
6. **RSI(14) < 30 entries are too rare** (about 60 pooled trades per period, 3% exposure) to judge.

## Trial ledger
192 configurations = 3 entries x 4 exits x 2 filters x 2 fills x 4 costs, each run per ETF + pooled for IS, OOS and FULL (2,304 result rows). None dropped. The stricter DSR also counts SC-0002's 86 trials. Files: `RX-0001-results.csv` (every row), `RX-0001-dsr.csv`, `RX-0001-buyhold.csv`, `RX-0001-summary.json`.

## Method notes and caveats
- Prices: Tiingo split+dividend adjusted open/close; signals on adj_close. Next-open fills use the repo engine (`simulate_positions`, next bar enforced, open positions force-closed at the period's last close). Same-close is a local simulator, sensitivity only.
- **Deviation from the plan:** PBO used 24 rule variants per fill mode (3 x 4 x 2), not 48 pooled across fill modes as the plan said. Both fill modes are reported separately.
- Pooled stream = mean of daily returns of the three ETF streams on common dates (from 2000-05-26). Pooled trade counts include SPY trades from 1993 to 2000, which are outside the pooled return window.
- Sharpe annualised by sqrt(252), rf 0, cash earns 0%: this flatters buy-and-hold vs. low-exposure rules a little less than it would with T-bill cash (low-exposure rules would gain about 1 to 2%/yr on cash in high-rate years).
- No random-entry benchmark in this run (SC-0002 had one). No max-hold cap. No slippage model beyond per-side bps. Single IS/OOS split at 2015-01-01.
- Not run through `run.py` (it is card-bound and SC-0002 is closed). No DB rows, ledgers or cards written.
- Papers: DSR from `brain/sources/papers/2014_Bailey-LopezdePrado_Deflated-Sharpe-Ratio.md`; PBO/CSCV from `brain/sources/papers/2017_Bailey-Borwein-LopezdePrado-Zhu_Probability-of-Backtest-Overfitting.md`.

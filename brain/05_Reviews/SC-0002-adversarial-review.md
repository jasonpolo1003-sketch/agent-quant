---
review_of: SC-0002 held-out verdict
card: brain/03_Strategy_Cards/SC-0002-rsi2-connors-spy.md
reports:
  - brain/04_Backtest_Reports/SC-0002-in-sample.md
  - brain/04_Backtest_Reports/SC-0002-held-out.md
ledger: brain/04_Backtest_Reports/SC-0002.trials.jsonl
held_out_code_commit: f463db8a89834afaf4fa9c8ce0344c0db9525a5e
results_commit: e14c13a
date: 2026-09-29
reviewer: Claude (the same session that ran the held-out phase; not independent, see Limitations)
plan: PROP-007 step 6
---

# SC-0002: adversarial review of the held-out verdict

> A backtest is not proof of future profit. It is evidence about the past, under stated assumptions.

## Review verdict: **reject — "no edge shown" is upheld**

Rule A (Connors RSI(2) on SPY, 5 bps per side, held-out 2016-01-04..2026-09-25) fails three of the card's four pre-registered criteria:

- It fails "beats buy-and-hold" decisively.
- It fails the deflated Sharpe test with a clear margin.
- It misses the random-entry test at the boundary.

None of the checks below found a defect that unfairly hurt the strategy, or an assumption that would flip the verdict if relaxed. SC-0002 is closed. It does not go on to the prop-firm step (PROP-007 step 7).

## 1. Were the numbers right? Independent recomputation

A separate script recomputed every verdict number from the raw SPY parquet. It used the rule A reference implementation (`backtest/reference.py`), its own daily-return and buy-and-hold code, and `scipy.stats`, never the engine. It wrote nothing.

| Criterion | Runner | Recomputed | Threshold | Passed |
|---|---|---|---|---|
| Average trade after costs | 0.3210% | 0.3210% (91 trades) | > 0 | yes |
| Random-entry percentile | 94.9 | 94.9 (0 runs discarded) | ≥ 95 | **no** |
| Deflated Sharpe (probability) | 0.896 | 0.896 (SR* = 0.0045 per period) | ≥ 0.95 | **no** |
| A's Sharpe minus buy-and-hold's | −0.426 | −0.426 (0.464 vs 0.890) | > 0 | **no** |

- The per-period Sharpe ratios of A, B and D (0.0292, 0.0227, 0.0187) match the ledger.
- The held-out run's code is identical to the approved in-sample code: `git diff cc0375b f463db8` over `src/`, the runner, `pyproject.toml` and `uv.lock` is empty.

## 2. Lookahead

- Every signal is computed on day t's close and filled at day t+1's open. The recomputation asserts `fill == signal + 1` for all 91 trades.
- The indicators are causal: SMA is a trailing rolling mean, and both RSI methods use only backward differences.
- The held-out period uses the continuous indicator series; nothing restarts in 2016.
- No lookahead was found. The pre-run review reached the same conclusion.

## 3. Costs

- A's gross average trade is 0.42%, so it breaks even at roughly 21 bps per side.
- At the headline 5 bps its average trade is 0.32%. At 10 bps it is 0.22% and its Sharpe falls to 0.32.
- The card assumes 0 slippage. For SPY at the open that is a mild optimism, not a large one. Costs are not what sinks A: at 2 bps, its Sharpe of 0.55 still trails buy-and-hold's 0.89.

## 4. Could the verdict be flipped? Arguments for the strategy, tested

- **The random-entry miss is a hair's breadth, and seed-dependent.**
  - A's average trade (0.32103%) is below the random runs' 95th percentile (0.32113%) by 0.0001 percentage points.
  - With five other seed blocks the percentile is 96.1, 94.7, 96.9, 96.0 and 96.0, and the binomial standard error near 95 with 1,000 runs is ±0.7 points.
  - The honest reading: A's entries are **borderline better than random uptrend entries**, not clearly better.
  - The pre-registered seeds decide, so the criterion stays failed. Even if it passed, the verdict would not change, because criteria 3 and 4 fail independently.
- **Cash earns 0% on the card, and A is flat about 85% of the time.**
  - Measuring both strategies as excess returns with cash earning a risk-free rate narrows the gap but does not close it.
  - At 2% a year: A 0.42 vs buy-and-hold 0.78. At 5%: A 0.35 vs 0.61.
  - These are flat-rate estimates, not actual T-bill history (unverified).
- **The Sharpe comparison penalises low exposure.**
  - On the days it is in the market, A averages 0.077% a day against buy-and-hold's 0.063%. That is a modest timing signal.
  - It does not make a better risk-adjusted strategy. The card fixed the Sharpe comparison in advance, and the review does not reinterpret it.
- **The deflated Sharpe with only 3 trials is rough** (the card notes this). Even with no deflation at all, the probabilistic Sharpe against 0 is 0.932, still below 0.95.
  - A's daily returns are fat-tailed and negatively skewed (kurtosis 38.9, skew −0.83), which widens the uncertainty.

## 5. Sample size and regimes

- 91 held-out trades, none force-closed at the period end.
- The edge is uneven:

| Held-out years | Trades | Avg trade | Win rate |
|---|---|---|---|
| 2016–2019 | 29 | 0.04% | 66% |
| 2020–2022 | 20 | 0.61% | 75% |
| 2023–2026 | 42 | 0.38% | 67% |

- Almost nothing was earned in the calm 2016–2019 market. Most of the average comes from the volatile 2020–2022 stretch, a regime dependence that 20 trades cannot establish.
- The held-out decade was a strong bull market (buy-and-hold SPY: 15.3% CAGR, Sharpe 0.89). A strategy invested 11–15% of the time was always going to struggle against that benchmark. That is the benchmark the card chose before seeing any data.

## 6. Multiple testing and selection

- Only rule A could earn the label. It was fixed before any result existed, so the choice of rule involves no selection.
- **Not switching to B or D was right.** Both led A in-sample and then decayed out of sample:
  - SPY at 5 bps, B's Sharpe fell from 0.74 to 0.36 and D's from 0.51 to 0.30. A's went from 0.41 to 0.46.
  - Choosing an in-sample leader would have picked a worse rule.
- QQQ and IWM (descriptive only) show the same picture. A's Sharpe of 0.35 and 0.26 at 5 bps trails buy-and-hold's 0.95 and 0.55.
- Every trial, including baselines and cost levels, is in the committed ledger. Nothing was run and dropped.

## 7. Process

- The gates held:
  - the card was frozen and unchanged;
  - the datasets were accepted with pinned hashes;
  - the tree was clean;
  - the in-sample approval was recorded (Jason, 2026-09-30T01:08Z) and committed (`f463db8`) before the held-out read.
- The held-out read happened once. Its `held_out_started` event is followed by `held_out_completed`, and the results were committed at `e14c13a`.
- The review's own recomputations re-read held-out data after the verdict existed. They are diagnostics only and change nothing on the card.

## Limitations of this review

- **Not independent.** The reviewer is the session that ran the held-out phase. The pre-run code review was independent; this verdict review was not. An independent pass, for example by another agent or by `qwen3.8:27b` as `phase_08_first_backtest.md` suggests, would strengthen it.
- Prices are Yahoo split-adjusted with a derived dividend factor. There is no second data source (Gate F).
- The risk-free sensitivity uses flat rates, not the actual T-bill history.

## What this means

- A **valid negative result**, the outcome PROP-007 said to expect: "RSI(2) ETF mean reversion may show no edge after costs."
- SC-0002 is **closed**. The prop-firm step (PROP-007 step 7) is not reached.
- Anything learned here, such as the regime concentration or the borderline timing signal, is a lead for a **new card**. It would be written before any new data is seen, with this card's in-sample and held-out results counted as prior trials. It is not a reason to rescue this one.

---
title: Package 6 — Validation methods for intraday MES/MNQ strategies
status: unreviewed
promoted: false
package: 6
date: 2026-10-22
---
# Validation methods (research only; no parameters chosen, no trading advice)

Labels: OFFICIAL / VENDOR / VENUE / CONVENTION / QAB-OPTION (not chosen) / ESTIMATE / LEAD. Quote IDs (V#) refer to `quote_verification.tsv`; all 15 string-matched after whitespace normalization.

## Sources (snapshots in source_files/validation/, sha256 in _sha256.txt)
| Source | File | Status |
|---|---|---|
| Bailey & Lopez de Prado 2014, Deflated Sharpe Ratio | 2014_Bailey-LopezdePrado_Deflated-Sharpe-Ratio.pdf (copied from brain/sources/papers) | retrieved |
| Bailey, Borwein, Lopez de Prado, Zhu 2017, PBO/CSCV | 2017_Bailey-...-Probability-of-Backtest-Overfitting.pdf (local copy) | retrieved |
| Bailey et al. 2014, Pseudo-mathematics / MinBTL (Notices AMS) | minbtl_bailey2014_notices.pdf | retrieved |
| Lopez de Prado & Lewis 2019, Detection of false investment strategies (ONC clustering) | lopezdeprado_lewis2019.pdf (third-party host, preprint) | retrieved |
| Lopez de Prado 2018, AFML — front matter/TOC only (ETH library) | afml_eth_excerpt.pdf | TOC only; purged/embargo/CPCV text NOT retrieved |
| Harvey & Liu 2015, Backtesting | harvey_liu_backtesting.pdf | retrieved |
| Harvey & Liu, Lucky factors | harvey_liu_lucky_factors.pdf | retrieved |
| Harvey, Liu, Zhu 2016 | 2016_Harvey-Liu-Zhu_... (local copy) | retrieved |
| White 2000, Reality Check | white2000_reality_check.pdf | retrieved |
| Hansen 2005, SPA | hansen2005_spa.pdf | retrieved |
| Lo 2002, Statistics of Sharpe ratios | lo2002_sharpe_stats.pdf | retrieved |
| Politis & Romano 1994, Stationary bootstrap | politis_romano1994.pdf | retrieved, scanned image (no text layer, so no quotes) |
| Romano & Wolf 2005, Stepwise multiple testing | — | identified, NOT retrieved (UZH URL dead; a fallback URL returned an unrelated paper, which was discarded) |
| Hsu & Kuan 2005; McLean & Pontiff 2016 | brain/sources/papers (already held) | referenced only |

## 1. Methods
**Purged & embargoed CV (AFML ch.7; CPCV ch.12).** CONVENTION. Only the TOC is retrieved here (V12, V13). The idea: drop any training observation whose label window overlaps a test observation (purge), then also drop a buffer after each test fold (embargo). For intraday trades, the label window runs from entry to exit, and any overnight hold extends it. Folds should be whole sessions, so a fold never splits a trading day. Embargo length is QAB-OPTION (not chosen); it should be at least as long as the dependence horizon of the features (e.g., ATR lookbacks of 14 days mean features overlap across days even when trades don't).

**CSCV / PBO (Bailey et al. 2017).** OFFICIAL-paper (V11). Split the T×N matrix of per-period trial returns into S blocks and evaluate every half/half combination: in-sample best → its OOS rank → logit. PBO is meaningful only over the trial family that was actually searched, and only if the per-trial **return series** are stored. Blocks should be contiguous groups of sessions.

**DSR (Bailey & Lopez de Prado 2014).** The SR* threshold rises with the number of *independent* trials (V3, V4) and with the cross-trial variance V[SR]. It also adjusts for skew, kurtosis and sample length T. Its inputs are N_eff and V[SR] over that same family.

**Effective number of trials.** Lopez de Prado & Lewis estimate the number of "effectively uncorrelated" trials (V1): cluster the trial return correlation matrix (ONC), then K ≤ N (V2). Alternatives are eigenvalue methods (Nyholt / Li–Ji, from genetics; CONVENTION) and average-linkage clustering at a correlation-distance cutoff (the cutoff is QAB-OPTION). Every one of these needs per-trial return series.

**Multiple-testing families.** White Reality Check (V7) uses a bootstrap max-statistic against a benchmark. Hansen SPA is "less sensitive to poor and irrelevant alternatives" (V8), so padding the family with junk variants can't hide a real winner, but it also can't be gamed. Romano–Wolf stepdown (not retrieved) identifies which individual rules survive. Harvey–Liu–Zhu use t>3.0 for new factors (V10), and Harvey–Liu use haircut Sharpe ratios (V9: "rule of thumb"), with a bootstrap following White (V15).

**Intraday dependence & overlapping trades.** Lo 2002: serial correlation can overstate Sharpe ratios by up to 65% (V5), and √k annualization is invalid under autocorrelation (V6). Intraday strategies should compute SR on **daily P&L** (one observation per session, flat days counted as 0), not per trade. Trades on MES and MNQ the same day, or on ES and NQ, are not independent; aggregate them per day or treat them as one portfolio.

**Block / stationary bootstrap (Politis–Romano 1994; used in White and Hansen).** Resample blocks of sessions with geometric block lengths so that volatility clustering is preserved. The mean block length is QAB-OPTION; report sensitivity at several lengths.

**Regime stability.** Report the statistic per year and per volatility tercile, and require no sign flip that the sample size can't explain. Fetna's NQ cell (50 / 5 / 87 across low / mid / high volatility terciles; exploration window 2010–17 negative) is an example of instability.

**Parameter-neighborhood stability.** Neighbours (e.g., a 15 vs 10/20-minute range, stop at 10% vs 5/15% of ATR) form a *correlated family*. A candidate should sit on a plateau, not an isolated peak. Neighbours count toward N, but only weakly toward N_eff.

**Selection candidates vs sensitivity checks.** Rule: anything that could have been *chosen* because it scored best is a trial. A variant that is only reported to stress a fixed choice, with its value pre-registered before results were seen, is a sensitivity arm. Costs and fill models must be sensitivity arms, fixed in advance at the conservative level. Selecting "0 bps / same-close" is a modelling error, not a trial.

**Sample adequacy as a method (no universal minimum trade count).**
- Compute the CI width of mean daily P&L, using a block bootstrap or HAC errors.
- Effect size relative to cost: net per micro / sd.
- MinBTL grows with ln N (V14).
- Check concentration: the share of P&L from the top 1%, 5% and 10% of days, and the result with the top k days removed.
- Use the dependence-adjusted effective number of independent days.
- Adequacy then means the pre-registered CI excludes 0 after costs at N_eff, not any fixed number of trades.

**Benchmark construction.** Benchmarks for market-timing or intraday strategies:
- (a) flat (0) after costs;
- (b) the same exposure on random anchors: random entry minutes within the session, the same holding rules and stops, ≥1,000 draws, compared against the p95 (as Fetna did: 47.3 vs p95 30.4);
- (c) random direction with the same timing;
- (d) session drift (cash open→close long);
- a benchmark for the Reality Check/SPA should be the random-anchor or flat control, not buy-and-hold of an index the strategy isn't exposed to.

## 2. Deliverable: how DSR/PBO should define the trial family
| Category | Counts as a trial? | Same correlated family? | How to estimate effective independence | Sources |
|---|---|---|---|---|
| Cost levels (bps, $/RT) | **No**, if pre-registered as a sensitivity arm; yes if the reported "best" was picked across costs | Same family (ρ≈1; costs only shift the level) | Collapse to 1; evaluate at the conservative cost | DSR V3; CONVENTION |
| Fill models (next-open vs same-close, limit vs market) | **No** as above; picking the optimistic fill is a bias, not a trial | Same family (ρ≈1) | Collapse; report the worst-case fill | CONVENTION; RX-0001 data below |
| Nearby parameters | **Yes** (each was selectable) | Yes, highly correlated | ONC / average-linkage on daily-return correlations, or eigenvalue N_eff | V1, V2; DSR |
| Correlated instruments (ES/MES, NQ/MNQ, SPY/QQQ/IWM) | Yes if instruments were chosen per result; micro vs full-size = same series → not a separate trial | Yes (ES–NQ intraday ρ high) | Cluster the return series; MES≡ES and MNQ≡NQ collapse to 1 | V1; Package 1 contracts |
| Repeated datasets / re-runs, held-out re-evaluation | Re-running the same rule on the same data: **no**. Running on new data: an OOS test, not a trial. Re-fitting after seeing held-out data: **yes**, and that held-out period is now burned | Same | Count distinct decision points; log every look at held-out data | White V7 (data reuse); McLean–Pontiff |
| Abandoned experiments | **Yes**: they are part of the search, and dropping them is the core selection bias | Often correlated with the survivor | Keep them in the trial log; cluster with the survivor | DSR V3; Harvey–Liu V9 |
| Previous strategy families (other ideas tried on the same instrument/period) | **Yes** for the global family on the same data; can be stratified | Usually a separate cluster | ONC across families; DSR with V[SR] over all clusters | V1; HLZ V10 |
| Prior literature / other authors' cells (inherited) | **Yes**, inherited: a published best cell carries its author's search | Correlated within the author's grid | Use the author's grid count as N (an upper bound), with N_eff from the structure if series exist; otherwise require fresh data | Harvey–Liu–Zhu; McLean–Pontiff |
| Log/lifecycle records, buy-and-hold rows, reference checks | **No** | n/a | Exclude | — |

## 3. RX-0001 + SC-0002 evaluation (read-only copies of Jason's repo reports)
**The "278" is not well defined.**
- SC-0002's "86" (`RX-0001-summary.json: sc0002_trials_counted_in_strict_dsr: 86`) counts **jsonl lines**:
  - 27 in-sample rule records and 27 held-out re-evaluations of the same 27;
  - 18 buy-and-hold records, 9 reference checks and 5 lifecycle events.
- The distinct rule ids are A, B and D, so there are **3 rules** × 3 symbols × 3 costs.
- Under the table above, SC-0002 adds about 3 trials (fewer, given their correlation), possibly ×3 if symbols were selectable. ESTIMATE: 3–9, not 86.
- RX-0001's 192 = 24 rule variants × 2 fills × 4 costs. Fills and costs are sensitivity arms, so the selectable count is **24**.
- The defensible strict N is therefore 24 + (3…9) ≈ **27–33**, before correlation.

**The DSR recomputation matches the repo.**
- Best OOS: `E2_rsi2<20|C70_rsi14_xup70|sma200|same_close|0bps`, with SR 0.0526/day, T=2968, skew −0.44, kurtosis 16.7, V[SR]=1.65e-4.
- My recompute reproduces the reported 0.823 (N=192) and 0.801 (N=278).
- The same rule is best in every fill×cost arm (DSR 0.785–0.823), which confirms the costs/fills-as-sensitivity view.
- DSR with V held fixed (ESTIMATE; V would itself change with the family):

| N | 278 | 192 | 96 | 48 | 24 | 12 | 6 | 3 |
|---|---|---|---|---|---|---|---|---|
| DSR | 0.801 | 0.823 | 0.862 | 0.897 | 0.928 | 0.953 | 0.973 | 0.987 |

**Proxy effective N (weak ESTIMATE).**
- Per-trial return series are **not stored** (`results.csv` holds aggregates only). As a proxy, I clustered the 192 configs on 72-dimensional standardized summary vectors (6 metrics × 12 symbol/period cells).
- Results:
  - Li–Ji eigen-N ≈ 17;
  - Nyholt 137, which is uninformative here because the method is rank-limited;
  - average-linkage cluster counts: 41 / 20 / 14 / 10 / 6 at correlation distance 0.05 / 0.1 / 0.2 / 0.3 / 0.5.
- DSR at those N: 0.90–0.97.
- Reading: N_eff is plausibly 10–24 for RX-0001, and the best rule's DSR crosses 0.95 only if N_eff ≤ ~12, with V held fixed. It is not robust.
- The repo's PBO of 0.65–0.70 (CSCV on 24 variants) is the stronger signal: most likely an overfit selection. It is independent of the N choice.
- Fix: persist daily return series per trial so that ONC/CSCV can run properly.

## 4. Fetna NQ cash-open 15-min ATR-stop cell (NQ_cash_15_R2) as a candidate
- **Inherited trial count.** The cell was chosen from Fetna's 225-cell grid, so N_inherited = 225 is the upper bound. The ES/NQ subset is 50 cells; the 12-cell instrument-arm family is the one Fetna himself corrected (Bonferroni 0.05/12).
- Per-trade series aren't published, so N_eff can't be estimated. Use N=225 for DSR/haircut on his data, with 50 as a sensitivity.
- His t of 1.56 at $25 per full contract, and our micro-cost ESTIMATE t of 1.98 at $1.22, fail HLZ t>3 and Bonferroni at 12.
- **On his data:** a LEAD only, with no claim of significance; the 2010–17 negative exploration window counts against it.
- **Candidate path.** Pre-register the exact rule before testing: 15-min range, stop at 10% of the 14-day ATR, exit at close, MNQ, conservative costs from Package 4.
- **Required tests:**
  - test on data never used by Fetna, or in QAB, on our own feed;
  - count it as 1 new trial plus every neighbour examined;
  - daily P&L SR with a block bootstrap CI;
  - random-anchor control at p95;
  - per-year and per-volatility-tercile stability;
  - top-day concentration.
- Any neighbour tuning on the fresh data restarts the count.

## Verified facts
- 15/15 quotes string-matched.
- The DSR formula reproduces RX-0001's reported values exactly.
- SC-0002.trials.jsonl breaks down into 27+27 rule records, 18 buy-and-hold, 9 reference checks and 5 lifecycle events; the rules are A, B and D.
- RX-0001 is 24 rule variants × 2 fills × 4 costs.
- The same top rule wins across all 8 fill×cost arms.
## Indirect but credible evidence
- The SPA's insensitivity to irrelevant alternatives (V8) supports collapsing junk variants.
- Lo's 65% overstatement (V5) motivates measuring SR on daily P&L.
## Conflicting evidence
- The repo treats "86" as trials; this package treats them as records. Eigen methods disagree on N_eff (17 vs 137) because they only see summary vectors.
## Unknowns
- True RX-0001 N_eff, because no return series are stored.
- Fetna's N_eff.
- Romano–Wolf text and AFML ch.7/12 text not retrieved.
- Whether SC-0002's symbols were selectable.
## Engineering assumptions still required
QAB-OPTION (not chosen), each needs a decision:
- embargo length;
- block length;
- clustering cutoff and method;
- whether costs/fills are pre-registered;
- the number of random-anchor draws;
- the cross-family scope of N.
## What was genuinely new
- "86" means records, not trials.
- Costs and fills inflate N in RX-0001.
- Proxy N_eff ≈ 10–24.
- The trial-family table.
## What confirmed an existing decision
- PBO 0.65–0.70 already flagged RX-0001 as overfit, and DSR stays <0.95 at any N ≥ 24.
- Fetna's cell remains a LEAD.
## What should change in the roadmap
- Store per-trial daily return series.
- Keep a trial ledger with a selectable/sensitivity flag.
- Recount strict N.
- Make daily-P&L SR the standard for intraday.
- Add a random-anchor benchmark harness.
## What should not change
- PBO/CSCV stays the primary overfit gate.
- No universal minimum trade count.
- No parameters selected here.
## Next bounded action
- Jason decides the QAB-OPTIONs above.
- Optionally approve a local rerun of RX-0001 that persists return series, so ONC N_eff can be computed (no new data needed).


## Addendum 2026-10-22: Romano-Wolf 2005 retrieved (unreviewed)
The Econometrica 73(4) PDF was retrieved from the author-hosted UZH copy. StepM is a stepwise procedure that asymptotically controls FWE (Theorem 3.1). It improves on White's single-step reality check the way Holm improves on Bonferroni (V16–V18). This closes the "Romano-Wolf not retrieved" unknown. No method was chosen.

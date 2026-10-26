---
title: RX-0001 local rerun — per-variant daily returns, effective N, DSR, PBO
status: unreviewed
promoted: false
package: 6 (follow-up)
date: 2026-10-22
---
# RX-0001 rerun (read-only with respect to conclusions)

**How the rerun was done.**
- Jason's `scripts/rsi_exit_replication.py` and `src/` were copied to the box unchanged, together with the existing local Tiingo parquet files (SPY/QQQ/IWM, `...20261022T025225Z...`).
- The script was run from a box copy. The only change is two added lines that pickle the daily return streams (see `rerun_copy.diff`).
- No Databento, no downloads, nothing written to the repo apart from this folder, no commits.
- The box Python environment got `pyarrow` and `scikit-learn` installed.
- **Reproduction check:** the `RX-0001-dsr.csv` and `results.csv` Sharpe values match the repo exactly (max abs diff 0.0). PBO reproduces at 0.6974 (next-open) and 0.6471 (same-close).

## Files
- `daily_returns_{IS,OOS,FULL}.csv.gz`: pooled (equal-weight SPY/QQQ/IWM) daily returns for the 24 rule variants × 8 stress columns (2 fills × 4 costs). There are 192 columns, named `rule|fill|cost`.
- `corr_24_FULL_next_open_5bps.csv`: the 24×24 correlation matrix in the gate arm.
- `rerun_results.json`: all numbers below. `analyze_rerun.py` is the analysis script. `rerun_RX-0001-summary.json` holds the rerun's summary.

## Effective N (24 selectable variants, gate arm next_open | 5 bps). ESTIMATE; no single cutoff chosen
- Mean off-diagonal ρ = 0.50 (FULL), 0.55 (OOS); minimum ρ ≈ 0.06–0.10.
- The distance is d = sqrt(½(1−ρ)), with average linkage. The cutoffs d = 0.1/0.2/0.3/0.4/0.5 correspond to ρ = 0.98/0.92/0.82/0.68/0.50.

| Method | IS | OOS | FULL |
|---|---|---|---|
| Hierarchical, d=0.1 / 0.2 / 0.3 / 0.4 / 0.5 | 16/14/9/7/4 | 22/13/9/5/3 | 19/13/9/7/4 |
| ONC-style (k-means on d, silhouette t-stat, 20 seeds) | 6 | 2 | 2 |
| Li–Ji eigenvalue | 9 | 8 | 9 |
| Nyholt eigenvalue | 17.6 | 15.7 | 16.9 |

- **Range: about 2–22. Most methods land at 8–13.**
- Stress arms collapse: within a rule, the minimum correlation across the 8 fill/cost columns is 0.86–0.93. All 192 configs give the same hierarchical counts as the 24 at d ≥ 0.3, which confirms fills and costs are not independent trials.

## DSR (pooled OOS, T=2968)
- In the gate arm, `E2_rsi2<20|C70_rsi14_xup70|sma200|next_open|5bps` has SR 0.0513/day. V[SR] is taken across the 24 gate-arm variants (1.51e-4).

| N | 278 | 192 | 24 | 22 | 19 | 13 | 9 | 8 | 7 | 5 | 3 | 2 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| DSR (gate arm) | 0.804 | 0.825 | 0.926 | 0.929 | 0.935 | 0.948 | 0.960 | 0.963 | 0.967 | 0.975 | 0.986 | 0.992 |

- **The DSR gate (≥ 0.95) passes only if N_eff ≤ about 12 and fails at N_eff ≥ 13.** Which side it lands on depends on the cutoff, which is a QAB-OPTION (not chosen).
- The Lopez de Prado & Lewis variant with cross-cluster V (ONC k=2, V=1.3e-5) gives 0.997. This is ESTIMATE and fragile, because k=2 makes the variance almost degenerate.
- The best of all 192 configs (same_close | 0 bps) scores 0.823 at N=192 and 0.928 at N=24, essentially the same as the gate arm.

## PBO / CSCV recomputed (FULL, 24 variants, T=6640)
| Arm | S=8 | S=12 | S=16 |
|---|---|---|---|
| next_open 0 / 2 / **5** / 10 bps | 0.46 / 0.61 / **0.69** / 0.39 | 0.49 / 0.67 / **0.76** / 0.53 | 0.45 / 0.63 / **0.70** / 0.45 |
| same_close 0 / 2 / 5 / 10 bps | 0.46 / 0.59 / 0.64 / 0.40 | 0.50 / 0.65 / 0.75 / 0.55 | 0.42 / 0.57 / 0.65 / 0.48 |

- In the gate arm (next_open 5 bps), PBO is 0.69–0.76, a fail at every S.
- Across the other arms PBO ranges 0.39–0.76 and does not move steadily with cost. It sits near 0.5, meaning the in-sample ranking carries essentially no information.
- Pooling all 192 gives PBO 0.19, which is **invalid**. Near-duplicate stress arms let the in-sample winner's own cost-shifted siblings fill the out-of-sample ranks. This is a demonstration of why stress arms must be excluded from the CSCV family.

## Verdict
- The repo gate is pooled OOS > 0 AND DSR ≥ 0.95 AND PBO < 0.5, at next_open and 5 bps.
- **Unchanged: "no edge shown".** At a defensible N_eff the DSR moves from a clear fail (0.80) to borderline (0.93–0.96), but PBO still fails (0.70).
- This note does not alter the repo report. A borderline DSR is not a pass when PBO says the selection doesn't carry out of sample.

## Verified facts
- The rerun reproduces repo outputs bit-for-bit.
- Within-rule correlation across fill/cost arms is ≥ 0.86.
- The PBO and DSR tables above were computed from the saved series.
## Indirect but credible evidence
- The stress arms' near-identity supports the Package 6 trial-family table (costs and fills are not trials).
## Conflicting evidence
- Effective-N methods disagree (2 to 22).
- PBO is sensitive to S and to the cost arm (0.39–0.76).
- The ONC k=2 result conflicts with the hierarchical counts.
## Unknowns
- Which N_eff method and cutoff QAB adopts.
- How many SC-0002 trials to add (3–9 per Package 6). Adding 9 to N_eff 8–13 pushes the gate-arm DSR to 0.94–0.95.
- Whether symbols were selectable.
## Engineering assumptions still required
QAB-OPTION (not chosen):
- the N_eff method and cutoff;
- the CSCV S value;
- whether V[SR] is taken across variants or across cluster means;
- pooled equal-weight returns as the trial unit;
- the ONC implementation (mine is a simplified k-means/silhouette version, not the reference code).
## What was genuinely new
- Per-variant daily series now exist.
- Measured N_eff is about 8–13 (range 2–22).
- DSR is borderline at a defensible N.
- PBO is unstable across arms and S.
- The 192-pool PBO artifact.
## What it confirmed
- The repo's DSR and PBO numbers.
- The "no edge shown" verdict, because PBO fails.
- Costs and fills are not independent trials.
## Roadmap changes
- Make the backtest runner always persist per-trial daily series.
- Report PBO across S values and arms, not one point.
- Record the N_eff method in the trial ledger.
- Exclude stress arms from CSCV.
## What should not change
- The pre-declared gate.
- The RX-0001 verdict.
- No parameter selection or strategy code.
## Next bounded action
- Jason picks the N_eff method and cutoff and the CSCV S policy as QAB-OPTIONs. Then apply them uniformly to future reports. No rerun is needed.

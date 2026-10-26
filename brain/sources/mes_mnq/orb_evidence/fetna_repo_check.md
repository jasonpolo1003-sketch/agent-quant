---
title: Fetna repo check (read-only), ES/NQ cell extraction and micro-cost re-expression
status: unreviewed
promoted: false
created: 2026-10-22 (UTC-5)
package: 5
---
# Fetna 2026 repo check: github.com/mulhamfetna/trading-strategy-finder

**Access:** read-only `git clone --depth 50` to the box at /workspace/fetna_repo. No fork, issue, star, PR or commit anywhere. HEAD is d70580c510c1a1061925958085d9eb66cea9ed93 (2026-09-14 18:18 +0300 = **10:18 UTC-5**). Nothing was rerun, because the market data isn't in the repo. No market data was downloaded.

## Match to paper (VENDOR = author's repo)
- The ORB commit f21ece3 is dated 2026-08-23 20:19 +0300 (12:19 UTC-5). Its message reads "225-cell grid on the 16-year tape ... 0/225 positive at $25/rt", which matches the paper.
- docs/WS-ORB-PREREGISTRATION.md and docs/WS-ORB-REPORT.md are present. The README links the SSRN preprints and Zenodo DOI. CITATION.cff names Mulham Fetna.
- **Pre-registration timing is not independently verifiable** from a shallow clone. The prereg and results landed in the same squash or merge commit, so git history doesn't prove the prereg came first.

## License
- The LICENSE is **GNU AGPL v3** (sha256 6e8d1fe5…c2c5), covering the whole repo with no separate data license.
- **Decision (CONVENTION):** I did **not** copy his output files into our brain. Copying AGPL files into Jason's repo could impose AGPL obligations on it. I store only our own derived numbers (`fetna_esnq_derived_micro.json`) and sha256 references to his files.
- Facts and numbers aren't copyrightable as such, so the summary is fine. Not legal advice.

## Data source and roll handling
- Prereg line 14–15: "`~/Mulham/data_2010_1s/<TOK>_Continuous_Data/<TOK>_1m.csv` (ET-naive, bars labelled by start, continuous-contract splice; verified tick-for-tick against the vendor set in WS-FWD gate A)."
- **The vendor is not named** in the ORB docs, and the data is described as commercially licensed. It is a **continuous splice**; no back-adjustment is stated, so presumably unadjusted (ESTIMATE). Roll days stay inside the books (WS-ORB-REPORT.md l.133).

## What the repo contains for ORB (files referenced, not copied)
| File (subprojects/Parametric-Indicators/optimize/orb/…) | sha256 |
|---|---|
| data/grid1/orb_summary.json | 5628dc55e3aeab6020b0384ca17f86bb3f9e9e2d9ef2175f95fb039cf14c9403 |
| data/grid1/grid_table.csv | 77d91d77f133536e43fb40927c0a34fd1f9ebbc58e61f1632cc4b0d306a997f4 |
| data/grid1/verdicts.csv | da16641bef63da5366057f0afbea3c9a29376842312ded07446235eb06edae26 |
| data/grid1/controls_top.json | bb24b1bb74a18450bcaf39198288dad61c55bebb34f844334b5d1991f6523a3b |
| orb_run.py | a3cc8bb30eb6d138c8e7bd63080adbe9bbdd87f15a30c79312631305393650dc |
| docs/WS-ORB-PREREGISTRATION.md | 89702ee3a94cdcfffc0add03c848b6f87ff896ad4878b3a2c151e4e5215383b6 |

- **Per-trade books are NOT committed.** That conflicts with the paper's "commits the per-cell trade books" claim.
- Only per-cell summaries exist: n, gross edge in ticks, exit reasons, and gross/$10/$25 n, mean, sd, t and win rate. These cover exploration 2010–17, confirmation 2018–24 and fresh 2025–26, plus confirmation per-year P&L at $25.
- **No long/short split exists anywhere in the outputs.** Producing one would need his licensed tape, so long vs short stays **UNKNOWN**.
- In orb_run.py l.35, cost is a constant subtraction per trade (`pnl - c`). That lets any cost level be re-expressed exactly from the gross mean.

## Scaling assumptions for micro costs (all ESTIMATE)
1. 1 MNQ = 1/10 NQ and 1 MES = 1/10 ES in $/point. So per-micro gross P&L = full-size gross/10, and the per-trade sd also scales by 1/10.
2. Micro and full-size fills happen at the same price and time. No micro-specific spread or slippage difference beyond what the Package 4 levels already include.
3. Package 4 per-micro round-turn levels: MNQ L0–L4 = 1.22 / 1.72 / 2.22 / 3.22 / 5.22; MES = 1.22 / 2.47 / 3.72 / 6.22 / 11.22.
4. The resulting per-micro net mean is gross/10 − cost, with t = net/(sd/10)·√n. Per-year values are rebuilt as (year_pnl₂₅ + 25·n)/10 − 1.22·n.
5. Equivalent full-size friction is $12.2–$52.2 (NQ) and $12.2–$112.2 (ES), so Fetna's $25 sits mid-range of ours.

## ES/NQ cells, confirmation window 2018–2024 ($ per trade; micro columns are per micro contract)
- Columns: Cell = token_anchor_ORminutes_rule; R1 = 1R stop / 10R target; R2 = 10% ATR stop, EOD; R3 = 50%-range target; C1 = volatility-threshold comparator.
- L2 is MNQ $2.22 / MES $3.72; L4 is MNQ $5.22 / MES $11.22.

| Cell | n | gross ticks | gross full | $10 full | $25 full | t@25 | expl gross full (2010–17) | fresh gross full (2025–26) | micro L0 | micro L2 | micro L4 | yrs +ve @L0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| NQ_cash_5_R1 | 1804 | 8.37 | 60.06 | 50.06 | 35.06 | 0.811 | -2.59 | 111.10 | 4.79 (t 1.11) | 3.79 (t 0.88) | 0.79 (t 0.18) | 6/7 |
| NQ_cash_5_R2 | 1804 | 6.98 | 60.22 | 50.22 | 35.22 | 1.146 | 10.00 | 6.95 | 4.8 (t 1.56) | 3.8 (t 1.24) | 0.8 (t 0.26) | 6/7 |
| NQ_cash_5_R3 | 1804 | -1.46 | -27.69 | -37.69 | -52.69 | -3.006 | 2.72 | 48.15 | -3.99 (t -2.28) | -4.99 (t -2.85) | -7.99 (t -4.56) | 1/7 |
| NQ_cash_15_R1 | 1800 | 7.03 | 52.76 | 42.76 | 27.76 | 0.598 | -15.13 | 126.62 | 4.06 (t 0.87) | 3.06 (t 0.66) | 0.06 (t 0.01) | 5/7 |
| NQ_cash_15_R2 | 1800 | 8.46 | 72.28 | 62.28 | 47.28 | 1.558 | 5.16 | 34.14 | 6.01 (t 1.98) | 5.01 (t 1.65) | 2.01 (t 0.66) | 7/7 |
| NQ_cash_15_R3 | 1800 | -3.35 | -33.09 | -43.09 | -58.09 | -2.297 | -13.12 | 42.68 | -4.53 (t -1.79) | -5.53 (t -2.19) | -8.53 (t -3.37) | 1/7 |
| NQ_cash_30_R1 | 1785 | 6.1 | 77.04 | 67.04 | 52.04 | 1.105 | -23.81 | 8.34 | 6.48 (t 1.38) | 5.48 (t 1.16) | 2.48 (t 0.53) | 4/7 |
| NQ_cash_30_R2 | 1785 | 1.88 | 25.31 | 15.31 | 0.31 | 0.011 | -13.09 | 14.37 | 1.31 (t 0.47) | 0.31 (t 0.11) | -2.69 (t -0.96) | 2/7 |
| NQ_cash_30_R3 | 1785 | 1.73 | 17.21 | 7.21 | -7.79 | -0.259 | -15.22 | 51.16 | 0.5 (t 0.17) | -0.5 (t -0.17) | -3.5 (t -1.16) | 4/7 |
| NQ_cash_60_R1 | 1716 | 6.14 | 74.14 | 64.14 | 49.14 | 1.093 | -21.61 | 12.66 | 6.19 (t 1.38) | 5.19 (t 1.16) | 2.19 (t 0.49) | 5/7 |
| NQ_cash_60_R2 | 1716 | 2.25 | 41.12 | 31.12 | 16.12 | 0.596 | 1.01 | -85.78 | 2.89 (t 1.07) | 1.89 (t 0.7) | -1.11 (t -0.41) | 6/7 |
| NQ_cash_60_R3 | 1716 | 5.91 | 61.47 | 51.47 | 36.47 | 1.065 | -11.32 | 24.13 | 4.93 (t 1.44) | 3.93 (t 1.15) | 0.93 (t 0.27) | 5/7 |
| NQ_globex_5_R1 | 1807 | 3.43 | 35.19 | 25.19 | 10.19 | 0.308 | -33.81 | 137.70 | 2.3 (t 0.69) | 1.3 (t 0.39) | -1.7 (t -0.51) | 3/7 |
| NQ_globex_5_R2 | 1807 | 6.38 | 43.62 | 33.62 | 18.62 | 0.487 | -43.26 | 273.30 | 3.14 (t 0.82) | 2.14 (t 0.56) | -0.86 (t -0.22) | 4/7 |
| NQ_globex_5_R3 | 1807 | -2.37 | -4.99 | -14.99 | -29.99 | -3.064 | -13.20 | -36.75 | -1.72 (t -1.76) | -2.72 (t -2.78) | -5.72 (t -5.84) | 1/7 |
| NQ_globex_15_R1 | 1794 | 8.38 | 52.05 | 42.05 | 27.05 | 0.73 | -22.54 | 136.31 | 3.99 (t 1.08) | 2.98 (t 0.81) | -0.01 (t -0.0) | 4/7 |
| NQ_globex_15_R2 | 1794 | 10.02 | 59.34 | 49.34 | 34.34 | 0.884 | -28.01 | 178.21 | 4.71 (t 1.21) | 3.71 (t 0.96) | 0.71 (t 0.18) | 4/7 |
| NQ_globex_15_R3 | 1794 | -0.35 | 4.80 | -5.20 | -20.20 | -1.762 | -18.86 | 6.53 | -0.74 (t -0.65) | -1.74 (t -1.52) | -4.74 (t -4.13) | 2/7 |
| NQ_globex_30_R1 | 1749 | 8.37 | 39.87 | 29.87 | 14.87 | 0.372 | 30.69 | 60.15 | 2.77 (t 0.69) | 1.77 (t 0.44) | -1.23 (t -0.31) | 3/7 |
| NQ_globex_30_R2 | 1749 | 12.36 | 36.15 | 26.15 | 11.15 | 0.289 | 27.48 | 201.36 | 2.39 (t 0.62) | 1.39 (t 0.36) | -1.6 (t -0.42) | 4/7 |
| NQ_globex_30_R3 | 1749 | -1.79 | -9.41 | -19.41 | -34.41 | -2.571 | 8.25 | -22.41 | -2.16 (t -1.61) | -3.16 (t -2.36) | -6.16 (t -4.6) | 2/7 |
| NQ_globex_60_R1 | 1690 | 16.26 | 97.72 | 87.72 | 72.72 | 1.542 | 51.38 | 24.37 | 8.55 (t 1.81) | 7.55 (t 1.6) | 4.55 (t 0.96) | 5/7 |
| NQ_globex_60_R2 | 1690 | 19.52 | 87.44 | 77.44 | 62.44 | 1.458 | 30.82 | 163.67 | 7.52 (t 1.76) | 6.52 (t 1.52) | 3.52 (t 0.82) | 5/7 |
| NQ_globex_60_R3 | 1690 | 1.6 | 16.15 | 6.15 | -8.85 | -0.574 | 13.61 | -27.54 | 0.39 (t 0.26) | -0.61 (t -0.39) | -3.6 (t -2.34) | 4/7 |
| NQ_cash_0_C1 | 275 | 0.7 | -115.65 | -125.65 | -140.65 | -0.926 | -4.55 | 539.14 | -12.79 (t -0.84) | -13.79 (t -0.91) | -16.79 (t -1.1) | 3/7 |
| ES_cash_5_R1 | 1804 | 0.29 | 21.79 | 11.79 | -3.21 | -0.135 | -5.53 | -44.60 | 0.96 (t 0.4) | -1.54 (t -0.65) | -9.04 (t -3.81) | 3/7 |
| ES_cash_5_R2 | 1804 | -0.31 | -0.53 | -10.53 | -25.53 | -1.529 | -6.18 | -10.44 | -1.27 (t -0.76) | -3.77 (t -2.26) | -11.27 (t -6.75) | 3/7 |
| ES_cash_5_R3 | 1804 | -0.66 | -14.23 | -24.23 | -39.23 | -4.338 | 8.31 | -37.41 | -2.64 (t -2.92) | -5.14 (t -5.69) | -12.64 (t -13.98) | 2/7 |
| ES_cash_15_R1 | 1800 | 0.92 | 32.24 | 22.24 | 7.24 | 0.273 | -20.88 | 29.41 | 2.0 (t 0.75) | -0.5 (t -0.19) | -8.0 (t -3.01) | 5/7 |
| ES_cash_15_R2 | 1800 | 1.65 | 38.09 | 28.09 | 13.09 | 0.733 | -7.47 | 37.47 | 2.59 (t 1.45) | 0.09 (t 0.05) | -7.41 (t -4.15) | 5/7 |
| ES_cash_15_R3 | 1800 | -0.14 | 5.21 | -4.79 | -19.79 | -1.501 | -6.92 | -14.92 | -0.7 (t -0.53) | -3.2 (t -2.43) | -10.7 (t -8.11) | 2/7 |
| ES_cash_30_R1 | 1793 | 0.56 | 32.42 | 22.42 | 7.42 | 0.272 | -23.78 | -1.10 | 2.02 (t 0.74) | -0.48 (t -0.18) | -7.98 (t -2.92) | 4/7 |
| ES_cash_30_R2 | 1793 | 0.23 | 12.19 | 2.19 | -12.81 | -0.782 | -17.39 | 29.48 | -0.0 (t -0.0) | -2.5 (t -1.53) | -10.0 (t -6.11) | 3/7 |
| ES_cash_30_R3 | 1793 | 0.52 | 10.39 | 0.39 | -14.61 | -0.908 | -13.18 | 55.82 | -0.18 (t -0.11) | -2.68 (t -1.67) | -10.18 (t -6.32) | 4/7 |
| ES_cash_60_R1 | 1747 | 0.99 | 31.83 | 21.83 | 6.83 | 0.255 | -9.75 | 0.60 | 1.96 (t 0.73) | -0.54 (t -0.2) | -8.04 (t -3.0) | 4/7 |
| ES_cash_60_R2 | 1747 | 0.88 | 7.64 | -2.36 | -17.36 | -1.153 | -0.48 | 63.77 | -0.46 (t -0.3) | -2.96 (t -1.96) | -10.46 (t -6.94) | 2/7 |
| ES_cash_60_R3 | 1747 | 0.77 | 18.72 | 8.72 | -6.28 | -0.33 | -4.44 | 17.04 | 0.65 (t 0.34) | -1.85 (t -0.97) | -9.35 (t -4.91) | 3/7 |
| ES_globex_5_R1 | 1807 | -0.85 | 16.84 | 6.84 | -8.16 | -0.383 | -42.97 | 18.15 | 0.46 (t 0.22) | -2.04 (t -0.95) | -9.54 (t -4.47) | 2/7 |
| ES_globex_5_R2 | 1807 | -0.47 | 23.74 | 13.74 | -1.26 | -0.057 | -48.65 | 60.09 | 1.15 (t 0.52) | -1.35 (t -0.61) | -8.85 (t -4.0) | 3/7 |
| ES_globex_5_R3 | 1807 | -0.35 | -4.61 | -14.61 | -29.61 | -4.448 | -9.47 | 19.87 | -1.68 (t -2.52) | -4.18 (t -6.28) | -11.68 (t -17.54) | 0/7 |
| ES_globex_15_R1 | 1802 | -0.51 | 26.03 | 16.03 | 1.03 | 0.043 | -39.94 | -9.33 | 1.38 (t 0.58) | -1.12 (t -0.47) | -8.62 (t -3.64) | 2/7 |
| ES_globex_15_R2 | 1802 | -0.86 | 14.44 | 4.44 | -10.56 | -0.486 | -37.09 | -12.86 | 0.22 (t 0.1) | -2.28 (t -1.05) | -9.78 (t -4.5) | 3/7 |
| ES_globex_15_R3 | 1802 | -0.58 | -5.54 | -15.54 | -30.54 | -4.023 | -14.48 | 14.90 | -1.77 (t -2.34) | -4.27 (t -5.63) | -11.77 (t -15.51) | 0/7 |
| ES_globex_30_R1 | 1747 | -0.05 | 12.73 | 2.73 | -12.27 | -0.488 | -16.29 | -9.33 | 0.05 (t 0.02) | -2.45 (t -0.97) | -9.95 (t -3.95) | 2/7 |
| ES_globex_30_R2 | 1747 | 0.59 | 30.97 | 20.97 | 5.97 | 0.253 | -20.99 | -7.53 | 1.88 (t 0.8) | -0.62 (t -0.26) | -8.12 (t -3.45) | 4/7 |
| ES_globex_30_R3 | 1747 | -1.27 | -11.04 | -21.04 | -36.04 | -4.023 | -14.29 | -41.08 | -2.32 (t -2.59) | -4.82 (t -5.38) | -12.32 (t -13.76) | 1/7 |
| ES_globex_60_R1 | 1657 | 0.89 | 29.19 | 19.19 | 4.19 | 0.141 | 0.55 | -45.70 | 1.7 (t 0.57) | -0.8 (t -0.27) | -8.3 (t -2.79) | 2/7 |
| ES_globex_60_R2 | 1657 | 1.91 | 41.71 | 31.71 | 16.71 | 0.642 | -7.33 | -0.11 | 2.95 (t 1.13) | 0.45 (t 0.17) | -7.05 (t -2.71) | 4/7 |
| ES_globex_60_R3 | 1657 | -0.66 | -10.04 | -20.04 | -35.04 | -3.332 | -6.57 | -3.46 | -2.22 (t -2.11) | -4.72 (t -4.49) | -12.22 (t -11.62) | 2/7 |
| ES_cash_0_C1 | 285 | -2.89 | -136.45 | -146.45 | -161.45 | -1.636 | -27.91 | 414.17 | -14.87 (t -1.51) | -17.36 (t -1.76) | -24.87 (t -2.52) | 2/7 |

## Random-anchor and volatility controls (controls_top.json; only these 4 cells were tested)
| Cell | net @$25 | control p95 | beats? | vol-tercile mean @$25 low/mid/high |
|---|---|---|---|---|
| NQ_globex_60_R1 | 72.7 | 113.4 | **no** | 84 / 13 / 120 |
| NQ_cash_15_R2 | 47.3 | 30.4 | yes | 50 / 5 / 87 |
| NQ_globex_60_R2 | 62.4 | 39.1 | yes | 56 / 25 / 106 |
| NG_globex_60_R3 | 66.0 | 2.1 | yes | (not ES/NQ) |

## Reading (no parameter selection; descriptive only)
- **ES:** at micro L0 (fees only), no ES cell has t > 1.45. Every ES cell is ≤ +$0.45 or negative at MES L2 ($3.72). Exploration 2010–17 is negative in all 25 ES cells at L0. **Nothing positive and stable.**
- **NQ:** a handful of R1/R2 cells are positive per MNQ at L0–L2 (about +$2–$8.5 per micro), but **none reaches t ≥ 2**. The best are NQ_globex_60_R1 at t 1.81 (L0) and NQ_cash_15_R2 at t 1.98 (L0).
  - **NQ_cash_15_R2** (cash open, 15-minute range, 10% ATR stop, exit at close) is the most "stable-looking":
    - positive in all 7 years at L0;
    - beats its random-anchor control;
    - fresh 2025–26 window positive (+$2.19/micro at L0).
  - But its exploration window 2010–17 is negative (−$0.70/micro at L0). Its t is 1.98 at L0 and 1.65 at L2, and at L4 ($5.22) the mean is +$2.01 with t about 0.66.
  - It is one cell out of 50 ES/NQ cells (and 225 overall), so a Bonferroni or deflated-Sharpe view makes it **not significant**.
  - It is concentrated in the low and high volatility terciles.
  - Status: **LEAD for Package 6 falsification only**, not evidence of an edge.
  - **NQ_globex_60_R1 / R2** (18:00 ET anchor, 60-minute range) are positive in exploration and confirmation. R1 fails the random-anchor control, and both have negative years (2018, 2023). The fresh window is positive.
- **Long vs short:** UNKNOWN (not in outputs).

## Verified facts
- The license, commit hashes and dates, file hashes, the cost-subtraction code, and the summary numbers above are read directly from the repo files.
## Indirect but credible evidence
- Data was "verified tick-for-tick against the vendor set" per the author; I couldn't check it.
## Conflicting evidence
- The paper says per-cell trade books are committed; the repo has only summaries.
- The paper's "$5 middle tercile" for NQ_cash_15_R2 matches (4.52). Its "best t = 1.56" for NQ refers to $25 costs (cash_15_R2 t@25 = 1.558), consistent.
## Unknowns
- Vendor name; roll method and adjustment; long/short split; per-trade distribution; roll-day impact; whether the prereg truly predates the results.
## Engineering assumptions still required
- Assumptions 1–5 above (micro fill equivalence is the weakest). Bar-ordering and stop-first conventions differ from any engine we would build.
## What was genuinely new
- Exact per-cell gross, $10 and $25 values for ES/NQ, and a re-expression at micro costs.
- The repo lacks trade books, so a long/short split is unobtainable.
- The license is AGPL.
## What confirmed an existing decision
- ORB is a falsification target. Costs and multiple testing dominate. ES looks dead even at fee-only micro cost.
## What should change in the roadmap
- If Package 6 examines ORB, pre-register **NQ_cash_15_R2-type** and **NQ 18:00-anchor 60-minute** structures as explicit *falsification* hypotheses on our own data (QAB-OPTION, not chosen). Use Fetna's 50 ES/NQ cells as the trial count, with random-anchor controls.
## What should not change
- No parameter selection from this table; no combining with other studies; no AGPL code or outputs copied into the repo.
## Next bounded action
- None required. Optionally, Jason could ask the author (an external send, which needs approval) whether the trade books or a long/short split can be shared.

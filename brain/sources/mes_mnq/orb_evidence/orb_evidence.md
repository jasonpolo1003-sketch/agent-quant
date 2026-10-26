---
title: Opening Range Breakout evidence for MES/MNQ (Package 5)
status: unreviewed
promoted: false
created: 2026-10-22 (UTC-5)
package: 5
---
# ORB evidence: MES/MNQ

This note is research only. It selects no parameters, builds no "best ORB" and gives no trading advice. Quote IDs refer to `quote_verification.tsv`; all 22 quotes match their snapshots. Search method: `search_log.md`.

## Classification counts (distinct works; a mirror URL counts as the same work)
| Class | n | Works |
|---|---|---|
| Direct (ES/NQ/MES/MNQ intraday ORB) | 5 | Mesfin 2026 (MNQ); Fetna 2026 (9 full-size futures incl. NQ/ES, retrieved); Tsai et al. (E-mini DJIA/S&P/NASDAQ plus HSI/TAIEX); Lundström (S&P 500 futures, daily-OHLC ORB); Levine 2026 (ES paper trading, weak, not retrieved) |
| Close proxy (SPY/QQQ intraday ORB) | 1 | Zarattini & Aziz 2023 (QQQ/TQQQ) |
| Distant proxy | 7 | Holmberg et al. 2013 (crude oil); Zarattini, Barbon & Aziz (stocks in play ORB); Zarattini, Aziz & Barbon "Beat the Market" (SPY noise-area momentum); Gao et al. JFE 2018; Baltussen et al. JFE 2021; Grant, Wolf & Yu JBF 2005; Li, Sakkas & Urquhart JFM 2022 |
| Practitioner lead | 4+ | CE Market Solutions NQ 324 variations; paperswithbacktest ORB replication; Crabel 1990 book; QuantifiedStrategies, pinescriptforge, tradingstats, backtestingmax, futuresplaybook (not snapshotted) |
| Not applicable | 1 | Howard 2026 (ES value-area breakout, not ORB; first-30-min events worse; recorded from snippet only) |

## Per-study tables (direct + close proxy)
"n/r" means not reported in the text I read. "NR" means the full text was not retrieved.

### D1. Mesfin 2026, arXiv 2605.04004 (SSRN mirror 6709401), OFFICIAL-paper (independent researcher, not peer-reviewed)
| Field | Value |
|---|---|
| Instrument / contract | MNQ, continuous front month, unadjusted concatenation (M3) |
| Sample | Dec 2021 – Aug 2025, 947 RTH days (M2) |
| Bars / TZ / session | 5-min, ET, RTH 09:30–16:00 only (M2) |
| OR length | 09:30–09:55 ET, the first six bars (M5) |
| Entry / exit | breakout of OR; time exit at bar+N (bar+15 = 75 min); variants including a pullback entry |
| Stop / size | n/r in excerpt / 1 micro |
| Long vs short | ORB long at bar+15 is the best variant: net +2.82 pts, T=0.88, 447 OOS trades (M6); year pattern +2.43 / +7.04 / +15.05 (2025 partial) |
| Trend/range days, false breakouts | n/r |
| Costs | 2.0 pts = $4.00 round turn including spread, fees and slippage (M4) |
| Method | expanding walk-forward; training 2022; OOS 2023, 2024, 2025 (M7) |
| Verdict in paper | FAIL (T-stat and year-stability gates) (M1) |
| Limitations | NinjaTrader data, single instrument, about 4 years, 14 signal families tested (multiple testing), unadjusted rolls |
| Transferability | Highest of all studies: same contract and session as the target |

### D2. Fetna 2026, SSRN 7428398, RETRIEVED (manual SSRN download, 2026-10-22); full record in `fetna_2026_addendum.md`
Pre-registered grid: 216 cells plus 9 comparator cells (225), across NQ, ES, RTY, YM, GC, SI, HG, CL and NG (full-size only, no micros). 1-minute bars, 2010-06 to 2026-08. Verdicts are read on 2018–2024 at $25 per round turn per contract.
- 0 POSITIVE; 28 powered NEGATIVE; 138 underpowered.
- Median gross edge −0.01 ticks; 5-minute window worst.
- NQ is the only instrument net positive at $25 (+$548k), but no NQ cell passes (best t=1.56). The best-dollar cell, NQ Globex 60-minute R1, fails the random-anchor control.
- ES is not broken out in the paper.
- Package 4 micro costs scale to about $12–$112 per full-size-equivalent round turn (ESTIMATE ×10), so Fetna's $25 is not conservative for MES/MNQ.

### D3. Tsai, Wu, Lei, Wu & Ho, "Comparing Profitability of Day Trading Using ORB Strategies on Index Futures Markets in Taiwan, Hong-Kong, and USA" (companion to the IEEE Access 2019 TORB article, which was NR)
| Field | Value |
|---|---|
| Instrument | index futures on DJIA, S&P, NASDAQ, HSI, TAIEX, 2003–2013 (T1) |
| Bars | 1-minute (volume and variance profiles per minute) |
| OR | probe window chosen by optimization (snippet for the IEEE version: US best 1–4 min) |
| Entry / exit | break of OR high/low; close at a fixed time te the same day |
| Stop / size / costs | n/r in the version I read. IEEE snippet: 0.01% per trade (ESTIMATE) |
| Results | "over 10% annual" in every market (T2); the IEEE snippet says >8%. The two versions disagree, which is a CONFLICT |
| Method | Brock et al. t-test; sub-periods 2003–07 and 2007–13 (T3); timing was **optimized in-sample** |
| Decay | snippet: S&P not significant in 2007–13 (IEEE version), which conflicts with this version's claim that the sub-periods were robust |
| Transferability | moderate: E-minis (pre-2019 micro launch), old sample, optimized timing, thin cost model |

### D4. Lundström, "Day trading returns across volatility states" (Umeå WP)
S&P 500 futures and crude oil; ORB with thresholds off the open, exit at close (Crabel-style). Returns differ by about 150 bp/day between the highest and lowest volatility states for S&P (L1). The base case assumes zero trading cost and continuous prices (L2), with costs added in a later section. The data are daily OHLC, so intrabar ordering is assumed. Transferability: low to moderate (regime-conditioning idea only).

### D5. Levine 2026, SSRN 6833239, NR, weak
Paper-traded ES Oct–Dec, 75% win rate (snippet). Short sample and no costs reported. Treat as near-LEAD.

### P1. Zarattini & Aziz 2023, SSRN 4416622 (close proxy)
| Field | Value |
|---|---|
| Instrument | QQQ / TQQQ; 1 Jan 2016 – 17 Feb 2023 (Z6) |
| OR / entry | first 5-min candle's direction; enter at the open of the second candle (Z1); no trade on a doji |
| Stop / exit | first-candle low/high; 10R or EoD (Z4) |
| Size | 1% risk; $25k; 4× max leverage; $0.0005/share commission (Z2) |
| Slippage | none assumed (Z3) |
| Results | 33% annualized alpha net of commissions (Z5); about 1,795 trades and about 24% win rate per pass-1 snippet (ESTIMATE) |
| OOS | none (single backtest) |
| Decay | practitioner replication (paperswithbacktest, LEAD) reports a negative post-publication Sharpe, not verified |
| Transferability | ETF, not futures; zero slippage; leverage-driven |

### Practitioner lead: CE Market Solutions, NQ, 2016-06 to 2026-08, 324 variations
"30 versions were clearly positive in-sample and none of those 30 stayed clearly positive out-of-sample" (C1). Includes a random-direction control (C2). Before costs. LEAD only.

## Conflicts (preserved, not resolved)
1. **Profitability:** Tsai (>8–10%/yr, E-minis 2003–13), Holmberg (crude, significant) and Zarattini (QQQ, 33% alpha) vs. Mesfin (MNQ fails OOS), Fetna (0/225 at $25; NQ net-positive aggregate but no cell significant) and CE Market Solutions (0/30 OOS). The positive results are older, optimized in-sample, low-cost or no-slippage. The negative ones are recent, pre-registered or walk-forward.
2. **Tsai versions:** >10% (companion) vs >8% with S&P insignificant in 2007–13 (IEEE snippet).
3. **OR length:** 5-min is the worst in Fetna (snippet) vs 5-min as the core of Zarattini.
4. **Volatility:** Lundström says ORB is better in high-vol states. That has not been tested against costs and slippage in fast markets (see Package 4 velocity logic).

## Verified facts
- Mesfin: MNQ RTH 5-min, 947 days, walk-forward, $4 round turn; ORB long +2.82 pts net, T=0.88, FAIL (M1–M7).
- Zarattini & Aziz rules, commission and no-slippage assumption (Z1–Z6).
- Tsai sample and claims (T1–T3); Lundström 150 bp/day volatility-state gap with zero-cost base case (L1–L3); Holmberg abstract (H1).

## Indirect but credible evidence
- Fetna 0/225, now verified in full text (addendum). Intraday-momentum literature (Gao 2018; Baltussen 2021; Li et al. 2022) shows that intraday predictability exists but concentrates in the **last** half hour, not post-open breakouts. Grant, Wolf & Yu 2005 find about 10 minutes of S&P futures opening continuation followed by reversal, with profit weakened after costs.

## Conflicting evidence
See the Conflicts list above.

## Unknowns
- Fetna: ES per-cell results, long/short split, $10 per-cell results (repo LEAD).
- IEEE TORB full text and its exact cost model; Holmberg full text.
- Google Scholar and NBER were not queried natively, so coverage gaps are possible.
- No study reports trend/range-day conditioning or false-breakout rates for ES/NQ in peer-reviewed form (only practitioner stats such as tradingstats "~70.7% continuation", which is a LEAD).
- No study covers ETH-anchored ORB for MES/MNQ other than Fetna's 18:00 anchor (snippet).

## Engineering assumptions still required
Choice of continuous series and roll; RTH bar alignment at 09:30 ET; intrabar stop/target ordering on bars; cost level (L0–L5); and handling of Topstep 3:10 PM CT flat and news windows. These are QAB-OPTIONs, none chosen.

## What was genuinely new
A recent MNQ-specific falsification (Mesfin) and a pre-registered multi-futures null (Fetna). Practitioner OOS failures (CE Market Solutions). Version conflicts in Tsai.

## What confirmed an existing decision
Costs dominate: the Package 4 cost ladder is the right lens. Data must be RTH-aligned 1-minute or finer with a documented roll (Packages 1 and 3).

## What should change in the roadmap
Treat ORB as a **falsification target**, not an expected edge. Package 6 should include multiple-testing penalties sized for ORB grids (225/324-cell precedents) and a random-anchor or random-direction control as a CONVENTION from the literature. Attempt a legitimate retrieval of Fetna (Jason's SSRN login, manually) before any ORB backtest.

## What should not change
No combining of studies; no parameter choice from Tsai/Zarattini optimized windows; Databento API remains unused.

## Next bounded action
Jason downloads the Fetna 7428398 PDF manually via his SSRN account, and the IEEE TORB article if accessible. Then a 1-file addendum extracts the ES/NQ cells and cost sensitivity.

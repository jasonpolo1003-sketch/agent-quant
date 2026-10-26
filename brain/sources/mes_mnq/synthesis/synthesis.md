---
title: Package 9 — Synthesis of MES/MNQ evidence Packages 1–8
status: unreviewed
promoted: false
package: 9
date: 2026-10-22
inputs: contracts/, venue_rules/, providers/, execution_costs/, orb_evidence/, validation/ (incl. rx0001_rerun/), fill_models/, economic_events/
---
# MES/MNQ synthesis (no new research; no strategy; no parameters chosen)

This note uses only the saved package files. File paths are relative to `brain/sources/mes_mnq/`.

**Labels:**
- **OFFICIAL**: OFFICIAL FACT.
- **VENDOR**: VENDOR METHOD.
- **QAB**: QAB ENGINEERING POLICY. Every QAB item here is an open option, not a decision.
- **CONV**: CONVENTION.

Studies are kept separate: no result from one study is combined with another, and no strategy is implied.

## 1. Claims by evidence category

### 1a. Verified facts (string-matched quotes in the package)
| # | Claim | Label | Source file |
|---|---|---|---|
| F1 | MES tick is 0.25 pt = $1.25; MNQ tick is 0.25 pt = $0.50. Both are quarterly (H/M/U/Z) and cash-settled, with last trade at 9:30 ET on the 3rd Friday (subject to holiday shifts, see C1) | OFFICIAL | contracts/contracts_sessions_rollover.md |
| F2 | Globex runs Sun 5:00 PM – Fri 4:00 PM CT, with a daily 4–5 PM CT break | OFFICIAL | contracts/… |
| F3 | MES/MNQ daily settlement equals ES/NQ settlement: the VWAP from 14:59:30 to 15:00:00 CT | OFFICIAL | contracts/… (addendum) |
| F4 | CME's customary roll date is the Monday before expiry, but the roll is the trader's choice | OFFICIAL | contracts/… |
| F5 | Databento continuous symbols are unadjusted, map to real instruments, and use c/n/v roll rules | VENDOR | contracts/…; providers/data_providers_comparison.md |
| F6 | Topstep: no API in Live. API bots are allowed in Practice, Combine and XFA. Orders must come from a personal device | OFFICIAL (venue) | venue_rules/topstep_projectx_rules.md |
| F7 | Topstep: flat by 3:10 PM CT, auto-flatten from 3:08. MLL is monitored intraday on unrealized P&L and liquidates by market order | OFFICIAL (venue) | venue_rules/…; fill_models/fill_models.md |
| F8 | Topstep Tier-1 windows (CPI, NFP, PPI, FOMC decision, FOMC press conference), ±5 min: micros capped at 1/3/6/9/15 contracts by account size. Pending orders don't fill, but reducing brackets are accepted | OFFICIAL (venue) | venue_rules/…; economic_events/economic_events.md |
| F9 | Round-turn fees are $1.22 for MES and MNQ at Topstep, the same as IBKR's base tier | OFFICIAL | execution_costs/execution_costs_mes_mnq.md |
| F10 | Velocity Logic can pause the equity group and eliminate market orders. A protected stop can rest unfilled at its protection limit. NQ/MNQ have a ±3.5%/hour dynamic circuit breaker with a 2-minute pause | OFFICIAL | execution_costs/…; fill_models/… |
| F11 | Topstep says SIM has less slippage than real markets | OFFICIAL (venue) | execution_costs/… |
| F12 | Every vendor reviewed stamps bars at bar start and omits empty minutes. Databento timestamps are UTC | VENDOR | providers/… |
| F13 | BLS CPI, PPI and Employment Situation are released at 8:30 ET. FOMC statements are released at 2:00 PM ET (verified only for the sampled releases) | OFFICIAL | economic_events/… |
| F14 | The 2025 shutdown (Oct 1 – Nov 12) cancelled Oct 2025 CPI, NFP and PPI and moved others. A 2026 lapse moved Jan 2026 NFP and CPI. BLS pages are revised in place | OFFICIAL | economic_events/…; event_calendar_2025_2026.csv |
| F15 | Mesfin, MNQ RTH 5-minute bars, 947 days, walk-forward, $4 round turn: ORB long +2.82 pts net, T=0.88, FAIL | study fact | orb_evidence/orb_evidence.md |
| F16 | Fetna (pre-registered): 0/225 cells pass. Power needs about 13,000 trades to detect $25, against about 1,800 available | study fact | orb_evidence/fetna_2026_addendum.md |
| F17 | RX-0001 rerun reproduces exactly. N_eff ranges 2–22 (mostly 8–13). Gate-arm DSR is 0.926 at N=24 and 0.948–0.960 at N 13–9. PBO 0.69–0.76 fails the PBO < 0.5 gate, so the verdict stays "no edge shown" | computed | validation/rx0001_rerun/rx0001_rerun.md |
| F18 | The repo gate is pooled OOS > 0 AND DSR ≥ 0.95 AND PBO < 0.5, measured at next_open and 5 bps | repo fact | validation/rx0001_rerun/… |

### 1b. Indirect evidence
| # | Claim | Label | Source file |
|---|---|---|---|
| I1 | ES spread is one tick almost always (2008–11). ES Velocity Logic thresholds are 6 ticks/1 ms and 18 ticks/1 s (academic) | indirect | execution_costs/… |
| I2 | Intraday momentum concentrates in the last half hour. S&P futures show about 10 minutes of opening continuation, then reversal, weakened after costs | indirect | orb_evidence/… |
| I3 | Vendors converge on an open-proximity path heuristic and next-open gap fills. This shows shared practice, not accuracy | VENDOR / CONV | fill_models/… |
| I4 | Within each rule, the cost and fill stress arms correlate at ≥ 0.86, which supports treating them as not being separate trials | computed | validation/rx0001_rerun/… |
| I5 | Topstep's CT event times line up with official ET release times | indirect | economic_events/… |
| I6 | The 2024-12-11 Databento unit prices (dated; current rates may differ). Kibot ES used as a proxy for MES | VENDOR | providers/… |
| I7 | Scaling micro costs makes Fetna's $25 a favourable case for MES/MNQ (×10 estimate) | ESTIMATE | orb_evidence/fetna_2026_addendum.md |

### 1c. Hypotheses to test (open)
| # | Hypothesis | Label | Source file |
|---|---|---|---|
| H1 | MES/MNQ RTH ORB has a net edge after L1–L4 costs. Prior evidence leans against (F15, F16); treat as a falsification target | hypothesis | orb_evidence/… |
| H2 | The share of ambiguous 1-minute bars (stop and target both touched) is small enough that the fill option doesn't change the verdict | hypothesis | fill_models/… |
| H3 | Actual MES/MNQ spread and depth at 9:30–10:00 ET fit within L1/L2 | hypothesis | execution_costs/… |
| H4 | Results are stable across roll rules and across the shifted June 2026 expiry | hypothesis | contracts/… |
| H5 | Excluding event days or event windows doesn't flip the verdict | hypothesis | economic_events/… |
| H6 | Results beat a random-anchor / random-direction control | CONV | validation/validation_methods.md; orb_evidence/… |
| H7 | ProjectX keeps bar history for expired contracts | hypothesis | venue_rules/… |
| H8 | Databento `status` / `definition` can supply a historical holiday and early-close calendar | hypothesis | providers/… |

### 1d. Rejected claims
| # | Rejected claim | Why | Source file |
|---|---|---|---|
| R1 | "Expiry = 3rd Friday" can be computed by formula | CME lists the June 2026 expiration as 6/18 (Thursday; Juneteenth) | contracts/… |
| R2 | An automated system can trade Topstep Live | There is no API in Live, and the call-up closes XFAs (F6) | venue_rules/… |
| R3 | The session ends at the 4:00 PM CT CME close for Topstep accounts | Flatten is at 3:08–3:10 PM CT (F7) | venue_rules/… |
| R4 | SC-0002's "86" counts trials | They are records (3 rules) | validation/validation_methods.md |
| R5 | Cost and fill arms are independent trials | Correlation ≥ 0.86 (I4); trial-family table | validation/… |
| R6 | Spreads can be estimated from daily OHLC; fees alone (L0) are an adequate cost | Contradicted for market and stop orders | execution_costs/… |
| R7 | SIM / Practice fills prove costs | Topstep itself says SIM slippage is lower (F11) | execution_costs/… |
| R8 | The current BLS pages show the point-in-time schedule | They are revised in place (F14) | economic_events/… |
| R9 | Daily OHLCV bars from Databento match CME session dates | They use UTC dates | providers/… |

### 1e. Conflicts (preserved, not resolved)
- **C1:** the spec says "3rd Friday" but the calendar says 6/18/2026. Whether the last trade time moved is unresolved.
- **C2:** the settlement window changed in 2020 (15:15 → 15:00 CT), so historical "settle" fields are not homogeneous.
- **C3:** vendors disagree on limit fills (touch vs trade-through) and on stop fill prices (open vs close). Fetna's "stop first" convention conflicts with the path heuristic.
- **C4:** Fetna finds 5 minutes the worst window, while Zarattini finds 5 minutes optimal (futures vs equities). NQ is net positive in aggregate, yet no NQ cell passes.
- **C5:** N_eff methods range from 2 to 22. PBO ranges from 0.39 to 0.76 depending on S and the cost arm. ONC k=2 conflicts with the hierarchical counts.
- **C6:** SIM fills are optimistic, yet Practice is the only fill venue that can be automated.
- **C7:** Topstep venue Conflicts 1–5 (see venue_rules/).
- **C8:** in Tsai, results conflict between versions.

## 2. Five design implications for the QAB MES/MNQ ORB harness (options, not decisions)
1. **Versioned contract and session calendar artifact.**
   - Contents: dated contracts on raw prices; expiries taken from the CME calendar, not a formula (R1); the roll map (rule is open); holidays and early closes; the Topstep session and the 3:08/3:10 CT flatten; storage in UTC.
   - Implementation details are left open.
   - Sources: Packages 1, 2, 3.
2. **Forced flatten and venue constraints as engine events.**
   - Liquidate by 3:08–3:10 CT.
   - Check MLL on unrealized P&L.
   - In Tier-1 windows: block opening fills, apply the micro cap, accept reducing brackets.
   - Sources: Packages 2, 8.
3. **Fill and cost stress columns.**
   - Log the ambiguous-bar condition for every trade.
   - Carry fill options (1a/1b/1c, 3a/3c, etc.) and cost levels L1–L4 plus the L5 no-fill / pause scenario as **sensitivity arms, not trials**.
   - Report MES and MNQ separately, plus in ES/NQ-equivalent terms.
   - Sources: Packages 4, 6, 7.
4. **Event calendar with original vs actual times.**
   - Keep one row per release, with original_scheduled, actual and status (including cancelled and unscheduled), plus source and snapshot.
   - Key filters on the schedule as known at the time of the decision, not on revised pages (R8).
   - Sources: Package 8.
5. **Trial accounting.**
   - Persist per-trial daily P&L series, measuring SR on daily P&L.
   - Keep a trial ledger with a selectable/sensitivity flag and the N_eff method recorded.
   - Report PBO across S values and arms; report power/MDE; run a random-anchor control.
   - Exclude stress arms from CSCV.
   - Sources: Packages 5, 6 and the rx0001_rerun.

## 3. Bounded falsification tests (no parameters chosen)
| Test | Question | Data needed | Cost | Pass / fail (gates) |
|---|---|---|---|---|
| T1 Base ORB falsification | Does any pre-registered MES/MNQ ORB family clear the gate after costs? | MES/MNQ dated 1-minute bars plus the calendar artifact | Free if existing Tiingo/other is adequate (it is not MES/MNQ-native). **Databento OHLCV-1m: needs Jason's approval, unpriced** | Pass only if pooled OOS > 0 AND DSR ≥ 0.95 (at the chosen N_eff method) AND PBO < 0.5, at the base cost/fill arm and holding under stress arms. Otherwise H1 is rejected |
| T2 Random-anchor control | Does the best ORB family beat random anchors and directions? | Same as T1 | Same as T1 | Pass if the family exceeds the chosen percentile of the random-anchor distribution (percentile is QAB). Otherwise treat the result as noise |
| T3 Ambiguous-bar tick sample | Does the fill option change the verdict? | About 60 RTH sessions (stratified, including FOMC/CPI/roll weeks) of trades/TBBO + 1-minute + Status | **Databento: Jason's approval, unpriced** | Pass (H2) if the verdict is the same under all fill options. Fail if any option flips the gate outcome |
| T4 Spread/depth check | Is L1/L2 realistic at the open? | CME Liquidity Tool export (Jason's login), or a TBBO sample | Liquidity Tool free with login; **Databento needs approval, unpriced** | Pass (H3) if the measured opening spread/slippage is ≤ the base level; otherwise move the base cost to the higher level and re-run the gate |
| T5 Roll / calendar robustness | Is the verdict stable across roll rules and the 6/18-type shift? | T1 data plus the calendar | No extra cost | Pass if the gate outcome is identical across roll options |
| T6 Event sensitivity | Do event days drive the result? | T1 data plus event_calendar (PIT gaps filled, or labelled) | Free; Wayback/FRASER needs approval | Pass (H5) if the gate outcome is unchanged across event-filter options a–h |
| T7 ProjectX retention probe | Is there expired-contract history? | One retrieveBars call (Practice) | Needs the API subscription and Jason's approval | Pass if expired 1-minute bars are returned |

## 4. Open decisions for Jason (consolidated)
| Decision | Options | Package |
|---|---|---|
| Cost levels | **DECIDED D-COST-01 (2026-10-22):** L1–L5 carried as stress columns; gate level L3 (MES $6.22 / MNQ $3.22 RT). See decisions_log.md. Still open: slippage reference price | 4 |
| Roll policy | CME Monday-before / volume-OI / fixed days / vendor c/n/v; handling of shifted expiries; indicators across rolls | 1 |
| Effective-N method | Hierarchical cutoff / ONC / eigen; cutoff value; SC-0002 trials to add (3–9) | 6, rerun |
| PBO blocks | CSCV S value(s); report across S; stress arms excluded | 6, rerun |
| Embargo / block length; random-anchor draws; power/MDE reporting | — | 5, 6 |
| Fill stress options | Rows 1–6 (path heuristic, stop-first, limit touch vs trade-through, gap, halt/no-fill, flatten price) | 7 |
| Event filter options | a–h (none / exclude days / ±5-min / venue model / stratify / original-vs-actual arms / expanded set / holidays) | 8 |
| Tick-sample pricing | Approve a priced Databento lookup for the 60-session sample (or not) | 7 |
| Databento signup and get_cost | Free signup; `get_cost` only | 3, 4 |
| Wayback/FRASER fill | Approve retrieval of PIT original schedules | 8 |
| CME Liquidity Tool | Jason logs in and exports MES/MNQ spread and depth by hour | 4 |
| Fetna repo / SSRN | Optional read-only extraction of ES/NQ cells | 5 |
| ProjectX API subscription for probe T7 | $29/mo ($14.50 with code) | 2 |
| Flatten time / Tier-1 blackout / bracket mode | ≤ 3:08 CT; blackout vs model | 2 |
| Raw-data storage | Gitignored raw data, manifests and checksums only | 3 |

## 5. Proposed PLAN.md changes (proposals only; PLAN.md not edited)
- **P1.** Add the "versioned contract/session/event calendar artifact" as a Tier-1 dependency before any backtest.
- **P2.** Record the hard constraint "Live = manual only; automation is limited to Practice/Combine/XFA".
- **P3.** Restate MES/MNQ ORB as a falsification target, citing Mesfin, Fetna and RX-0001.
- **P4.** The runner must persist per-trial daily series, keep a trial ledger with selectable/sensitivity flags, record the N_eff method, and report PBO across S.
- **P5.** Stress arms (cost, fill, event, roll) are sensitivity columns, not trials, and are excluded from CSCV.
- **P6.** Before any ORB claim is promoted, require T3/T4 (fill and cost reality checks), with Databento steps gated on Jason's approval.
- **P7.** Raw vendor data stays gitignored; only manifests and checksums are committed.
- **P8.** Add a Wayback/FRASER PIT-calendar task (optional, approval-gated).

## Verified facts
- The synthesis uses only Packages 1–8. Every claim links to its file.
- Prior ORB evidence (Mesfin, Fetna, RX-0001) contains no gate pass.
## Indirect evidence
- I1–I7 above.
## Conflicting evidence
- C1–C8 above, preserved.
## Unknowns
- MES/MNQ spread and depth.
- The share of ambiguous bars.
- PIT originals outside the lapse table.
- Early-close times.
- ProjectX retention.
- Databento current prices and licence.
## Engineering assumptions
- Everything in §4. None was chosen.
## What was new
- Consolidation alone. No new facts were added.
## What it confirmed
- ORB is a falsification target.
- Stress arms are not trials.
- A calendar artifact is a prerequisite.
## Roadmap changes
- P1–P8 (proposed).
## What should not change
- The gate.
- The RX-0001 verdict.
- No Databento.
- No strategy code.
- No parameter choices.
## Next bounded action
- Jason resolves §4, starting with the cost levels, roll policy and N_eff method.
- He then decides whether to approve pricing for T1/T3 data.

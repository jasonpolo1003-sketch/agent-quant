---
title: MES/MNQ contract, session and rollover facts (Package 1)
package: 01_contracts
status: unreviewed
promoted: false
created: 2026-10-22
retrieved: 2026-10-22
author: Grok Bot (research only; no strategy code, no parameter choices)
---

# MES/MNQ contract, session & rollover facts

Labels: **[OFFICIAL]** = exchange (CME) fact · **[VENDOR]** = a data vendor's own method · **[CONVENTION]** = industry convention (not an exchange rule) · **[QAB-OPTION]** = engineering options for QAB, none chosen.
All quotes were string-matched against saved snapshots in `../source_files/` (37/37 PASS; see `quote_verification.tsv`). CME pages were captured by rendering in a real Chrome session on 2026-10-22 ~09:35–09:45 UTC-5 (CME blocks plain HTTP fetches).

## 1. Contract identity [OFFICIAL]
| Item | MES | MNQ | ES (ref) | NQ (ref) |
|---|---|---|---|---|
| Multiplier | $5 x S&P 500 (Q2) | $2 x Nasdaq-100 (Q4) | $50 x S&P 500 | $20 x Nasdaq-100 |
| Tick | 0.25 pt = **$1.25** (Q1) | 0.25 pt = **$0.50** (Q3) | 0.25 pt = $12.50 (Q5) | 0.25 pt = $5.00 (Q6) |
| Calendar-spread tick | 0.05 pt = $0.25 | 0.05 pt = $0.10 | 0.05 pt = $2.50 | — |
| Globex code | MES (Q15) | MNQ (Q16) | ES | NQ |
| Listed | Mar/Jun/Sep/Dec, 5 consecutive quarters (Q9) | same (Q10) | 21 consecutive quarters (Q11) | — |
| Settlement | Financially settled (Q14) | Financially settled | cash settled (Q29) | — |
| Last trade | 9:30 a.m. ET, 3rd Friday of contract month (Q12) | same (Q13) | — | — |
| Rulebook chapter | CME 353 | CME 361 | 358 | — |

Month codes [OFFICIAL]: H=Mar, M=Jun, U=Sep, Z=Dec (Q17–Q20). Symbol = root+month+year digit, e.g. `MESZ6` was shown as the active Globex code on the MES page at retrieval.

## 2. Sessions, maintenance break, time zone [OFFICIAL]
- Globex: "Sunday 6:00 p.m. - Friday - 5:00 p.m. ET (5:00 p.m. - 4:00 p.m. CT) with a daily maintenance period from 5:00 p.m. - 6:00 p.m. ET (4:00 p.m. - 5:00 p.m. CT)" (Q7 MES, Q8 MNQ).
- "Trading hours are subject to change and are in U.S. Central Time unless otherwise stated." (Q24)
- **Daylight saving [CONVENTION / inference, not stated by CME]:** hours are fixed in CT wall-clock time, so their UTC equivalent shifts by one hour at US DST changes (CDT = UTC-5, CST = UTC-6). Store UTC plus exchange-local time and derive session date from CT. No CME page saved in this package states DST handling explicitly.
- Session-date convention (trade date starts 5:00 p.m. CT the evening before) is implied by the hours and the holiday table ("TRADE DATE: FRI 27 NOV … 17:00 OPEN" on Thursday 26 Nov). Treat as **[OFFICIAL, implied]**; confirm against CME trade-date definitions in Package 2/4.

## 3. Holidays & early closes [OFFICIAL]
- 2026 Globex holiday windows include Thanksgiving 26–28 Nov 2026, Christmas 24–26 Dec 2026, New Year's 31 Dec 2026–1 Jan 2027, Juneteenth 18–19 June 2026 (Q26).
- "Trading hours are usually finalized approximately two weeks prior to the holiday." (Q25) and schedules are "subject to input from the New York Stock Exchange (NYSE) and the Securities Industry and Financial Markets Association (SIFMA)."
- Per-holiday early-close times are in CME's per-holiday notes/downloadable calendars, which were **not** captured here → Unknown. For history, the current page does **not** give past years: a historical holiday archive is required.

## 4. Daily settlement [OFFICIAL]
- MES: "Daily settlement of the Micro E-mini S&P futures (MES)and  E-Nano S&P 500 (NES) are equal to the daily settlement price of the E-Mini S&P 500 futures (ES)." (Q27)
- ES lead month: VWAP of Globex trades 14:59:30–15:00:00 CT, rounded to .25 (Q28); fallbacks are bid/ask midpoint, then a cash-index carry formula.
- History note (search snippet, not saved — **lead**): CME SER-8591 (Sept 2020) moved this window from 15:14:30–15:15:00 CT to 14:59:30–15:00:00 CT. Pre-2020 settlement prices therefore use a different window.
- MNQ/NQ daily settlement method: **not captured**. A snippet says it is "determined by CME Group staff based on…" → Unknown.
- Final settlement at expiry is via the Special Opening Quotation (SOQ) of the index (wiki links to "Understand the SOQ"); details not captured.

## 5. Roll conventions
- [OFFICIAL] "CME Group Equity Index futures allow market participants to roll their futures positions from one quarterly futures contract month to the next at any time they choose." (Q22). So the exchange itself does not enforce a roll date.
- [OFFICIAL-published CONVENTION] "Equity products roll date is the Monday prior to the third Friday of the expiration month.*" (Q21); "After the roll date, it is customary to identify the second nearest expiration month as the “lead month”…" (Q23). CME publishes this, but calls it customary.
- CME table: 2026 roll/expiry pairs (US indexes): Mar 3/16→3/20, Jun 6/15→**6/18**, Sep 9/14→9/18, Dec 12/14→12/18; 2027: 3/15→3/19, 6/14→6/18, 9/13→9/17, 12/13→12/17.
- Volume/OI migration: no data captured. CME's Quarterly Roll Analyzer is linked but is an interactive tool → Unknown; we need to measure it ourselves from per-contract daily volume/OI.

## 6. Continuous series
- [VENDOR: Databento] "The continuous contract prices returned are the original, unadjusted prices. We don't create a synthetic time series by back-adjusting the prices to remove jumps during rollovers." (Q30). Format `[ROOT].[ROLL_RULE].[RANK]` (Q31). The rules are `c` (calendar/nearest expiry), `n` ("Will rank the expirations by the open interest at the previous day's close." Q32) and `v` ("…previous day's trading volume." Q33). "We do not retroactively reassign symbols in our historical data." (Q34). The symbology mapping returns per-date instrument IDs, so a dated contract is recoverable.
- [CONVENTION: Premium Data/Norgate] Difference back-adjustment: "Only those prices prior to the last roll date are adjusted." (Q35); "every time a new contract is added to the series, the back-adjusted contract is re-calculated and all previous prices are adjusted." (Q36); "Traders looking for real historical prices should consult their spliced charts." (Q37).
- [CONVENTION, lead only, snapshot not saved] Ratio (proportional) adjustment multiplies earlier prices by the roll ratio. It preserves % returns but distorts point moves and the tick grid. Leads: Vojtko & Padysak, SSRN 3517736; PortaraCQG ratio-adjust note; QuantStart (fetch returned 503).
- CQG continuous-symbol rules: help page not retrievable → Unknown (carry to Package 3 providers).

## 7. Purpose → data representation (critical table)
| Purpose | Representation | Justification | Label |
|---|---|---|---|
| Broad charting / regime context | Back-adjusted (difference) continuous, or unadjusted with roll markers | Removes spurious roll gaps for visual trends; levels are not real (Q37) | CONVENTION |
| Indicator research (returns, vol, %-based) | Ratio-adjusted continuous **or** per-contract indicators restarted/warm-started at roll | Difference-adjusting distorts % returns in old data; ratio preserves % | CONVENTION / QAB-OPTION |
| Intraday ORB-style indicators on one session | Raw dated contract for that session (the contract actually traded that day) | Intraday window never spans a roll if the roll map is per session date; no adjustment needed | QAB-OPTION |
| Entry/stop/target prices | **Raw dated contract prices only** | Must sit on the real 0.25 tick grid (Q1, Q3); adjusted levels were never tradable | OFFICIAL (tick) + CONVENTION |
| Fill simulation | Raw dated contract minute bars (plus tick/quote samples where available) | Fills happen in a specific contract; Databento continuous prices are unadjusted and map to instrument IDs (Q30, Q34) | VENDOR + QAB-OPTION |
| P&L and tick accounting | Raw contract: ticks × $1.25 (MES) / $0.50 (MNQ) | Point P&L × multiplier is exact only on raw prices | OFFICIAL |
| Roll analysis | Every dated contract side by side: volume, OI, calendar-spread price | Roll timing is the trader's choice (Q22); the customary date (Q21) must be checked against migration we measure | OFFICIAL + CONVENTION |

QAB roll-rule options (none chosen): (a) CME customary Monday-before-3rd-Friday; (b) Databento `v.0` previous-day-volume; (c) `n.0` open interest; (d) fixed N days before expiry. All must produce a per-session-date contract map stored with the data.

## Source records
| # | Title | Org | URL | Pub date | Type | Instrument | sha256 (txt) | Limitations | Applicability |
|---|---|---|---|---|---|---|---|---|---|
| S1 | Micro E-mini S&P 500 Contract Specs | CME Group | https://www.cmegroup.com/markets/equities/sp/micro-e-mini-sandp-500.contractSpecs.html | not stated (live page) | exchange spec | MES | 52ed30f85cd3e6fb… | live page; changes without versioning | direct |
| S2 | Micro E-mini Nasdaq-100 Contract Specs | CME Group | https://www.cmegroup.com/markets/equities/nasdaq/micro-e-mini-nasdaq-100.contractSpecs.html | not stated | exchange spec | MNQ | 2587572664cf0df2… | same | direct |
| S3 | E-mini S&P 500 Contract Specs | CME Group | https://www.cmegroup.com/markets/equities/sp/e-mini-sandp500.contractSpecs.html | not stated | exchange spec | ES | 8923a2ad9f3f4082… | reference only | proxy |
| S4 | E-mini Nasdaq-100 Contract Specs | CME Group | https://www.cmegroup.com/markets/equities/nasdaq/e-mini-nasdaq-100.contractSpecs.html | not stated | exchange spec | NQ | ed37f0ddfed28b88… | reference only | proxy |
| S5 | CME Group Holiday and Trading Hours | CME Group | https://www.cmegroup.com/trading-hours.html | 2026/2027 schedule | exchange calendar | all Globex | 00d7ec315faa066b… | current years only; per-holiday times not captured | direct (current) |
| S6 | Equity Index Roll Dates | CME Group | https://www.cmegroup.com/trading/equity-index/rolldates.html | covers 2025–2028 | exchange notice | US equity index futures | c9cdeaa6cc0a18f9… | customary roll, not a rule; no history before 2025 | direct |
| S7 | Contract Month Codes | CME Group | https://www.cmegroup.com/month-codes.html | not stated | exchange reference | all | fe17fbdc31c3987c… | — | direct |
| S8 | E-Mini Standard and Poors 500 Futures (settlement) | CME Client Systems Wiki | https://www.cmegroup.com/confluence/display/EPICSANDBOX/E-Mini+Standard+and+Poors+500+Futures | "Updated Aug 20" | exchange procedure | ES/MES | 04ccb941b4e76c47… | no MNQ; pre-2020 window not on page | direct (MES) |
| S9 | Symbology | Databento | https://databento.com/docs/standards-and-conventions/symbology | not stated | vendor docs | GLBX.MDP3 futures | b2600c205441a58b… | vendor method only | direct for data sourcing |
| S10 | Continuous Contracts Explained Part 2 | Premium Data (Norgate) | https://www.premiumdata.net/support/futurescontinuous2.php | not stated | vendor education | generic futures | e8cb4a3720b329a2… | examples are commodities | indirect |
Full checksums (html + txt) are in `../_sha256.txt`. Retrieval date for all: 2026-10-22.

## Verified facts
- MES tick is 0.25 pt = $1.25; MNQ tick is 0.25 pt = $0.50. Both trade quarterly (H/M/U/Z), with 5 quarters listed, are financially settled, and stop trading at 9:30 a.m. ET on the 3rd Friday.
- Globex runs Sun 5:00 p.m. to Fri 4:00 p.m. CT, with a daily 4:00–5:00 p.m. CT maintenance break. CME hours are in CT.
- MES daily settlement equals ES settlement: the 14:59:30–15:00:00 CT VWAP.
- CME's customary roll is the Monday before the 3rd Friday, but rolling is the trader's choice.
- Databento continuous symbols are unadjusted and map to real instrument IDs, with c/n/v roll rules.
## Indirect but credible evidence
- Premium Data's difference back-adjustment description. Ratio vs difference trade-offs (leads, snapshot not saved).
## Conflicting evidence
- Spec says expiry is the "3rd Friday", but CME's roll table lists **June 2026 expiration 6/18 (Thursday)**. 19 June 2026 is a Friday and the Juneteenth holiday. Holiday-shifted expiries must therefore come from the calendar, not a formula. Unresolved: whether last trade moved to Thursday 18 June.
- Settlement window changed in 2020 (15:15 → 15:00 CT), per the lead source. Historical "settle" fields are not homogeneous.
## Unknowns
- MNQ/NQ daily settlement method; SOQ final-settlement details.
- Per-holiday early-close times (current and historical); a historical holiday archive.
- Explicit CME statement on DST.
- Observed volume/OI migration dates for MES/MNQ (needs data).
- CQG/other vendor continuous rules.
- Whether Topstep/ProjectX use their own roll or contract-mapping rules (Package 2).
## Engineering assumptions still required
- Roll rule (options a–d above); session-date definition in code; DST/UTC storage; holiday-calendar source for history; how to treat 6/18-type shifted expiries; whether indicators may span a roll.
## What was genuinely new
- The June 2026 Thursday expiration anomaly; MES settles to ES, not its own trades; Databento does not back-adjust; the 2020 settlement-time change.
## What confirmed an existing decision
- Store dated contracts, not just continuous symbols. Do all price/fill/P&L work on raw prices.
## What should change in the roadmap
- Add a versioned contract-calendar artifact (expiry, roll map, holidays, early closes) as a Tier-1 dependency before any backtest. Add the historical holiday/early-close archive to Package 3 (providers) requirements.
## What should not change
- The 9-step order; Package 2 (Topstep/ProjectX) next.
## Next bounded action
- Package 2: official Topstep/ProjectX rules per stage. In parallel, a 10-minute check of CME holiday notes for the Juneteenth 2026 MES/MNQ last-trade time and MNQ settlement procedure (adds 2 sources).

## Addendum 2026-10-22 (side check from Package 2; quotes V62–V66 in ../venue_rules/quote_verification.tsv)
- [OFFICIAL] MNQ/NQ daily settlement: settlements "are determined by CME Group staff based on trading and market activity on CME Globex." The lead month "settles to the volume-weighted average price (VWAP) of the trade(s) during this period" (14:59:30–15:00:00 CT). "Daily settlement of the Micro contracts are equal to the settlement price of their associated Mini contracts." Source: CME Client Systems Wiki, Nasdaq-100 page (Updated Aug 20), snapshot `source_files/cme_wiki_nq_mnq_settlement.*`. This resolves the MNQ settlement unknown.
- [OFFICIAL] Juneteenth 2026: "Note: Friday June 19, 2026 CME Group will not derive or disseminate settlement prices for CME," and all products settled at normal times Thursday 6/18 (`source_files/cme_juneteenth_2026_settlement.pdf/.txt`). Final settlement uses the SOQ, described as "on expiration Friday" (`cme_final_settlement_soq.*`). **Still unresolved:** the exact last-trade time on 6/18/2026. That needs CME's Juneteenth trading-hours holiday note or an SER.

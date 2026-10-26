---
title: Phase B calendar addendum (gap-fill to Package 1)
status: unreviewed
promoted: false
date: 2026-10-22
retrieved: 2026-10-22
---
# Phase B calendar addendum — DST, settlement history, holidays, roll migration, symbol mapping

Quotes verified in `contracts/phaseB_quote_verification.tsv` (10/10 MATCH). Classification in brackets.

## 1. Daylight saving / session-date treatment
- CME states hours in Central Time: "Trading hours are subject to change and are in U.S. Central Time unless otherwise stated." (CME Group Holiday and Trading Hours, cmegroup.com/trading-hours, saved `source_files/cme_trading_hours_holidays.txt` L41) [official] **OFFICIAL FACT**.
- Consequence (inference): sessions are anchored to America/Chicago wall clock, so UTC offsets shift by one hour on US DST changes; Databento timestamps are UTC nanoseconds (Package 3). Engine must convert UTC→America/Chicago with a tz database, never a fixed offset. **QAB ENGINEERING POLICY (proposed)**.
- Session-date (trade date) convention: Globex session opening 5:00 PM CT Sunday–Thursday belongs to the next trade date (Package 1, CME specs). The addendum adds no new source; **CONVENTION** for bucketing evening bars into next trade date — option, not chosen.
- Unknown: whether US/EU DST mismatch weeks (March/Oct–Nov) need any special handling — for CME-only data, no (inference).

## 2. Settlement procedure changes over time
- Package 1 already holds the current ES/MES and NQ/MNQ settlement wiki pages and the Juneteenth 2026 notice. Historical versions of the settlement procedure pages could not be re-pulled: **cmegroup.com now returns an explicit anti-scraping block** ("This IP address is blocked due to suspected web scraping activity … Use of scripts … is strictly prohibited by CME Group's website Data Terms of Use"). Per rules I did not attempt evasion; Wayback lookups for CME pages timed out. **Unknown**: dated history of settlement-procedure changes. Option: Jason opens CME pages in his own browser, or use the Wayback Machine manually.
- Alternative data route: Databento `statistics` schema carries exchange-published settlement prices and open interest (priced below, C8: $0.64 for MES+MNQ 2019→now) [vendor] **VENDOR METHOD** — gives the *values*, not the *procedure*.

## 3. Historical holidays / early closes (CME)
- "with the 2026 and 2027 calendar year the CME Group will be providing downloadable holiday calendars for Globex" (same CME page, L19) [official] **OFFICIAL FACT** — so downloadable files exist only from 2026; earlier years need per-holiday notices or reconstruction.
- Reconstruction option (inference): Databento `status` and `ohlcv-1d/1m` gaps show which sessions actually traded/closed early — empirical, not authoritative. Holiday page refresh blocked (see §2).

## 4. Actual volume / open-interest roll migration
- Official convention: "Equity products roll date is the Monday prior to the third Friday of the expiration month." (CME Equity Index Roll Dates, saved `cme_equity_rolldates.txt` L5) **OFFICIAL FACT/CONVENTION**; and participants may roll "at any time they choose" (L3).
- Free official volume/OI-by-contract history: CME's daily bulletin/volume pages are blocked to scripts (§2). Measurable alternative: Databento `ohlcv-1d` per raw contract (volume) + `statistics` (open interest) — C7 $0.20 + C8 $0.64. Databento's `MES.v.0` (volume-ranked) vs `MES.c.0` (calendar) continuous symbols encode the two roll definitions (Package 3). Evidence of *actual* migration = **unknown until those cheap pulls are approved**.

## 5. Symbol mapping: CME vs Databento vs ProjectX
| System | Example (MNQ Sep 2025) | Source |
|---|---|---|
| CME Globex raw | MNQU5 | CME month codes (Pkg 1) |
| Databento raw_symbol | MNQU5; also numeric instrument_id that "some publishers remap them daily" | db_symbology L785, L860 |
| Databento parent | MNQ.FUT — includes **futures spreads** ("whether the instrument is a future or futures spread") | db_symbology L865, L880 |
| Databento continuous | MNQ.c.0 / MNQ.v.0 / MNQ.n.0 | Pkg 3 |
| ProjectX | id "CON.F.US.MNQ.U25", name "MNQU5", symbolId "F.US.MNQ" | venue/px_search_contracts.txt L47-53 |
- Implication: map on (root, month code, year); store instrument_id per day, never as permanent key. ProjectX uses 2-digit year in id, 1-digit in name. Parent requests include calendar spreads, which must be filtered (instrument_class). **OFFICIAL FACT / VENDOR METHOD**.

## Verified facts
- CME hours in CT; roll-date convention Monday before 3rd Friday; Databento instrument IDs can remap daily; parent symbology includes spreads; ProjectX id format CON.F.US.<root>.<M><YY>.

## Indirect but credible evidence
- Databento statistics/ohlcv-1d as roll-migration proxy (vendor-derived from CME feed).

## Conflicting evidence
- None new; CME convention roll date vs volume-based roll (v.0) may differ — to be measured.

## Unknowns
- Dated history of settlement procedure changes; pre-2026 holiday/early-close list; actual roll migration days.

## Engineering assumptions still required
- tz-aware Chicago session anchor; trade-date bucketing convention; filter spreads from parent pulls.

## What was genuinely new
- CME anti-scraping block on cmegroup.com; parent symbology returns spreads; downloadable holiday calendars only from 2026.

## What it confirmed
- Package 1 roll and session facts.

## Roadmap changes
- Calendar artifact must carry instrument_id per date and a spread filter; holiday table sourced separately pre-2026.

## What should not change
- Old packages 1–9 untouched; no PLAN.md edits; no strategy code; no parameters chosen.
## Next bounded action
- If approved: definition (C6 $0.10) + ohlcv-1d (C7 $0.20) + statistics (C8 $0.64) to build calendar and measure roll migration.

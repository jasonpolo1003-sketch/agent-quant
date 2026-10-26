---
title: Phase B gap-fill summary and Drew handoff
status: unreviewed
promoted: false
date: 2026-10-22
---
# Phase B summary (gap-fill addenda; no code, no parameters chosen)

## Executive summary (plain English)
- Real MES and MNQ 1-minute data for the whole micro history (May 2019→today) costs about **$28.55** from Databento; MES alone is **$9.61–$13.89**. Contract definitions are **$0.10**. Even with a 60-session MES tick sample (~$26), the test fits well inside the $125 credit. Nothing was downloaded.
- Calendar: CME hours are Central Time, so the engine must use a real time-zone database. Databento instrument IDs can change daily and its "MES.FUT" pulls include spreads, so mapping must go through raw symbols per date. ProjectX names contracts differently (CON.F.US.MNQ.U25).
- Events: GDP and PCE come out at 8:30 AM ET, before the open — **except three PCE releases at 10:00 AM ET** (2025-04-30, 2025-12-05, 2026-01-22). Treasury note/bond auctions close at **1:00 PM ET**, inside an all-day hold. CME had an ~11-hour outage on Nov 27–28, 2025.
- 1-minute bars can't tell which of a stop or target hit first, or the bid/ask at a breakout; that needs trades or tbbo samples.
- cmegroup.com now blocks automated access outright, so historical settlement procedures, pre-2026 holidays and official outage notices stayed unverified. I did not try to get around it.

## Contradictions / unknowns
| Item | Status | Resolution route |
|---|---|---|
| CME roll date (Mon before 3rd Fri) vs actual volume roll | unknown | ohlcv-1d + statistics ($0.84) or v.0 vs c.0 comparison |
| Settlement procedure history | unknown (CME blocked) | Jason's browser / Wayback manually |
| Pre-2026 holidays & early closes | unknown | CME notices manually; empirical from bars/status |
| Original pre-shutdown BEA dates | gap (iCal shows current only) | Wayback/FRASER (free) |
| Topstep/ProjectX latency | unknown | trades-based delay test |
| Breakout spreads MES/MNQ | unknown | tbbo sample ($43) |
| Licensing text (Databento/CME) | leads only | read Databento catalog license in browser |
| Older CME outages (pre-2025) | unverified | status schema scan |

## What Drew should implement (facts and options only)
1. Session clock anchored to America/Chicago with tz database; trade-date convention for evening session (option).
2. Contract table keyed by (root, month, year) with per-date instrument_id; filter spreads by instrument_class; ProjectX id mapping CON.F.US.<root>.<M><YY>.
3. Roll policy options: CME roll-date convention / Databento v.0 / measured volume-OI cross (Jason decides).
4. Event calendar types: BLS (Pkg 8), BEA GDP/PCE (time per row, not assumed 8:30), FOMC, Treasury auctions (1:00 PM ET notes/bonds), outages/halts (status schema).
5. Fill model: 1m bar logic per Package 7 options + same-bar ambiguity flag; optional trades/tbbo calibration.
6. Costs: L1–L5 stress columns, L3 gate (D-COST-01).
7. Data loader layout for R-B/R-C (raw dated ohlcv-1m + definition), raw files gitignored, sha256 manifests.

## Verified facts
- Prices (get_cost), CME CT hours, roll-date convention, Databento symbology notes, ProjectX ids, BEA times, Treasury auction close times.
## Indirect but credible evidence
- Outage coverage (CNBC, DCD citing Bloomberg); licensing leads.
## Conflicting evidence
- None new beyond Package 9's eight preserved conflicts.
## Unknowns
- See table.
## Engineering assumptions still required
- Trade-date bucketing, roll policy, latency, event types used as filters vs stress subsets.
## What was genuinely new
- Exact Databento prices; 10:00 AM ET PCE releases; 1:00 PM ET auctions; CME anti-scraping block; parent symbology includes spreads.
## What it confirmed
- Packages 1, 3, 7, 8.
## Roadmap changes
- Proposed (not applied): event calendar gains BEA/Treasury/outage types; calendar artifact stores instrument_id per date.
## What should not change
- PLAN.md, old packages, no strategy code.
## Next bounded action
- Jason chooses a request option (R-A/R-B/R-C/R-D, ± trades sample).

---
title: Drew ORB build handoff (Phase B)
status: unreviewed
promoted: false
created: 2026-10-23
---
# Drew ORB build handoff

This is a handoff only. It contains no strategy code and no parameter picks beyond what the decisions log records. **Freeze all rules and open decisions in writing before the test runs, then run it once and accept the result.** No re-runs with tweaked parameters.

## Ready
1. **Data (R-C, Databento GLBX.MDP3, licensed, do not redistribute or commit):** `C:\Users\jason\OneDrive\Desktop\Quant\data\databento\rc_2026-10-22\` (box: `/workspace/data/databento/rc_2026-10-22/`). Contents: ohlcv-1m, ohlcv-1d, statistics, and definitions (canonical = `def_years\` per-quarter files, 124,454 records). Covers MES/MNQ outrights from 2019-05-01 to 2026-10-21. 33/33 checksums verified on JPolo. The `parts\` folder is just split copies.
2. **Data quality:** `validation/rc_data_quality/rc_data_quality.md`. It found no bad, duplicate or off-tick prices, and the 1m bars sum to the 1d bars on 4,654 front days. Must handle:
   1. A missing minute means no trade. Never forward-fill a bar into fills.
   2. Holiday early closes and the pre-2021 15:15–15:30 CT halt come from the session calendar, not from the bars.
   3. Exclude or flag 2025-11-28 (Globex outage, 10.8 h gap) and 2020-03-16 (limit-down reopen).
   4. The daily file is keyed by UTC date. Rebuild CME trade-date bars from the 1m data.
   5. Tick value: hard-code MES $1.25 and MNQ $0.50 (the definitions field is ×0.01).
   6. CPI and tariff outlier bars are real. They belong to the event-filter decision.
3. **Costs, D-COST-01:** carry L1–L5 as stress columns. **The gate is L3** (MES $6.22, MNQ $3.22 round turn). See `execution_costs/execution_costs_mes_mnq.md`.
4. **Roll, D-ROLL-01:** fixed calendar roll at expiration minus 8 days (prior business day if a holiday), taken from the start of that trade date. Calendar: `contracts/roll_calendar_2019_2026.csv`, 68 rows (34 MES and 34 MNQ, Jun 2019 to Sep 2027; the rows after Oct 2026 are scheduled from listed definitions). Builder: `contracts/build_roll_calendar.py`. Sensitivity: prior-day-volume roll, see `contracts/roll_volume_check.csv`. **Caution:** prior-day volume had not yet moved to the new contract on any of the 60 historical roll dates. The volume roll lands 2–4 trading days later, so roll-window days should be reported separately in the cost/fill stress.
5. **Events:** `economic_events/event_calendar_2025_2026.csv`, `phaseB_bea_gdp_pce_calendar.csv`, `phaseB_treasury_auctions_2025_2026.csv`, and the notes in `economic_events.md` and `phaseB_events_addendum.md`. Point-in-time history before 2025 is a known GAP.
6. **Fill models:** options tables in `fill_models/fill_models.md` and `phaseB_fill_addendum.md` (touch vs trade-through, stop slippage, Velocity Logic pause, price bands). No policy has been chosen.
7. **Repo gate:** OOS > 0, DSR ≥ 0.95, PBO < 0.5. All three must pass at the L3 cost level.
8. **Venue:** the Topstep 3:08–3:10 PM CT flatten and the ±5-minute news windows. See `venue_rules/topstep_projectx_rules.md`.

## Still open for Jason (must be frozen before the run)
- Effective-N method and cutoff for DSR (hierarchical, ONC or eigenvalue; the RX-0001 rerun gave 2–22, mostly 8–13).
- PBO/CSCV block count.
- Which fill options to carry as stress cases.
- Event filter: which options and windows.
- Flatten time and bracket mode.
- Optional: tick-sample purchase (needs a price check and approval first) and the ProjectX subscription.

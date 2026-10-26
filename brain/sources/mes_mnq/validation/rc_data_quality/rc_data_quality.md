---
title: R-C Databento data-quality scan (MES/MNQ, GLBX.MDP3, 2019-05 to 2026-10-21)
status: unreviewed
promoted: false
created: 2026-10-23
script: scan_rc_quality.py (local only, zero Databento API calls)
---
# R-C data-quality scan

**Verdict: clean enough for Drew's ORB test.** No broken prices or structural defects were found. Drew still has to handle the session and calendar items listed under "Required engineering assumptions".

Scope: 7,665,225 outright 1-minute bars (spreads excluded), ohlcv-1d, and 124,454 definition records (29 quarterly files; the `.truncated` file was ignored). The statistics schema was **not** scanned in this pass.
Front month = **the contract with the highest 1-minute volume per CME trade date** (17:00 CT on the prior day to 16:00 CT). This is a scan convenience only, **not a roll policy**.

## Results
| Check | Result |
|---|---|
| Non-positive prices / high<low / open or close outside high-low | 0 / 0 / 0 |
| Prices off the 0.25 tick | 0 |
| Duplicate (instrument, timestamp) | 0 |
| Zero-volume bars | 0 |
| Unmapped instrument_ids vs definitions | 0 |
| Bars inside the 16:00-17:00 CT break | 5 (all at 16:59 CT on 2020-03-30, 2020-03-31 and 2020-06-30; tiny volume) -> `flag_in_daily_break.csv` |
| Front-month jumps (>1% close-to-close, >2% bar range, or >25x rolling median range) | 395 bars -> `flag_front_jump.csv`. By year: 2019 29, 2020 124, 2021 6, 2022 54, 2023 36, 2024 37, 2025 82, 2026 27 |
| Jumps >5% | 1: MESM0 2020-03-16 08:45 CT, -6.3% (reopen after the limit-down halt) |
| 1m aggregated to UTC day vs ohlcv-1d (front month, 4,654 rows) | 0 OHLC mismatches, 0 volume mismatches. Total volume is identical (4,202,737,357) |
| Front-month daily volume anomalies (<0.2x or >5x 20-day median) | 0 |
| Missing weekdays (per root) | 17, all CME full-closure days (Christmas, New Year, Good Friday 2020/22/24/25, 2021-12-24, 2022-12-26, 2023-01-02) |
| Front-month minutes missing vs 1,380 per day | 3,864 root-days; median 0. 2,426 days complete; 311 days with >30 missing; 1,077 days with a gap of 5+ minutes. Median missing by year: 2019 33, 2020 15, 2021 7, 2022 onward 0 |
| RTH 08:30-15:00 CT front-month bars | 3,712 of 3,854 days have all 390; 138 have <380, mostly holiday early closes |
| Nov 2025 outage | Visible: no MES bars from 2025-11-27 20:44 CT to 2025-11-28 07:30 CT (10.8 h). The earlier gap, 12:59-17:00 CT Nov 27, is the normal Thanksgiving halt |
| Definitions | 35 MES + 35 MNQ outrights; tick 0.25; unit_of_measure_qty MES 5 / MNQ 2 (matches $5 / $2); expirations at 13:30 UTC on the 3rd Friday, except M6 (2026-06-18) and M7 (2027-06-17), which move to Thursday for Juneteenth. `min_price_increment_amount` reads 0.0125 / 0.005, a x0.01 display scale (true tick values are $1.25 / $0.50) |

Worst jumps are all real market events: 2020-03-16 COVID reopen; CPI releases at 07:30 CT (2022-07-13, 09-13, 10-13, 11-10; MNQ +2.6% bar); 2025-04-09 12:19 CT tariff-pause rally (MES +2.6%, 3.3% range); 2025-04-06 17:00 CT Sunday open (MNQ -4.5% versus Friday's close).

## Verified facts
- Zero price-integrity, tick, duplicate or zero-volume defects in 7.67M outright bars.
- ohlcv-1m aggregates exactly to ohlcv-1d for every front-month day.
- The Nov 27-28 2025 outage is visible as a 10.8 h hole.
- Multipliers and tick sizes match MES $5 / MNQ $2, 0.25.

## Indirect evidence
- The missing minutes in 2019-2021 look like no-trade minutes. Databento omits bars for minutes with no trades, and micros were thinner in their early years, so this is not data loss.
- The repeated 15-minute gap ending 15:30 CT through early 2021 matches the old 15:15-15:30 CT equity maintenance halt.

## Conflicting evidence
- None among the files. The earlier count of "7 missing weekdays" used a different method; this scan finds 17 full-closure days per root.

## Unknowns
- The statistics schema (settlements, open interest) is unchecked.
- I can't tell whether the 16:59 CT bars on 3 quarter-end days in 2020 are real trades or vendor artifacts.
- 1-minute bars can't show anything inside a minute. That needs the tick sample, which is undecided.

## Required engineering assumptions (Drew must handle)
1. **A missing minute means no trade.** Do not forward-fill a fake bar into fills; treat the minute as empty.
2. **Holiday early closes and the pre-2021 15:15-15:30 CT halt** must come from the session calendar, not be inferred from bars.
3. **Exclude 2025-11-28 (outage) and 2020-03-16 (limit-down) explicitly or flag them in the ORB test**, since the opening range is broken on both.
4. **The daily file is keyed by UTC date, not CME trade date.** Rebuild session bars from the 1-minute data.
5. **Scale the tick value by 100** if you read `min_price_increment_amount`, or hard-code $1.25 / $0.50.
6. **Big CPI and tariff bars are real.** Do not filter them as bad data; they belong to the event-filter decision.
7. **Roll policy is still undecided.** Highest volume per day was used here only for the scan.

## What was new
- Exact defect counts (zeros), the measured outage window, the pre-2021 15-minute halt signature, the Juneteenth expiry shift, and the x0.01 tick-value scale.
## What it confirmed
- The R-C download is complete and internally consistent, and 1m and 1d agree.
## Roadmap changes
- None. Drew can start the calendar and engine on this data.
## What should not change
- Raw data stays outside Git. Roll policy stays Jason's decision. No strategy parameters are set by this scan.
## Next bounded action
- Optional: run a light statistics-schema check (settlement vs 1m close at 15:00 CT), then Jason picks the roll policy.

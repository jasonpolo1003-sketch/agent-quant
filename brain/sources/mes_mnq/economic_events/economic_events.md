---
title: Package 8 — Economic events for MES/MNQ ORB (calendars, point-in-time, Topstep news window)
status: unreviewed
promoted: false
package: 8
date: 2026-10-22
---
# Economic events (no event-filter policy chosen; no strategy code)

Labels:
- **OFFICIAL FACT**: agency, exchange or venue documentation.
- **VENDOR METHOD**: a vendor's own method.
- **CONVENTION**: common practice.
- **QAB ENGINEERING POLICY**: an open option.

Quote IDs (E#) refer to `quote_verification.tsv`; 22/22 string-matched. All retrievals are dated 2026-10-22. All times are ET unless marked CT.

## Provenance
| IDs | Label | Source / URL | Scope | Timeframe | Transferability |
|---|---|---|---|---|---|
| E1 | OFFICIAL FACT | BLS CPI release schedule, https://www.bls.gov/schedule/news_release/cpi.htm (the PPI and Employment Situation pages ppi.htm and empsit.htm were also saved) | US macro releases, market-wide | Forward schedule, currently Oct 2026–Dec 2027 | Direct (release timestamps) |
| E2–E5 | OFFICIAL FACT | BLS, Revised news release dates following the 2025 and 2026 lapses, https://www.bls.gov/bls/2025-lapse-revised-release-dates.htm | Same | Oct 2025–Feb 2026 | Direct; the **only retrieved source that keeps original and revised dates side by side** |
| E6 | OFFICIAL FACT | BLS notice, https://www.bls.gov/bls/092025-cpi-reschedule-notice.htm | CPI | Oct 2025 | Direct |
| E7 | OFFICIAL FACT | BLS CPI shutdown FAQ, https://www.bls.gov/cpi/additional-resources/2025-federal-government-shutdown-impact-cpi-faq.htm | CPI | 2025 | Direct |
| E8 + 24 monthly pages | OFFICIAL FACT | BLS monthly schedules, https://www.bls.gov/schedule/YYYY/MM_sched_list.htm (2025-01…2026-12, snapshots in bls_monthly/) | All BLS releases | Monthly | Direct, but the pages are **revised in place**, so they are not point-in-time |
| E9 | OFFICIAL FACT | Fed press releases monetary20250917a, monetary20260916a and monetary20261007a (.htm under /newsevents/pressreleases/) | FOMC | Per meeting | Direct; the time is verified for only these releases |
| E10–E12 | OFFICIAL FACT | Fed meeting calendars, https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm; 2020 page fomchistorical2020.htm (2019 also saved) | FOMC | 2021–2026 (current); historical by year | Direct (dates, unscheduled and cancelled meetings) |
| E13–E17 | OFFICIAL FACT (venue rule) | Topstep, Risk adjustments high-risk/high-volatility, https://help.topstep.com/en/articles/13613539-risk-adjustments-high-risk-high-volatility (snapshot venue/ts_risk_adjust_hv, Package 2) | Topstep accounts; ES/NQ, MES/MNQ | Current rule; the page shows no effective-date history | Direct for Topstep only |
| E18–E19 | OFFICIAL FACT | CME Group holiday and trading hours, https://www.cmegroup.com/trading-hours.html | Globex | 2026–27 holiday calendars | Direct; the per-product early-close table is JS/downloadable and was **not captured** (GAP) |
| E20 | OFFICIAL FACT | Census economic indicator calendar, https://www.census.gov/economic-indicators/calendar-listview.html | Trade, retail, construction, durable goods | 2027 view (the 2026 view is linked) | Direct |
| E21 | OFFICIAL FACT | DOL weekly UI claims release, https://www.dol.gov/ui/data.pdf | Jobless claims | Weekly, Thursday | Direct (current release only) |
| E22 | OFFICIAL FACT | BEA release schedule, https://www.bea.gov/news/schedule | GDP, PCE / personal income | 2026 (2025 and 2027 tabs exist) | Direct |

## Key findings
**BLS releases.**
- CPI, PPI and the Employment Situation are released at **8:30 AM ET**, an hour before the 9:30 cash open (E1, E4).
- The 2025 lapse in appropriations ran Oct 1 – Nov 12, 2025 (E7).
- Releases were moved or **cancelled outright**: October 2025 CPI, Employment Situation and PPI were cancelled (E3). September 2025 CPI went out on Oct 24 (E6).
- A **2026 lapse** also moved the January 2026 Employment Situation from Feb 6 to Feb 11, and January 2026 CPI from Feb 11 to Feb 13 (E5).
- BLS updates its calendar in place (E2, E8). The current schedule pages show *revised* dates; the original dates survive only in the lapse table.

**FOMC.**
- Statements are released at 2:00 PM ET (E9, verified for the sampled releases). Minutes appear about three weeks later, with the date shown on the calendar (E10).
- The press-conference time (2:30 PM ET) comes only from Topstep's table (1:30 PM CT); the Fed's own source for it was not retrieved (GAP).
- The calendar also records unscheduled and cancelled meetings (E11, E12). The 2020 examples are included in the CSV.

**Topstep news window.**
- Tier 1 events are CPI, NFP, PPI, the FOMC decision and the FOMC press conference (E13). The table gives the CT times: 7:30 AM CT (8:30 ET) for CPI, NFP and PPI; 1:00 PM CT (2:00 ET) for the FOMC decision; 1:30 PM CT (2:30 ET) for the press conference.
- **Minis:** no new openings during the 10-minute window, ±5 minutes (E14).
- **Micros (MES/MNQ):** opening transactions are capped at 1/3/6/9/15 contracts by account size (E15).
- Existing positions may be kept and managed.
- **Pending orders will not fill during the window.** Reducing TP/SL brackets are accepted (E16).
- Announcement is by email and a platform banner (E17).
- The article has no archive of which dates were flagged, and no effective date for the rule. A historical Topstep event list is therefore **not point-in-time reconstructible** (GAP).

**Relevance to the open.**
- The 8:30 ET windows (8:25–8:35 ET) end before 9:30, so they don't overlap an RTH opening range directly. They do change the opening gap and volatility.
- The FOMC windows (1:55–2:05 and 2:25–2:35 ET) fall **inside** an open-to-close ORB holding period. Pending entry orders would not fill then; bracket exits are accepted.
- 10:00 ET releases fall inside a 30–60 minute range-forming window. These include JOLTS (BLS), construction spending and other Census series, and some BEA series. ISM and the University of Michigan surveys are private, so not covered here (GAP).

**CME.** Holiday and trading hours are shown in CT and are subject to change (E18). From 2026–27 the calendars are downloadable (E19). The specific MES/MNQ early-close times (e.g., the Nov 27 and Dec 24, 2026 equity closes) were not captured as text (GAP).

## Representing original vs actual times (`event_calendar_2025_2026.csv`, 121 rows)
**Columns:** `event, agency, reference_period, original_scheduled_date, actual_date, time_et, status, label, original_source, original_snapshot, actual_source, actual_snapshot, retrieval_date`.

**Status values:** `rescheduled`, `cancelled` (actual_date blank), `as_scheduled_confirmed_after_lapse`, `per_current_schedule`, `per_current_schedule_past(not cross-checked to release)`, `held`, `scheduled`, `unscheduled`, `released`.

**Coverage:**
- 72 BLS rows: CPI, PPI and NFP for reference months Dec 2024 – Nov 2026.
- 49 FOMC rows: 2025–26 statements, press conferences and minutes, plus 3 examples from 2020.
- 14 rows are rescheduled or cancelled.

**Gaps, labelled in the rows:**
- Original dates outside the lapse table are not point-in-time verified (106 cells marked GAP).
- The original September 2025 CPI date was not retrieved.
- Press-conference times come from Topstep, not the Fed.
- FOMC statement times are verified for only two meetings in the CSV (2025-09-17 and 2026-09-16).
- Minutes dates are not pre-announced on the calendar.
- No row was cross-checked to the release document's own embargo stamp. The DOL PDF shows that stamp format for claims (E21).

**Ways to obtain true point-in-time originals** (none performed): Wayback Machine captures of BLS and Fed schedule pages; FRASER (St. Louis Fed) archived BLS notices; each release PDF's embargo line; the annual BLS schedule published before the year starts.

## Event-filter OPTIONS (no policy chosen)
| Option | Pros | Cons | Evidence |
|---|---|---|---|
| a. No filter; report results with event-day flags | No selection; complete | Mixes regimes | — |
| b. Exclude all sessions with a Tier 1 event | Simple; matches the Topstep event list | Removes high-vol days, which may be where the edge or the risk lives; regime bias | E13 |
| c. Exclude only the Topstep window (±5 min) | Matches the venue constraint exactly | 8:30 windows don't touch RTH entries; FOMC windows block pending orders mid-session | E14, E16 |
| d. Model the venue constraint: no new fills in the windows, brackets still work, the micro cap applies | Most faithful to Topstep | Needs a point-in-time event list Topstep doesn't archive | E15, E16 |
| e. Stratify: report event / non-event / FOMC-afternoon days separately | Shows dependence | More cells, which are sensitivity splits, not trials (Package 6) | — |
| f. Use original vs actual dates as separate stress arms (e.g., a filter built from original dates during shutdowns) | Tests the look-ahead from calendar revisions | Needs PIT originals, which are partly GAP | E2–E6 |
| g. Expand beyond Tier 1 (claims, GDP, PCE, 10:00 releases) | Captures other movers | Scope creep; more choices to make | E20–E22 |
| h. Exclude CME holiday and early-close sessions | Avoids thin or short days | Needs the early-close table (GAP) | E18 |

Engineering point: the calendar has to be keyed by **actual** release timestamps for a market-impact filter. For a "what a trader knew in advance" filter, it must use the **schedule as known at the decision time**. These differ in shutdown periods: 14 rows in 2025–26.

## Verified facts
- The BLS 8:30 ET times.
- The 2025 lapse dates and the cancelled or rescheduled CPI/NFP/PPI releases.
- The 2026 lapse shifts.
- The FOMC 2:00 PM ET statement time (sampled).
- Unscheduled and cancelled FOMC meetings are recorded on the Fed calendar.
- The Topstep Tier 1 events, times, ±5 minute window, micro caps and pending-order rule.
- The CME calendars are in CT and subject to change.
## Indirect but credible evidence
- Topstep's CT times line up with the official ET release times (7:30 CT = 8:30 ET; 1:00 CT = 2:00 ET).
## Conflicting evidence
- BLS current monthly pages disagree with what was originally scheduled for shutdown months (e.g., Dec 2025 shows the revised dates). This is expected because the pages are revised in place.
## Unknowns
- Point-in-time originals outside the lapse table.
- The press-conference time from a Fed source.
- The effective date of the Topstep rule and its historical flag list.
- MES/MNQ early-close times.
- Private releases (ISM, UMich).
## Engineering assumptions still required
- Event set (Tier 1 vs expanded).
- Whether to key on actual or originally scheduled times.
- Window width.
- Treatment of holidays and early closes.
- Whether to model the Topstep pending-order block.
## What was genuinely new
- The 2026 lapse.
- Cancelled October 2025 releases mean "missing event" rows, not just moved ones.
- Topstep blocks pending fills in the window but accepts brackets.
- FOMC windows fall inside ORB holding periods.
## What it confirmed
- 8:30 releases sit before the open.
- The Package 2 Topstep rule.
- Event filters are sensitivity splits, not trials (Package 6).
## Roadmap changes
- Store the event calendar with original/actual columns and a snapshot per row.
- Capture Wayback or FRASER originals before any event-filter result is promoted.
- Capture the CME early-close table.
## What should not change
- No filter chosen.
- No Databento.
- Topstep rules remain venue constraints, not market facts.
## Next bounded action
- Jason picks the event-filter options to carry as stress arms.
- Optionally approve a bounded Wayback/FRASER retrieval to fill the GAP originals for 2015–2026, using free official archives only.


## Addendum 2026-10-22: Wayback point-in-time originals (unreviewed)
- 47 BLS original dates were filled from pre-release Wayback captures of the BLS schedule pages (E23–E28). The CSV has new columns pit_original_date_wayback, pit_capture_utc, pit_snapshot and pit_check.
- September 2025 CPI was originally scheduled for Oct 15, 2025 (E23) and released Oct 24.
- Wayback agrees with the BLS lapse table for the Sep–Nov 2025 shutdown rows. The 2026-02-13 PPI capture postdates the 2026 revision, so the lapse-table original stands.
- The FOMC 2025–26 meeting dates in the 2025-01-03 capture match the current page (E29).
- Remaining gaps: 2026 CPI originals, minutes originals, the press-conference time, early closes. FRASER was not needed.

---
title: Phase B events addendum (gap-fill to Package 8)
status: unreviewed
promoted: false
date: 2026-10-22
retrieved: 2026-10-22
---
# Phase B events addendum — GDP, PCE, Treasury auctions/refunding, CME outages

Does not modify Package 8 files. Quotes: `economic_events/phaseB_quote_verification.tsv` (10/10 MATCH).
New data files: `phaseB_bea_gdp_pce_calendar.csv` (53 GDP + Personal Income & Outlays rows, Jan 2025–Dec 2027, from BEA iCal), `phaseB_treasury_auctions_2025_2026.csv` (192 note/bond auctions).

## 1. GDP and PCE (BEA)
- Source: BEA Release Schedule iCal, bea.gov/news/schedule/ics/online-calendar-subscription.ics, saved `source_files/phaseB/bea_schedule.ics` [official] **OFFICIAL FACT**. Times in UTC, e.g. "SUMMARY:Personal Income and Outlays\, December 2024" with "DTSTART;VALUE=DATE-TIME:20250131T133000Z" = 8:30 AM ET.
- PCE: "The PCE price index, released each month in the Personal Income and Outlays report" (BEA PCE price index page, saved `bea_pce.txt` L18). Next release listed: October 29, 2026.
- Time: 46 of 53 rows are 12:30Z/13:30Z = 8:30 AM ET (before 9:30 ET open); the rest are 10:00 AM ET: four state/Puerto Rico GDP releases and **three Personal Income & Outlays (PCE) releases at 10:00 AM ET — 2025-04-30 (14:00Z), 2025-12-05 and 2026-01-22 (15:00Z)**, i.e. 30 minutes after the cash open, inside a typical opening-range window. **OFFICIAL FACT** (from iCal rows).
- Revision behaviour: GDP has advance/second/third estimates; "Previously published estimates contain historical data and have since been revised." and BEA keeps a "Vintage History of Quarterly Gross Domestic Product (GDP) and Gross Domestic Income (GDI) Estimates" (bea_gdp_topic.txt L65, L67) — the archive for point-in-time values.
- **Point-in-time warning (inference):** the iCal has **no Oct–Nov 2025 rows** — it reflects the current schedule after shutdown changes, not the originals. Original dates need Wayback/FRASER (same gap as Package 8).

## 2. Treasury auctions and refunding
- TreasuryDirect TA_WS securities/search JSON (treasurydirect.gov, saved `td_auctioned_2025_2026.json`) [official]: 2025-01-01→2026-10-22 gives 791 auctions; notes/bonds close competitive bidding at **1:00 PM ET** in 164 of 192 cases ("competitiveAuctionCloseTime":"01:00 PM"); bills mostly 11:30 AM ET. **OFFICIAL FACT**. 1:00 PM ET falls **inside** an all-day ORB hold (inference).
- Refunding: "Changes in debt management policy are generally informed by and communicated through the quarterly refunding process near the middle of each calendar quarter." (Treasury Quarterly Refunding page, home.treasury.gov, saved `ust_refunding.txt` L329). Exact refunding statement times not extracted (Package 8 note: typically 8:30 AM ET Wednesday — **lead, unverified**).
- Revision: auction results are final, not revised; announcements can move with holidays (inference).

## 3. Major CME exchange interruptions
- Nov 28, 2025: "Stock futures and options trading reopened fully at 8:30 a.m. ET." (CNBC, Chloe Taylor, published 2025-11-28, saved `cnbc_cme_halt_2025.txt` L119) [news/practitioner lead] — halt across Globex after CyrusOne CHI1 cooling failure.
- "The data center shutdown experienced by CME Group in late November has been attributed to human error, according to a report." / "Procedure was not followed when draining cooling towers" (DatacenterDynamics, 2025-12-08, saved `dcd_cme_outage.txt`) [news, citing Bloomberg; **mirror, not independent**].
- Official CME Globex notices history: **blocked** (cmegroup.com anti-scraping). Older outages (e.g. 2014, 2019) not verified — **unknown**. Databento `status` + bar gaps can detect them empirically.

## 4. Options (none chosen)
1. Treat 1:00 PM ET note/bond auction days as stress subset. 2. Exclude Nov 28 2025 (post-outage, holiday half-day). 3. Mask sessions with status halts. 4. Use first-release vs latest GDP values only if a macro filter is ever used (vintage archive).

## Verified facts
- BEA GDP/PCE at 8:30 AM ET (iCal UTC); Treasury note/bond auctions close 1:00 PM ET; refunding mid-quarter; Nov 2025 CME outage reopened 8:30 AM ET.
## Indirect but credible evidence
- DCD/Bloomberg root cause (human error).
## Conflicting evidence
- None.
## Unknowns
- Original (pre-shutdown) BEA dates; CME official outage list; refunding statement times.
## Engineering assumptions still required
- Whether auctions count as events; outage day handling.
## What was genuinely new
- Three PCE releases moved to 10:00 AM ET (inside the opening range); Treasury 1:00 PM ET auctions sit inside an all-day hold; BEA iCal drops cancelled releases.
## What it confirmed
- Morning macro releases precede the 9:30 ET open (Package 8).
## Roadmap changes
- Add auction and outage rows to the event calendar artifact as separate event types.
## What should not change
- Package 8 calendar untouched.
## Next bounded action
- Wayback/FRASER pull of BEA schedule snapshots (free) when Jason approves.

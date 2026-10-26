---
title: MES/MNQ minute & tick data provider comparison (Package 3)
package: 03_providers
status: unreviewed
promoted: false
created: 2026-10-22
retrieved: 2026-10-22
author: Grok Bot (research only; nothing purchased, no accounts created, no API calls)
---

# MES/MNQ data providers (Package 3)

Labels: **[VENDOR]** = the provider's own documented statement · **[QAB-OPTION]** = choice for Jason, not made · **[ESTIMATE]** = my arithmetic, not a published price · **[LEAD]** = unverified.
Snapshots are in `../source_files/providers/`. 35/35 quotes (P1–P35) were string-matched after collapsing whitespace (`quote_verification.tsv`). In the 2024 Databento price PDF the hyphen renders as a private-use glyph (U+E088), and the quote keeps that glyph.
Retrieved 2026-10-22, roughly 10:00–10:20 UTC-5. Prices are as published that day.

## Quick drops
- **Tiingo:** its docs overview and pricing pages (saved) list no futures product, so it is a non-fit. Absence-based, medium confidence.
- **Norgate:** daily data whose "Close price in the data is the official settlement price" (P29). There is no intraday data, so it is a non-fit for minute bars. It may still be useful for settlement-based daily context ($148.50 for 6 months / $270 for 12).
- **Portara/CQG:** the product page returned 404, so nothing could be verified. Lead only; their pricing is usually by quote.
- **Barchart OnDemand:** the getHistory API supports "ticks, minutes, nearbyMinutes…" (P35), but pricing is "Contact Us" (sales-gated). Lead only.
- **St. John's library:** WRDS isn't available. None of the library resources found in the earlier session provide CME intraday futures. Not pursued.

## Comparison table
| Item | **Databento (GLBX.MDP3)** | **FirstRate Data (MES/MNQ)** | **Kibot** | **Massive (ex-Polygon) Futures** | **ProjectX retrieveBars** |
|---|---|---|---|---|---|
| Dated contracts | Yes. Raw symbols plus instrument IDs; parent `MES.FUT`; continuous `MES.c.0`/`.v.0`/`.n.0` (Package 1 Q30–Q33) | Yes, "Individual contracts start with MESZ19" (P16) | Yes, "all individual contract files" (P27) | Yes, the ticker includes the expiry (e.g. ESU5) | Yes, contract ID like `CON.F.US.MNQ.U25` (Package 2) |
| Continuous/adjusted | Continuous is unadjusted only, with no back-adjustment | Unadjusted, absolute-adjusted and ratio-adjusted continuous series (P17) | Unadjusted calendar roll (P26); you apply your own adjustment | Not stated | None |
| How 1-minute bars are built | Vendor-built "from trades" (ohlcv schema). Raw exchange events are also available | Vendor-built; source "direct from major exchanges" | Vendor-built | "Bars are built from the trades in each interval" (P33) | Platform-built; method undocumented |
| Tick / BBO / depth | **Yes:** MBO, MBP-1, MBP-10, TBBO, Trades, BBO-1s/1m (P2) | Tick data sold separately for some tickers (not checked for MES) | Tick and bid/ask "to 2009" for stocks; futures tick not confirmed | Trades and top-of-book quotes on the $79+ tiers | Second-level bars; no ticks documented |
| Timestamps | UTC, nanosecond, hardware-captured (P1, P5). Records carry ts_event (exchange) and ts_recv (capture) | **US Eastern local time** (P19) | **US Eastern** by default, changeable (P24) | Nanosecond Unix; schedules in UTC (P34) | UTC ISO strings |
| Bar timestamp marks | **Bar start** (P3) | Bar start (P19) | Bar open (P25) | window_start, i.e. bar start | Not stated (example `t` looks like bar start) |
| Empty minutes | No record (P3) | No bar (P20) | Not stated | No bar (P33) | Not stated |
| History start for MES/MNQ | GLBX since 2010; MES/MNQ since launch (May 2019); exact first date not shown | Continuous from 5 May 2019; dated contracts from MESZ19 (P16) | "back to inception" (generic) | 2 / 5 / 7+ years depending on tier (P30–P32). **Full 2019 history only on the $199 tier** | Undocumented; expired-contract retention unknown |
| Corrections / versioning | Not captured. Batch jobs can be re-downloaded for 30 days. Whether identical data can be pulled later is unknown | Daily updates; versioning not stated | Not stated | Not stated | Not stated |
| License | Not captured (terms page wouldn't load) → **Unknown** | Derivatives and published research allowed; **raw data can't be redistributed** (P22) | **Internal use only, no redistribution** (P28) | Individual use, non-pro (pricing page) | Topstep/ProjectX terms |
| API limits | 100 concurrent connections; 100 timeseries requests/s; 20 metadata requests/s (P6) | File download | File download/API | Free tier 5 calls/min; paid tiers unlimited | 50 bar requests / 30 s (Package 2) |
| Price | Usage-based per GB of uncompressed DBN (P8), with no monthly fee (P10). 2024-12-11 list: **OHLCV-1m $70/GB, TBBO $28/GB, MBP-1 $1.80/GB** (P11–P13). This list is dated, so confirm with get_cost. **$125 free credit at signup, expiring after 6 months** (P9) | **MES £199.95** per dataset (P15); updates $99.95/yr after 1 free month (P18). MNQ page not captured, presumably similar (lead) | Custom orders from $19; "ES 1-minute full history is $110" (P23). MES/MNQ price not captured | Free / $29 / $79 / $199 per month (P30–P32) | $14.50–$29/mo API (Package 2) |
| Free sample | Free credit covers real data | 2-week samples (P21) | Stock samples only | Free tier, 2 years | Practice account |
| Session/holiday calendar | `status` schema gives session state changes, scheduled and unscheduled (P14), so historical sessions can be reconstructed | None | Trading-hours page (generic) | **Schedules API with holidays, in UTC** (P34); historical depth unknown | None |

## Databento cost check — exact request to price (needs Jason's free signup; not run)
`get_cost` and `list_unit_prices` are free metadata calls (P8 context, "Access to metadata… is free").
```python
import databento as db
c = db.Historical("<key from free signup>")
# A) Full minute history, all dated MES+MNQ contracts (parent symbology includes spreads -> also price outrights only)
c.metadata.get_cost(dataset="GLBX.MDP3", symbols=["MES.FUT","MNQ.FUT"], stype_in="parent",
                    schema="ohlcv-1m", start="2019-05-05", end="2026-10-22")
# B) Same for ES/NQ reference
c.metadata.get_cost(dataset="GLBX.MDP3", symbols=["ES.FUT","NQ.FUT"], stype_in="parent",
                    schema="ohlcv-1m", start="2019-05-05", end="2026-10-22")
# C) Bounded quote sample: 20 RTH sessions, front month only (e.g. MESZ6/MNQZ6, raw_symbol)
c.metadata.get_cost(dataset="GLBX.MDP3", symbols=["MESZ6","MNQZ6"], stype_in="raw_symbol",
                    schema="tbbo", start="2026-09-21T13:30", end="2026-10-19T20:00")   # repeat with schema="mbp-1"
# D) Definitions + status for contract/session metadata
c.metadata.get_cost(dataset="GLBX.MDP3", symbols=["MES.FUT","MNQ.FUT"], stype_in="parent",
                    schema="definition", start="2019-05-05", end="2026-10-22")         # and schema="status"
```
For delivery, request batch `encoding="dbn"` with `compression="zstd"`, or csv. Billing is on uncompressed DBN size either way (P8). Use ranges that are multiples of 10 minutes (P7). Query C spans multiple days and includes overnight; tighten it to per-day RTH windows if needed.
**[ESTIMATE, not a price]:** one OHLCV record is about 56 bytes. MES+MNQ outrights at roughly 1,380 bars/day × ~1,880 sessions × ~2 active contracts each ≈ 10M records ≈ 0.6 GB ≈ $40 at $70/GB. That could fit inside the $125 credit. Spreads in parent symbology and the current rates could change this, so get_cost is the deciding number.

## Recommendation shortlist (tradeoffs; not a purchase)
1. **Databento.** The only source documented here with dated contracts, UTC nanosecond timestamps, bar-start convention, tick/BBO samples for fill research, and a session-status feed, all from one source. It is also likely free at first through the $125 credit. Cons: usage-based billing can surprise, so always run get_cost. The license terms weren't verified. Re-pulling the same data later costs again unless done within the 30-day batch window.
2. **FirstRate Data.** Fixed price (£199.95 for MES), files covering May 2019 onward, dated contracts plus three continuous variants, and a clear license (published research and derived results OK; no raw redistribution, so raw data can't go in Git). Cons: Eastern-time stamps (DST handling needed), no quotes, no session calendar.
3. **Kibot.** The cheapest fixed-price candidate (ES full 1-minute history $110). Cons: internal-use-only license, Eastern time, and MES/MNQ coverage and pricing weren't confirmed.
- **ProjectX bars** are a cross-check for what the venue sees, not the primary dataset (retention unknown). **Massive** needs the $199/mo tier for history back to 2019, so it's poor value for a one-time backfill, though its schedules API is worth noting.

## Verified facts
- Databento GLBX: hardware-captured UTC timestamps, schemas from OHLCV-1m through MBO, bar-start stamping, no empty bars, $125 signup credit for 6 months, per-GB metering on uncompressed DBN, rate limits of 100 timeseries requests/s.
- FirstRate MES: £199.95, from May 2019, dated contracts from MESZ19, Eastern time, bar start, no redistribution of raw data.
- Kibot: Eastern default, bar-open stamps, unadjusted calendar roll, internal use only.
- Massive: $29/$79/$199 tiers with 2/5/7+ years of history.
## Indirect but credible evidence
- The 2024-12-11 Databento unit prices (dated, current rates may differ). Kibot's ES price as a proxy for MES.
## Conflicting evidence
- None direct. Note that a Databento ohlcv-1d bar is a UTC date, not the CME session (P4). Daily bars therefore don't match Norgate settlement closes or CME session dates.
## Unknowns
- Databento license and redistribution terms; current GLBX unit prices; whether corrections are versioned.
- FirstRate MNQ price; Kibot MES/MNQ coverage and price.
- Historical depth of Massive's schedules API.
- ProjectX expired-contract retention.
- Whether any vendor publishes a historical CME holiday archive. Databento's `status` schema is the best candidate, but it's untested.
## Engineering assumptions still required
- [QAB-OPTION] Primary vendor; whether raw data stays out of Git (likely required under every license seen); how to convert Eastern-time vendors to UTC; how to treat empty minutes (all vendors omit no-trade bars).
## What was genuinely new
- Every vendor stamps bars at bar start and omits empty minutes.
- Databento's free credit may cover the full MES/MNQ minute history (estimate only).
- FirstRate provides three continuous variants plus dated contracts.
- No license reviewed allows raw data in a public repo.
## What confirmed an existing decision
- Store dated contracts with UTC timestamps. Daily OHLC can't serve as a cost or fill source; Databento TBBO/MBP-1 samples can.
## What should change in the roadmap
- Add a raw-data storage rule: raw vendor data stays gitignored, and only manifests and checksums are committed.
- Use Databento `definition` and `status` for the contract-calendar artifact if Jason approves signup.
## What should not change
- Package order. Costs (Package 4) should use the bounded TBBO/MBP-1 sample rather than daily estimators.
## Next bounded action
- **Needs Jason:** free Databento signup (his email; there's no student discount, so his main email per his rule). Then run only the four `get_cost` calls above and `list_unit_prices` (free) and report the dollar figures. Nothing is downloaded until he approves a figure.

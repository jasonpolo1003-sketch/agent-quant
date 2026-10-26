---
title: Databento request design for frozen ORB test (MES primary, MNQ comparison)
status: unreviewed
promoted: false
date: 2026-10-22
priced: 2026-10-22 ~21:56–22:00 ET via metadata.get_cost / get_record_count / get_billable_size (free; no data downloaded)
---
# Databento request design — priced, NOT downloaded

Approval scope (Jason, 2026-10-22): metadata.get_cost, get_dataset_range, list_schemas, get_record_count, get_billable_size only. **No timeseries.get_range, no batch jobs, no downloads were made.** Raw results: `providers/databento_get_cost_results.tsv`. API key never printed or written to repo.

## Dataset facts (from metadata, VENDOR METHOD)
- GLBX.MDP3 range: 2010-06-06 → 2026-10-22T18:56Z for ohlcv-1m, trades, mbp-1, tbbo, definition, statistics, status (mbo/cmbp-1 from 2017-05-21).
- Schemas: mbo, mbp-1, mbp-10, tbbo, trades, bbo-1s, bbo-1m, ohlcv-1s/1m/1h/1d, definition, statistics, status, cmbp-1, cbbo-1s, cbbo-1m.
- MES/MNQ listed May 2019 (Package 1), so 2019-05-01 is effectively "max available" for micros.

## Price table (exact get_cost USD; end date exclusive; full 24h Globex sessions)
| ID | Schema | Symbols (stype) | Range | USD | Records | Billable size |
|---|---|---|---|---|---|---|
| C1 | ohlcv-1m | MES.FUT (parent) | 2019-05-01→2026-10-22 | 13.89 | 3,805,005 | 213 MB |
| C2 | ohlcv-1m | MES.FUT+MNQ.FUT (parent) | 2019-05→now | 28.55 | 7,821,461 | 438 MB |
| C3 | ohlcv-1m | MES.FUT | 2022-01→now | 9.49 | 2,598,089 | 145 MB |
| C4 | ohlcv-1m | MES.FUT+MNQ.FUT | 2022-01→now | 19.67 | 5,387,966 | 302 MB |
| C5 | ohlcv-1m | MES.FUT | 2024-01→now | 5.61 | 1,535,578 | 86 MB |
| C14 | ohlcv-1m | MES.v.0 (continuous, volume-ranked front) | 2019-05→now | 9.61 | 2,631,041 | 147 MB |
| C15 | ohlcv-1m | MES.v.0+MNQ.v.0 | 2019-05→now | 19.22 | 5,263,662 | 295 MB |
| C16 | ohlcv-1m | MES.v.0+MES.v.1 (front+next) | 2019-05→now | 13.28 | 3,638,333 | 204 MB |
| C6 | definition | MES.FUT+MNQ.FUT | 2019-05→now | 0.10 | 124,454 | 65 MB |
| C7 | ohlcv-1d | MES.FUT+MNQ.FUT | 2019-05→now | 0.20 | 20,365 | 1 MB |
| C8 | statistics (settle, OI) | MES.FUT+MNQ.FUT | 2019-05→now | 0.64 | 8,569,886 | 686 MB |
| C9 | trades | MES.FUT | 2026-06-29→09-23 (~60 sessions) | 26.73 | 21,354,686 | 1.03 GB |
| C17 | trades | MES.v.0 | same ~60 sessions | 25.80 | 20,609,679 | 0.99 GB |
| C10 | tbbo | MES.FUT | same | 44.55 | 21,354,686 | 1.71 GB |
| C18 | tbbo | MES.v.0 | same | 43.00 | 20,609,679 | 1.65 GB |
| C11 | mbp-1 | MES.FUT | same | 79.10 | 589,832,618 | 47.2 GB |
| C19 | mbp-1 | MES.v.0 | same | 71.21 | 530,982,272 | 42.5 GB |
| C20 | trades | MNQ.v.0 | same | 97.13 | 77,599,208 | 3.72 GB |
| C12 | trades | MES.FUT+MNQ.FUT | same | 127.47 | 101,839,723 | 4.89 GB |
| C13 | ohlcv-1m | ES.FUT+NQ.FUT (reference) | 2010-06→now | 58.75 | 16,092,444 | 901 MB |
Credit: $125. Notes: parent (.FUT) includes calendar spreads and back months (why C1 > C14); prices are list-price estimates from get_cost and may differ slightly at download; "now" ends 2026-10-22 (partial day). get_cost is for the full 24h; there is no RTH-only filter, so RTH cuts do not reduce cost.

## Candidate smallest requests (options, none chosen)
- **R-A (minimum MES):** C14 + C6 = **$9.71**. Volume-ranked front only; roll fixed by Databento's rule; cannot test alternative roll policies.
- **R-B (MES raw contracts):** C1 + C6 = **$13.99**. All dated contracts (+spreads to filter); supports any roll policy and the contract calendar.
- **R-C (MES then MNQ, raw):** C2 + C6 + C7 + C8 = **$29.50**. Adds MNQ comparison, daily volume and OI for measuring roll migration.
- **R-D (front+next MES):** C16 + C6 = **$13.38**. Compromise for roll testing.
- **Optional ambiguity sample:** C17 MES trades ~60 sessions **$25.80**; tbbo C18 **$43.00** adds bid/ask at each trade. MNQ trades are ~3.8× pricier (C20 $97.13). mbp-1 not needed for ORB on 1m.
- Example fit inside $125: R-C ($29.50) + C17 ($25.80) = $55.30, leaving ~$69.70. (Illustration only, not a recommendation.)

## Fields (ohlcv-1m, VENDOR METHOD, Package 3)
ts_event (UTC ns, bar open), rtype, publisher_id, instrument_id, open, high, low, close (fixed-point 1e-9), volume. definition adds raw_symbol, expiration, instrument_class (future vs spread), min_price_increment, etc. Use `map_symbols` / symbology json to join instrument_id→raw_symbol per date.

## Licensing / storage
- Databento pricing FAQ (lead via search; page JS-rendered, not snapshotted): "Most of our datasets can be redistributed internally or externally after 24 hours", subject to the publisher's pass-through rules. CME licensing FAQ (lead via search; cmegroup.com blocked): non-display use of historical information "must be licensed, but is not reportable and carries no fees at this time." **Practitioner lead — not verified snapshots.**
- QAB policy (existing): raw vendor files gitignored; store manifests + sha256 only. Sizes above are billable (uncompressed DBN); zstd files are typically much smaller (inference).

## Verified facts
- Exact get_cost prices/records/sizes above (metadata API responses, saved TSV).
## Indirect but credible evidence
- Licensing statements (search-result leads).
## Conflicting evidence
- None.
## Unknowns
- Final billed amount at download; whether v.0 roll matches CME roll date; licensing text verbatim.
## Engineering assumptions still required
- Parent vs continuous; date range; whether MNQ is pulled now or after MES result.
## What was genuinely new
- Full MES+MNQ 1m history since launch costs ~$28.55; micros trades sample is the expensive part.
## What it confirmed
- 1m bars are a small fraction of the $125 credit.
## Roadmap changes
- None to PLAN.md; Drew can design the loader against the R-B/R-C layout.
## What should not change
- No download until Jason chooses a request.
## Next bounded action
- Jason picks R-A/R-B/R-C/R-D (+/− trades sample); then a single timeseries/batch pull with a cost cap.

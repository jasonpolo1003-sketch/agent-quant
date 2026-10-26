# brain/sources/mes_mnq/_INDEX.md

| # | Package | Status | Review | Files | Sources | Proposed plan change |
|---|---|---|---|---|---|---|
| 1 | contracts/ (contract, session, rollover facts) | complete 2026-10-22 (addendum: MNQ settlement, Juneteenth) | unreviewed | contracts/contracts_sessions_rollover.md, contracts/quote_verification.tsv, source_files/* (20 files), _sha256.txt | 10 (S1–S10); 37/37 quotes verified | Add versioned contract-calendar artifact as Tier-1 dependency; historical holiday archive needed |
| 2 | venue_rules/ (Topstep/ProjectX rules & API) | complete 2026-10-22 | unreviewed | venue_rules/topstep_projectx_rules.md, venue_rules/quote_verification.tsv, source_files/venue/* (31 pages ×2), source_files/cme_wiki_nq_mnq_settlement.*, cme_juneteenth_2026_settlement.*, cme_final_settlement_soq.* | 31 official pages (22 Topstep help, 9 ProjectX docs) + 3 CME; 66/66 quotes verified | Live = no API (manual only); flatten 3:08–3:10 PM CT and Tier-1 windows go into calendar artifact; add ProjectX bar-history probe to Package 3 |
| 3 | providers/ (data-provider comparison) | complete 2026-10-22 | unreviewed | providers/data_providers_comparison.md, providers/quote_verification.tsv, source_files/providers/* | 14 provider sources (Databento 9 pages+price PDF, FirstRate 4, Kibot 6, Norgate, Massive 3, Barchart, Tiingo 2, Portara 404); 35/35 quotes verified | Raw vendor data gitignored (manifests+checksums only); Databento free signup + get_cost is next; use definition/status for calendar |
| 4 | execution_costs/ (fees, spread, fast-market, fill evidence) | complete 2026-10-22 | unreviewed | execution_costs/execution_costs_mes_mnq.md, execution_costs/quote_verification.tsv, source_files/costs/* | 10 new sources (CME 6, IBKR 2, 2 academic) + Package 2/3 reuse; 23/23 quotes verified | Add no-fill/paused-market scenario to Package 7; quote sample or CME Liquidity Tool read before freezing costs; separate MES/MNQ tick calibration |
| 5 | orb_evidence/ (ORB evidence) | complete 2026-10-22 | unreviewed | orb_evidence/orb_evidence.md, orb_evidence/search_log.md, orb_evidence/fetna_2026_addendum.md, orb_evidence/fetna_repo_check.md, orb_evidence/fetna_esnq_derived_micro.json, orb_evidence/quote_verification.tsv, source_files/orb/* (14 files) | 5 direct, 1 close proxy, 7 distant; 41/41 quotes verified; Fetna retrieved; repo checked (AGPL; summaries only, no long/short) | ORB = falsification target; add power/MDE + random-anchor controls to Package 6; report micro costs in full-size-equivalent terms |
| 6 | validation/ | complete, unreviewed (2026-10-22) | validation_methods.md, quote_verification.tsv (15/15), rx0001_effective_n_derived.json | 13 primary sources retrieved; Romano-Wolf + AFML ch7/12 text not retrieved | trial-family table; RX-0001 N_eff proxy 10-24; SC-0002 86=records (3 rules) ; +rx0001_rerun/ (N_eff 2-22, mostly 8-13; DSR 0.93-0.96; PBO 0.70; verdict unchanged) | unreviewed |
| 7 | fill_models/ | complete, unreviewed (2026-10-22) | fill_models.md, quote_verification.tsv (27/27) | CME order types/Velocity/price limits, Topstep hours (reused); TradingView, NinjaTrader, QuantConnect, backtrader docs (new); MultiCharts 403 | 6-condition options tables, no policy; tick-sample test design unpriced | unreviewed |
| 8 | economic_events/ | done (unreviewed) | economic_events.md, event_calendar_2025_2026.csv | E1–E22 verified | BLS/Fed/CME/BEA/Census/DOL/Topstep | PIT originals outside lapse table = GAP |
| 9 | synthesis/ | done (unreviewed) 2026-10-22; D-COST-01 decided | synthesis/synthesis.md, synthesis/decisions_log.md | Packages 1–8 only; no new research | — | P1–P8 proposed (PLAN.md not edited) |
| 9a | scraper retry 2026-10-22 | done (unreviewed) | synthesis/scraper_retry_2026-10-22.md + addenda in fill_models, execution_costs, validation, economic_events | 23 new quotes verified (B28–B35, C24–C27, V16–V18, E23–E29) | Wayback (MultiCharts, BLS, Fed), static NinjaTrader, UZH Romano-Wolf, CME wiki, CFTC/FIA | Research Scout fetch lane failed; MES/MNQ VL/band values still missing |
| 10 | manual_fetch_list.md | created (unreviewed) 2026-10-22 | manual_fetch_list.md | 13 rows (M1–M13) for blocked, login-only or paywalled items | save PDFs to C:\Users\jason\OneDrive\Desktop\Quant\manual_sources\ | no blocks circumvented |
| 11 | D-ROLL-01 roll calendar + Drew handoff | done (unreviewed) 2026-10-23 | contracts/roll_calendar_2019_2026.csv, contracts/roll_volume_check.csv, contracts/build_roll_calendar.py, synthesis/decisions_log.md (D-ROLL-01), synthesis/drew_orb_build_handoff.md | local R-C data only, no API calls | 68 roll rows; prior-day volume agreement 0/60 (volume roll 2-4 trading days later) | none (PLAN.md not edited) |


Main note sha256:
```
d962fe4183bba073980d68406cbcc4f04004a3d36318f084c63058321238e503  contracts/contracts_sessions_rollover.md
25bd76658621cbab251ddf3e029ccae6bff1ce244ab0c9803782db31ebd02421  venue_rules/topstep_projectx_rules.md
5739a1e7cf417c1415e407ae5d63d232063ff74137e048399ad820678ea0130c  providers/data_providers_comparison.md
60311a7c45374245c59cc73392640d972df73bed043f07a3baa937badf91daab  execution_costs/execution_costs_mes_mnq.md
```
All source checksums: _sha256.txt
bd5617344629a4b1a6cf841f9d5e6bf9406aff0d309a01b6c4f66a74598941a0  orb_evidence/fetna_2026_addendum.md
4602292c0c4af756ac4f6cfffc0ba53432a16973547fd8c471bf36eb0c05ba86  orb_evidence/orb_evidence.md
ec752c088b7b033a0d513b1492ba86a179f25779753070987ed83cbbe74cd13a  orb_evidence/search_log.md
aadd79980bff0c27a23386114cab49dfe5b40350a355affbba5ecd4bba265deb  orb_evidence/quote_verification.tsv
fda9c3032623eb7605f55a946738d7897a8a14286782bd7fb7fda1ef90727a9e  orb_evidence/fetna_repo_check.md
db64bd129c4e7e35e3c4fbe552e933a76dd5794b103414d3d6f43fecc23919e9  orb_evidence/fetna_esnq_derived_micro.json
| B1 | contracts/phaseB_calendar_addendum.md (DST, settlement history, holidays, roll migration, symbol mapping) | complete 2026-10-22 | unreviewed | + phaseB_quote_verification.tsv (11/11) | CME (saved), Databento symbology, ProjectX | Calendar stores instrument_id per date; spread filter |
| B2 | fill_models/phaseB_fill_addendum.md (latency, 1m limits, quotes/trades need) | complete 2026-10-22 | unreviewed | + phaseB_quote_verification.tsv (4/4) | Databento OHLCV/status docs | status-based halt mask option |
| B3 | economic_events/phaseB_events_addendum.md (GDP, PCE, Treasury, CME outages) | complete 2026-10-22 | unreviewed | + phaseB_quote_verification.tsv (10/10), phaseB_bea_gdp_pce_calendar.csv (53), phaseB_treasury_auctions_2025_2026.csv (192) | BEA iCal, TreasuryDirect, Treasury, CNBC, DCD | BEA/Treasury/outage event types |
| B4 | providers/databento_request_design.md (priced via get_cost; no download) | complete 2026-10-22 | unreviewed | + databento_get_cost_results.tsv (20 requests) | Databento metadata API | none |
| B5 | synthesis/phaseB_summary.md (exec summary, unknowns, Drew handoff) | complete 2026-10-22 | unreviewed | — | Phase B addenda | none applied |
| B6 | providers/databento_rc_download_manifest.md (R-C download: ohlcv-1m, definition, ohlcv-1d, statistics MES+MNQ) | downloaded 2026-10-22; definition re-pulled 2026-10-23 in 29 chunks, 124,454/124,454 (old file kept as .truncated) | unreviewed | raw data outside Git: box /workspace/data/databento/rc_2026-10-22 + JPolo Desktop\Quant\data\databento\rc_2026-10-22 (SHA verified) | Databento GLBX.MDP3 | none |
| B7 | validation/rc_data_quality/rc_data_quality.md (local R-C data-quality scan; no API calls) | complete 2026-10-23 | unreviewed | + scan_rc_quality.py, flag_*.csv, front_by_volume.csv, front_coverage_by_day.csv, definitions_outrights.csv, checkpoint.json | Databento R-C local files | none (verdict: clean enough for ORB test) |

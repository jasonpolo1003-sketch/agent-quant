
## Databento (market data)
- Created: 2026-10-22 by quantam
- URL: https://databento.com/login
- Email/login: jasonpolo1003@gmail.com
- Password: (removed 2026-10-27; never store passwords in the repo)
- User ID: LFTQGLMY
- Status: active (email verified, card added for identity check only, no charges). API key in portal at https://databento.com/portal/keys (also on bot computer, not in repo).
- Rule: NO data downloads without Jason approval; only free cost checks.
- 2026-10-22 ~21:56–22:00 ET: metadata only (get_dataset_range, list_schemas, get_cost, get_record_count, get_billable_size) for 20 candidate requests. No downloads. Results in brain/sources/mes_mnq/providers/databento_get_cost_results.tsv.
- 2026-10-22 22:09–22:36 ET: R-C DOWNLOAD approved by Jason. get_cost re-check identical ($29.4972). Pulled ohlcv-1m, definition, ohlcv-1d, statistics for MES.FUT+MNQ.FUT parent, 2019-05-01→2026-10-22 (excl). Files in /workspace/data/databento/rc_2026-10-22. definition file appears truncated (119,188 of 124,454 records). Nothing else downloaded.

## 2026-10-23 definition re-pull complete
- 29 chunked timeseries.get_range calls (definition, GLBX.MDP3, MES.FUT,MNQ.FUT) plus retries of truncated streams; no other schemas/datasets requested.
- Sum 124,454 = expected 124,454. Canonical: rc_2026-10-22/def_years/. Old file renamed .truncated.
- Cost: est ≈ $0.10 (get_cost); retries may have billed separately — confirm in portal.
- Copied all R-C data + def_years to JPolo; 33/33 SHA256 verified.

## 2026-10-27 multi-market daily bars (approved by Jason, free credits)
- Re-quoted $39.44 just before downloading. ohlcv-1d, GLBX.MDP3, parent symbols for 29 markets (ES NQ RTY YM ZT ZF ZN ZB 6E 6J 6B 6A 6C 6S GC SI HG CL NG RB HO ZC ZW ZS ZL ZM LE HE), 2010-06-06 to 2025-01-01 (exclusive). Paid from the $125 new-account credit; Jason expected no card charge.
- Files: `Quant/data/databento/daily_2010-06-06_2024-12-31/` (7 group files, manifest.json, SHA256SUMS). Record counts match get_record_count exactly, and the last bar is 2024-12-31. Script: `scripts/fetch_databento_daily.py`.
- Not bought: contract definitions ($71.10; not needed, since rolls use volume from the daily bars) and 2025-26 exam-period data (~$18; buy only when a strategy needs an exam).


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

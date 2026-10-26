---
title: Databento R-C download manifest (MES+MNQ, GLBX.MDP3)
status: unreviewed
promoted: false
date: 2026-10-22
updated: 2026-10-23
---
# Databento R-C download manifest

Approved by Jason 2026-10-22 (R-C, $29.50). Downloaded 2026-10-22 22:09–22:36 ET via timeseries.get_range (HTTP streaming), encoding=dbn, compression=zstd, stype_in=parent, stype_out=instrument_id, symbols=MES.FUT,MNQ.FUT, start=2019-05-01, end=2026-10-22 (exclusive, i.e. through 2026-10-21 = last full day; same as priced). Nothing else downloaded.

## Pre-download get_cost re-check (identical to pricing)
| Schema | Priced USD | Re-check USD |
|---|---|---|
| ohlcv-1m | 28.554468527436 | 28.554468527436 |
| definition | 0.102461628616 | 0.102461628616 |
| ohlcv-1d | 0.201802328229 | 0.201802328229 |
| statistics | 0.638506263494 | 0.638506263494 |
| **Total** | **29.497238747775** | **29.497238747775** |
Actual billed amount: not exposed by the free metadata API; check the Databento portal billing page (not accessed).

## Files (raw data OUTSIDE Git)
Box: `/workspace/data/databento/rc_2026-10-22/`. JPolo target: `C:\Users\jason\OneDrive\Desktop\Quant\data\databento\rc_2026-10-22\` (sibling of the repo, not inside it). **Copied to JPolo 2026-10-23** (parts rejoined; all 33 files in SHA256SUMS verified on JPolo).
| File | Bytes | Records (file) | Records (get_record_count) | sha256 |
|---|---|---|---|---|
| glbx-mdp3_definition_MES-MNQ-FUT_20190501-20261022.dbn.zst.truncated (NOT canonical) | 522269 | 119188 | 124454 | f2d97c97fa5f19c57cbf23b6fd89e0f484127ee6b5a8952473c1bdf4d9a93666 |
| glbx-mdp3_ohlcv-1d_MES-MNQ-FUT_20190501-20261022.dbn.zst | 560401 | 20365 | 20365 | 027c3a3a05caae629d7281643f005e0a0fd4f7249a0c07ca3228ca4b64d2a44a |
| glbx-mdp3_ohlcv-1m_MES-MNQ-FUT_20190501-20261022.dbn.zst | 130158938 | 7821461 | 7821461 | 28d7a629a24c19053f0629945aba7feffd534d2c9f6041e045a1ed5c69655e74 |
| glbx-mdp3_statistics_MES-MNQ-FUT_20190501-20261022.dbn.zst | 199487729 | 8569886 | 8569886 | 1c04f3c54e79e5052a128b06a42f64c23bca3b2f502d13d239ca3d4de0872eb4 |

## Integrity checks (basic only; no backtest)
- ohlcv-1m: 7,821,461 records = expected. 2019-05-05 22:00Z → 2026-10-21 23:59Z. 35 MES and 34 MNQ outright contracts (M9 → Z7 for MES, M9 → Z6 for MNQ; parent also includes calendar spreads, 212 symbols total). 2,327 trade dates each. Weekdays with no bars (7, both roots): 2020-04-10, 2020-12-25, 2021-01-01, 2021-12-24, 2022-04-15, 2024-03-29, 2025-04-18 — all Good Friday / Christmas / New Year exchange closures (inference; consistent with CME holiday conventions). No trade date with <100 bars.
- ohlcv-1d: 20,365 = expected; 2019-05-05 → 2026-10-21; same contract list.
- statistics: 8,569,886 = expected; 2019-05-03 → 2026-10-21.
- definition (original single file, superseded) — — 119,188 records vs 124,454 expected (−5,266, −4.2%); last ts 2026-06-25. Download stream took ~20 min for 522 KB and appears truncated. Not re-requested (re-download might bill again; needs Jason's OK). Contract calendar should not rely on this file until re-pulled; raw_symbol/expiry for later contracts are recoverable from ohlcv symbology mapping meanwhile.
- Full output: \`/workspace/data/databento/rc_2026-10-22/integrity.txt\`.

## Definition re-pull (canonical), approved by Jason
Same request params (GLBX.MDP3, definition, MES.FUT,MNQ.FUT, parent→instrument_id) split into 29 ranges: 2019-05-01→2020-01-01 then quarterly to 2026-10-22 (excl). Each chunk retried until its record count equalled the expected count for that range (several streams truncated mid-transfer and were re-requested; see def_download.log). **Sum = 124,454 = expected 124,454.** Canonical set: `def_years/def_*.dbn.zst` (checksums in SHA256SUMS). Cost: get_cost for the whole range ≈ $0.10, but truncated/retried streams may each have billed; actual amount cannot be confirmed without the Databento portal (not accessed).
| File | Records | sha256 |
|---|---|---|
| def_2019.dbn.zst | 11516 | 5bf4523a074d88937a81dcd66f22887b8804d489712a7c0e0855c04a8ea548f1 |
| def_202001.dbn.zst | 4220 | d8922482600991655e61e67cfe369dcb27f2706189efe9814dad58e12f97704b |
| def_202004.dbn.zst | 4164 | f5dabac860568d97be0fdabde54eeb26e77c89882dd87cc6ed023cf762df7a3d |
| def_202007.dbn.zst | 4166 | 486d284e8210542c6028ce1242a867487bee04ad84cfb0a1f5332622b35c329a |
| def_202010.dbn.zst | 4166 | 74f87b0ef34955bb1af5aca74b1de88c2a99812a5e702b4fde9bf46308c44e8a |
| def_202101.dbn.zst | 4066 | 57803248b157f70e026271497513a6b23c1b1d1831be5447550afbb835b0c10d |
| def_202104.dbn.zst | 4116 | 25ea34c777f0fe1ccbafd80acbe7161ec041d5880a948b6065a262ca319793c0 |
| def_202107.dbn.zst | 4166 | e07f6311dcf6c22220b546a4b0adb25ac80a9a99dbb64bf1b4c471dd9ee1a154 |
| def_202110.dbn.zst | 4166 | 0b0ca80b9f84bdffe80c66b616fd889aea3d07163c6c7b303bfe03094c15d182 |
| def_202201.dbn.zst | 4066 | 95cb6f52f7fd44dd66007637caabd0944017fd85f2f908ae940ea20315417d45 |
| def_202204.dbn.zst | 4116 | cf70dc9c287e309bc419cd23a1c07f4be2f8bab5b0c5566f823357bc3889ecde |
| def_202207.dbn.zst | 4166 | 0f980e656dc15f614676b8f9d90e738701663f2380a0315ce6e17800e83f0619 |
| def_202210.dbn.zst | 4116 | 1ce305b08123f91d13b996f9693cc6811806fad8ef24c40e5712ae55fa5704a0 |
| def_202301.dbn.zst | 4116 | 884dfaba45a47daea9d8ebb72b795751008d8d31915d17440317f918c744a90f |
| def_202304.dbn.zst | 4116 | b2bedc5a6ecb9ed9817743a6ca30d01f9419e83b6d328d50c735ba122a36f037 |
| def_202307.dbn.zst | 4116 | d224278fa194be82487da752ca9795dfaca56986c54cbb35c44e79c2548d484f |
| def_202310.dbn.zst | 4166 | 7e601fec380adef91a4c390cb07da987b854ee5908ac77b6236d8e21ac88f1d2 |
| def_202401.dbn.zst | 4116 | 4984f43245cdeb3163cbf775d5f06597320a03256025aa614c367f060bc22156 |
| def_202404.dbn.zst | 4116 | f24f9559959dfec0d2852f9d304f117a7d3a3ad21c24de5478aa0ad0f8ad47c6 |
| def_202407.dbn.zst | 4266 | 0642450c985d3e79121fac50d8063ade83e7c3e82ba434a8b06d044b4071d94c |
| def_202410.dbn.zst | 4166 | cec63493b324dca9ee80b15c40ed2a114c85d275bb7209fc8d9251207c53aeac |
| def_202501.dbn.zst | 4066 | bc29c5575fdb3169d806aec3000b8996cc91954f91d24cfb0e9679f2a37f8e01 |
| def_202504.dbn.zst | 4184 | a82d3ead4d318df4446100acbf28aafa674215f46ad4d6bbc81a3aded9b2cadb |
| def_202507.dbn.zst | 4166 | 18281d83b34b55f19f9a6e0f971f16d1584e89b866071e9410c4367b1305605c |
| def_202510.dbn.zst | 4316 | 9ebe476d443cc57c8b5ec1cfced63a7828a3b7412742c841dff9204ca0d5df38 |
| def_202601.dbn.zst | 4066 | 11bef0e0acb9c8a3a085311e01508addb9e99d9122746c099f19ae308759362d |
| def_202604.dbn.zst | 4202 | 1df587fc73c576009eb60ff857f289c4caeb2252420dbcd0db408a2d35a98ef1 |
| def_202607.dbn.zst | 4166 | d9f1f373cc3eae739ea9af57abc15dcdedca1381ec8bf331f9c60de8827fbb29 |
| def_202610.dbn.zst | 900 | 5347784a8d85c7315fd507b9f25846d34a621cf6c2bb0142ee30095fad7b1421 |

## License note
CME Globex data via Databento: internal research use; no redistribution of raw data. Databento states redistribution rights pass through the publisher's terms (pricing FAQ, lead) and CME historical non-display use "must be licensed, but is not reportable and carries no fees at this time" (CME licensing FAQ, lead; cmegroup.com blocked to scripts). QAB policy: raw files never in repo; only this manifest + checksums.

## Verified facts
- Record counts and sha256 above; get_cost unchanged.
## Indirect but credible evidence
- Missing weekdays match exchange holidays.
## Conflicting evidence
- Original definition file short (superseded by re-pull, now resolved).
## Unknowns
- Actual billed amount; cause of stream truncations; exact re-pull cost.
## Engineering assumptions still required
- Spread filtering; roll policy.
## What was genuinely new
- Full micro history on disk.
## What it confirmed
- Prices from the design note.
## Roadmap changes
- None.
## What should not change
- No backtests or strategy code run.
## Next bounded action
- Jason: check portal billing for the definition re-pull; decide roll policy before building a contract calendar from def_years.

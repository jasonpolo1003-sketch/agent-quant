# SC-FUT-0013 month-end results (2026-10-29): both trials FAILED on MES

Spec: `brain/_system/futures/sc-fut-0013-spec.v1.json` (frozen, sha256 cbba76d5..., commit 06dab19; unchanged). Addendum 1 (`sc-fut-0013-addendum-1.md`) was written before any result. Code: `src/quant_brain/workbench/month_end.py` (family `month_end`), fixtures `tests/test_month_end_fixtures.py` (18 tests), run `scripts/month_end_report.py`. Results JSON: `brain/04_Backtest_Reports/workbench/results/sc-fut-0013-month-end.json` plus one file per run. Practice 2019-05-01..2024-12-31, volume roll, 1,428 NYSE sessions. No exam data was touched.

## Verdicts (L3: MES $6.22, MNQ $3.22 per round trip; spec bar p < 0.0253)

| Trial | Market | Trade days | $/trade | $/session | Control $/trade | vs control | p | $1/session | $5/trade | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| T1 rebalance (L-2, L-1, L against MES-ZN MTD) | **MES** | 201 | +5.95 | +0.84 | -6.42 | +12.37 | 0.183 | fail | pass | **FAIL** |
| T2 turn of month (long L, F1-F3) | **MES** | 269 | +2.85 | +0.54 | -6.06 | +8.91 | 0.169 | fail | fail | **FAIL** |
| T1 rebalance | MNQ (diag) | 201 | +28.70 | +4.04 | -0.88 | +29.58 | 0.106 | pass | pass | not gated (would fail on p) |
| T2 turn of month | MNQ (diag) | 269 | +12.20 | +2.30 | -3.43 | +15.62 | 0.177 | pass | pass | not gated (would fail on p) |

- **Neither MES trial beats its matched control** (p 0.18 and 0.17 against 0.0253) and both miss the $1.00/session floor. T2 also misses the $5/trade floor. Failures are recorded as is, with no retuning (spec `no_retuning`).
- Sharpe of daily L3 net over all sessions (not gated): MES T1 0.19, T2 0.11; MNQ T1 0.52, T2 0.26.
- Hit rate: MES T1 50.2%, T2 55.8%; MNQ T1 51.2%, T2 56.9%.
- Both bars appear in the records. The workbench honesty counter multiplies FAMILY_SPLIT (2) by the trials logged, so it printed 0.0253 / 0.0127 / 0.0085 / 0.0064 in run order. The spec bar of 0.0253 for each trial governs (addendum item 8). Every p is far above both bars, so the choice of bar changes nothing.
- Trade days: T1 = 67 months x 3 (May 2019 has no signal because its start close, 30 April 2019, is before the data). T2 = 68 months x 4 = 272 positions, of which 3 are non-evaluable: 1-3 May 2019, because the dev file has no bars before 2019-05-05. Those 3 count $0 in the floor's numerator and stay in its 1,428-session denominator. No other trade day had a missing 08:30 or exit bar.

## Costs L1-L4 (MES)

| | L1 | L2 | L3 | L4 |
|---|---|---|---|---|
| T1 $/trade | 9.70 | 8.45 | 5.95 | 0.95 |
| T1 $/session | 1.37 | 1.19 | 0.84 | 0.13 |
| T2 $/trade | 6.60 | 5.35 | 2.85 | -2.15 |
| T2 $/session | 1.24 | 1.01 | 0.54 | -0.41 |

On MES, T1 clears the per-session floor only at L1 and L2, and it never beats luck. MNQ is nearly cost-insensitive: T1 runs from $30.20 to $26.70 per trade from L1 to L4.

## Per year (L3 net; $/session uses that year's sessions)

| Year | MES T1 n / net / $/trade | MES T2 n / net / $/trade | MNQ T1 net / $/trade | MNQ T2 net / $/trade |
|---|---|---|---|---|
| 2019 (May-Dec) | 21 / +292 / +13.90 | 29 / -840 / -28.98 | +565 / +26.92 | -1,038 / -35.79 |
| 2020 | 36 / -219 / -6.08 | 48 / +1,721 / +35.86 | +23 / +0.63 | +2,835 / +59.06 |
| 2021 | 36 / -181 / -5.04 | 48 / -1,265 / -26.35 | -797 / -22.14 | -2,458 / -51.20 |
| 2022 | 36 / +1,000 / +27.77 | 48 / +434 / +9.04 | +2,397 / +66.57 | +578 / +12.05 |
| 2023 | 36 / +412 / +11.45 | 48 / +1,218 / +25.37 | +1,689 / +46.92 | +2,689 / +56.03 |
| 2024 | 36 / -108 / -2.99 | 48 / -502 / -10.46 | +1,893 / +52.57 | +673 / +14.03 |

MES T1 is positive in 3 of 6 years and MES T2 in 3 of 6. Neither is stable from year to year. MNQ T1 is positive in 5 of 6 years, but 2022-2024 carry it.

## Diagnostics (spec, not gated)

- **T1 hit rate by sign of rel** (signal months: 46 with rel > 0, 21 with rel < 0, 1 missing):
  - MES: rel > 0 (short) 138 days, 49.3% hit, +$6.28 gross/trade; rel < 0 (long) 63 days, 52.4% hit, +$25.08 gross/trade.
  - MNQ: short 50.7%, +$17.09; long 52.4%, +$64.41.
  - The short leg, which carries the paper's "stocks overweight -> sell" story and two thirds of the trades, is a coin flip on MES. Most of what T1 earned came from the long leg, which on 2019-2024 overlaps the market's upward drift.
- **T2 vs always-long on every other session** (same 08:30 -> 15:00 window, L3):
  - MES: T2 +$2.85/trade vs other sessions -$3.99/session (1,156 sessions). Difference +$6.84, Welch t 0.55.
  - MNQ: +$12.20 vs +$0.35. Difference +$11.84, t 0.55.
  - The turn of the month is better than an ordinary RTH day by a few dollars, but nowhere near significant. The published TOM premium is largely overnight, which this RTH-only rule does not hold (as the edge scout warned).
- **MNQ on the same rules:** larger dollars, because MNQ has about 2.5 times MES's per-trade dollar volatility (gross sd $328 vs $189 per trade), but still p 0.11 and 0.18.

## Power and in-sample caveats

- **Power is low.** The per-trade difference from the control has an sd of about $188 on MES. With 201 or 269 trade days, the standard error is $13.3 (T1) and $11.2 (T2). A one-sided test at 0.0253 has 80% power only for a true edge of about **$37/trade (T1) or $31/trade (T2) over the control**. The observed edges, $12.4 and $8.9, are a third of that. A real but small effect of this size could not have passed. Equally, these numbers give no evidence that one exists. On MNQ the detectable edge is about $64 (T1) and $55 (T2).
- **Practice is in-sample for the papers.** Harvey, Mazzoleni & Melone's sample runs to March 2023, and the TOM literature covers 2019-2024 in its updates, so this was a replication, not an out-of-sample test. Failing a replication on our intraday, RTH-only, 1-contract version does not refute the papers: their effects are measured close to close or over the next day, and much of TOM sits overnight.
- T2 also earns market beta. MES always-long on other RTH sessions lost $3.99/session at L3 (the 2019-2024 equity gains were mostly overnight), so beta does not explain T2 here.
- Only the MNQ T1 numbers look interesting ($28.70/trade, $4.04/session, 5 of 6 years positive). That is a diagnostic market, picked out after the fact, at p 0.106 with no multiple-testing allowance. It is a hypothesis at most. It would need a new frozen card and fresh (exam or forward) data, with Jason's OK. It is not a basis for an exam check under this card, because the card gates on MES.

## Spec advance rule

Neither MES trial passed, so neither is a candidate for exam check #2. Exam checks used remain 1 of 3.

## Engineering notes

- Existing families are unchanged. The edits to shared files are additive only: a registry, GRADING and DESCRIPTIONS entry; `FAMILY_SPLIT["month_end"] = 2`; `month_end.py` appended to `engine.CODE_FILES`; and a loader branch plus a `spec_verdict` hook in `scripts/workbench.py`. **Byte-identical check:** HEAD (06dab19) and the working tree each simulated all 8 earlier families (orb, late_momentum, shock_reversal, noise_area, noise_area_pyramid, fade_band, gap_fill, evening_revert; default settings) on MNQ and MES 2021-2022 (503 sessions, 500 control draws). Result: all 320 DayTable arrays across the 16 tables are identical. Full suite: 1386 passed, 4 skipped.
- Adding `month_end.py` to `CODE_FILES` changes `code_hash`, so every family's fingerprint changes and its next run re-simulates instead of reading the cache. The honesty counter counts distinct settings, so no trial count moves. The parallel SC-FUT-0012 MES runs (code b578eda6) were logged after this file was added; their results are unaffected.

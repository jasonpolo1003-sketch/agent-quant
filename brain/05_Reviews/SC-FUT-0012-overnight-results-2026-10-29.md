# SC-FUT-0012 overnight drift: practice results (2026-10-29). Both trials FAIL

Spec: `brain/_system/futures/sc-fut-0012-spec.v1.json` (sha256 5cf6d4ac..., frozen in 7a51f9e, unchanged). Addendum: `sc-fut-0012-addendum-1.md`, written before any result. Data: practice 2019-05-01..2024-12-31 from the hash-checked dev file, volume roll, workbench CLI. No exam data was used.

The rule: buy 1 contract at the open of the 17:00 CT Globex reopen bar and sell at the open of D's 08:29 CT bar. T1 trades every night. T2 trades only after a down previous NYSE session. The luck control holds the same position over the same bars in a random direction (500 draws, seeded [20261029, root, yyyymmdd, 12]).

## Verdict (spec gates, MNQ, L3)

| Trial | $/day L3 | vs control $/day | p (one-sided) | bar | Sharpe (≥1.0) | $5 floor | Verdict |
|---|---|---|---|---|---|---|---|
| T1_unconditional | **+6.59** | +9.75 | **0.028** | 0.0253 | **0.51** | pass | **FAIL** (p just above the bar; Sharpe fails by a wide margin) |
| T2_after_down_day | +3.19 | +4.53 | 0.118 | 0.0253 | 0.32 | fail | **FAIL** (all three gates) |

- Days: 1,418 evaluable (1,425 eligible; 7 non-evaluable because the 17:00 or 08:29 bar was missing, 0.49%, under the workbench's 1% missing-minute alarm). 52 nights were holiday skips at $0 (addendum item 1). Trades: T1 1,366, T2 625.
- The p-values come from the workbench headline test (stationary bootstrap, 9,999 replicates). The workbench grid repeats the test with 1,999 replicates and gets 0.032 / 0.13.
- **Honesty bar.** The spec bar is 0.0253 per trial. The workbench counter multiplies FAMILY_SPLIT 2 by the trials logged, so its own printed bar was 0.0253 for T1 but 0.0127 for T2, and stricter again for the MES diagnostics. Both trials fail under either bar.
- **The holiday reading** (addendum item 1) cannot change the verdict. T1's p of 0.028 sits near the bar, but its Sharpe of 0.51 is half the required 1.0, and the reading touches only 52 of 1,418 days.
- Neither trial goes to the prop simulator ("advance" gate). Nothing is retuned.

## Cost levels (MNQ, $/day over evaluable days)

| Trial | L1 | L2 | L3 | L4 |
|---|---|---|---|---|
| T1 | 8.04 | 7.56 | 6.59 | 4.67 |
| T2 | 3.85 | 3.63 | 3.19 | 2.31 |

Costs are not what makes this fail. One trade a night costs about $1-5 against about $10 of gross. The problem is the size of the return relative to its swings: T1's Sharpe is only about 0.75 even before any cost.

## Per year (MNQ, L3)

| Year | T1 $/day | T1 vs control | T1 p | T1 Sharpe | T2 $/day | T2 p | T2 Sharpe | Days |
|---|---|---|---|---|---|---|---|---|
| 2019 (May-) | +7.43 | +10.99 | 0.104 | 1.27 | +3.14 | 0.121 | 0.78 | 166 |
| 2020 | **+30.46** | +34.11 | 0.004 | 2.39 | +6.71 | 0.197 | 0.71 | 247 |
| 2021 | +4.89 | +8.26 | 0.209 | 0.45 | +5.58 | 0.165 | 0.71 | 252 |
| 2022 | **-24.61** | -22.72 | 0.948 | -1.44 | -8.64 | 0.761 | -0.65 | 251 |
| 2023 | -3.13 | +0.60 | 0.477 | -0.31 | +1.29 | 0.331 | 0.21 | 250 |
| 2024 | **+25.08** | +27.97 | 0.015 | 1.61 | +11.05 | 0.138 | 0.85 | 252 |

T1's total of +$9,349 comes almost entirely from 2020 and 2024. It lost money in 2022 (-$6,177) and 2023. It also follows the volatility regime: calm days -$13.31/day, normal +$11.38, volatile +$15.63. So the return depends on the market regime and is not steady.

## Where the drift lives: always-long RTH on the same sessions (L3, same contract)

Long at D's 08:30 open, out at the close of the last bar before the regular close (addendum item 6). This uses the same sessions as each trial's trades, and none were missing.

| | Overnight $/traded day | RTH $/traded day | Overnight Sharpe | RTH Sharpe |
|---|---|---|---|---|
| MNQ T1 (1,366 sessions) | +6.84 | +3.43 | 0.51 | 0.17 |
| MNQ T2 (625 sessions, after down days) | +7.23 | **+13.06** | 0.32 | 0.43 |
| MES T1 | +0.98 | -1.53 | 0.12 | -0.14 |
| MES T2 | -1.82 | +4.76 | -0.13 | 0.27 |

(Sharpe is over all evaluable days, with $0 on days without a trade.)

- **Unconditional (T1).** On MNQ the night carried more of the gain than the cash session: +5.03 points of gross per night against about +3.3 per RTH session. That matches the papers' direction. But it is still weak and depends on the period.
- **After a down day (T2).** The papers' "larger after a down US session" does not show up as an overnight-specific effect here. After a down day, the *following RTH session* earned more than the night (+$13.06 against +$7.23 per traded day on MNQ). Whatever bounce follows a down day is spread across the whole next day; it is not concentrated in the Globex night.

## MES diagnostic (not gated)

| Trial | $/day L3 | vs control | p | Sharpe |
|---|---|---|---|---|
| T1 | +0.94 | +6.92 | 0.014 | 0.12 |
| T2 | -0.79 | +1.92 | 0.201 | -0.13 |

MES nights average +1.44 points (about $7.20 gross), and the $6.22 L3 cost takes almost all of it. Per year, T1 MES runs +2.39 / +15.53 / +1.46 / -17.08 / -6.11 / +10.16 $/day for 2019-2024, the same pattern as MNQ.

## The beta caveat

This rule is long-only. The random-direction control is centred on zero, so "beats the control" here means "the overnight return was above zero in 2019-2024". It does not mean skill. T1's +$9.75/day against the control is just its average gross (+$6.59 + $3.22 cost). In those years the Nasdaq more than doubled: overnight plus RTH gross on these sessions adds up to about +11,400 MNQ points. A strategy that earns plain market beta looks good in a rising market and loses in a falling one, which is exactly what happened in 2022 (-$24.61/day). Even if the p-value had cleared 0.0253, it would have measured "Nasdaq went up overnight in this sample", not an edge that could be repeated. The RTH comparison adds one finding: on MNQ, without conditioning, the overnight window did collect more of that beta than the RTH session.

## Engineering and checks

- New code. Builder `bars.build_overnights` (additions only; the earlier bars.py is an exact prefix of the new one, and `build_days` is byte-identical). Plug-in `workbench/overnight.py` (`OvernightDrift`; a custom equity path walks the minutes in order across midnight). Registry, GRADING (the $5 floor and Sharpe ≥ 1.0 tiers, as in `_SMALL_EDGE`), DESCRIPTIONS, `engine.CODE_FILES`, `analysis.FAMILY_SPLIT["overnight_drift"] = 2`, and CLI `dev_loader(overnight=True)`.
- Fixtures: 12 new tests in `tests/test_bracket_fixtures.py` (o1-o12). They cover:
  - the entry and exit bars, plus the equity low across midnight;
  - a missing 17:00 or 08:29 bar making the day non-evaluable;
  - the holiday skip, with a real MLK gap in the builder;
  - the Sunday-to-Monday night, where Friday evening bars are excluded;
  - T2 reading the last bar before 15:00 and the 08:30 open (the 15:00 and 15:05 bars are ignored);
  - an early-close previous session using its 12:14 bar;
  - costs L1-L4 on the engine table;
  - control seeding, checked against an independent PCG64([20261029, root, yyyymmdd, 12]) stream for MNQ and MES;
  - the registry and the 0.0253 bar.
- **Existing families unchanged.** noise, bracket, shock, orb, controls, session_audit, multi, inference and paths are untouched against HEAD. I also re-simulated gap_fill MNQ, fade_band MNQ, evening_revert MNQ and evening_revert MES with the new code: every DayTable array is **identical** to the tables cached under the old code hash (46fd067e).
- **Concurrent edit.** Another agent added SC-FUT-0013 (`month_end`) to strategies.py, engine.py, analysis.py and scripts/workbench.py while these runs were going. That is why the ledger shows code 56273e1c for the MNQ runs and b578eda6 for the MES runs. The MNQ tables re-simulated under the later code are identical to those logged, so all four runs used the same overnight logic.
- Ledger fingerprints:
  - MNQ T1: 329edf58d5...
  - MNQ T2: 4f52e9567c...
  - MES T1: f205f94a73...
  - MES T2: 0b40dc6c3d...

  Results are in `brain/04_Backtest_Reports/workbench/results/<fingerprint>.json`.

## Running count
Failed MNQ ideas on practice data:
- ORB
- late momentum
- shock reversal
- pyramiding
- multi-market
- cushion sizing
- day tilt
- fade band
- gap fill
- evening reversion
- overnight drift (T1, T2)

SC-FUT-0005 is still the only practice pass, and it failed exam check #1.

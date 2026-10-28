# SC-FUT-0008 noise-area on four markets: FAILED (2026-10-28)

Card frozen bf83fcf before any new-market result. Practice 2019-05..2024-12, volume roll, L3.

## Per market (1 contract, workbench; not gated)
| Market | $/day after L3 | vs random direction | p | Sharpe |
|---|---|---|---|---|
| MNQ (SC-FUT-0005) | +$11.49 | +$14.15 | 0.0001 | 1.31 |
| ZN | −$58.98 | +$3.50 | 0.19 | −5.1 |
| M6E | −$5.04 | +$0.33 | 0.29 | −3.3 |
| MGC | −$3.24 | +$1.08 | 0.29 | −0.7 |

None of the new markets shows an edge over random direction, even before costs. ZN's $65.80 round trip (4 ticks × $15.625 + fees) makes it a large loser on top.

## Book (MNQ 2, ZN 2, M6E 13, MGC 5; sizes from volatility only)
All 4 cells FAIL: mean net cash −$483 (standard plan) / −$933 (no activation fee plan) over 42 days, 0% chance of a payout (stated 15–70%). It "beats luck" ([+44, +97]) only because luck pays the same costs. Output: `brain/04_Backtest_Reports/workbench/prop/portfolio/SC-FUT-0008_20261028T165754Z.json`.

## Conclusion
The noise-area edge is specific to equity-index futures (MNQ; MES is too costly). Diversifying this rule across markets does not work. No variants (frozen); markets and sizes were not changed after results.

## Data and spend
Bought ZN, 6E, GC outright 1-min 2019-05..2024-12 ($29.73 of credit). ZC was refused with HTTP 402 (free credit used up, nothing charged); the first run's broken ZN definition stream probably used part of the credit. CL not bought. Card charges: $0.

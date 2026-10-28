# SC-FUT-0007 MNQ pyramiding: FAILED the cash gate (2026-10-28)

Card: brain/03_Strategy_Cards/SC-FUT-0007-noise-area-pyramiding.md (frozen 29e857d before any result). Workbench trial 6dc9a56f, MNQ, volume roll, practice 2019-05..2024-12.

## Result
| | SC-FUT-0005 (1 MNQ) | SC-FUT-0007 (1 MNQ base, up to 4) |
|---|---|---|
| Mean / day after L3 | $11.49 | $13.23 |
| vs random direction (same rule) | +$14.15, p 0.0001 | +$13.94, p 0.002 |
| Sharpe | 1.31 | **0.73** |
| Day sd | ≈ $139 | $286 |
| Best 20 days, share of profit | 76% | **172%** |
| Worst day (uncapped) | −$629 | −$1,327 (7 days below −$1,000) |

Units per traded day: 2.4 on average, up to 8 (adds across a reversal).

**Cash gate (42 days, Topstep 50K + $1,000 DLL, L3), all 4 cells FAIL:**

| Plan / payout path | Mean net cash | Luck | Strategy − luck, 90% | Payout chance |
|---|---|---|---|---|
| standard / standard | −$112 | −$114 | [−7, +5] | ~0% |
| standard / consistency | −$113 | −$114 | [−7, +4] | ~0% |
| no activation fee / standard | −$205 | −$210 | [−5, +13] | ~0% |
| no activation fee / consistency | −$206 | −$210 | [−6, +11] | ~0% |

Stated payout range was 3–30%; the result is below it. Output: `brain/04_Backtest_Reports/workbench/prop/portfolio/SC-FUT-0007_20261028T162201Z.json`.

## Why
- Adds fill after the move and are given back at the band/VWAP trailing stop. They roughly double the day's volatility but add only about $2/day.
- At a 1-MNQ base, ~$13/day is far below the ~$70/day needed to reach the $3,000 Combine target within 42 days. The account never gets to a payout, so strategy and luck both just pay fees.
- Lesson for B3: the size of the whole book matters more than per-contract tricks. Sizes must be fixed in advance from volatility, large enough to matter.

No variants (frozen). The noise_area family's honesty counter rises by 1 (workbench) + 4 (cash cells).

# Firm × account-play grid for SC-FUT-0005: no cell passes (2026-10-28)

Plan: `brain/_system/plan/prop_firm_grid_plan.md` (+ pre-run addendum). Menu: `brain/_system/prop/account-play-menu.v1.json` (values frozen f1cb0c8, pinned 7e66b5c). QA: `prop-firm-grid-QA-2026-10-28.md` (DLL-exit floor bug and 4 rule readings fixed before the run). Strategy: SC-FUT-0005, MNQ, workbench trial 266777ef (practice 2019-05..2024-12), L3, 42 trading days, 2,000 paths, 40 outer resamples. Output: `brain/04_Backtest_Reports/workbench/prop/firm_grid/266777ef7609_20261028T190356Z.json`.

Ran: 12 firm-plan files × variants × 4 policies + the 4 Topstep 50K adapter variants = 88 cells. Not run (refused to load): Lucid Flex/Pro/Direct (no official price), FundedNext Rapid Pro and Tradeify Lightning (no official payout share).

## Result
- **No cell passes** (needs mean net cash lower bound > $0 AND beats luck). The confirmation run is therefore not needed.
- **Luck is negative in every cell** (no "volatility pays" artifact after the QA fix).
- **Only the most aggressive policy has a positive average.** P4 (Combine 12 MNQ, funded 4 MNQ) is positive in 9 of its 22 cells; P1–P3 are negative everywhere.

| Best cells (P4_sprint_both) | Mean net / 42 d | 90% range | Payout chance | Chance > $0 | Worst 5% | vs luck (90%) |
|---|---|---|---|---|---|---|
| Tradeify Growth 50K (no Python route; L3 flatters) | +$134 | [−36, +484] | 31% | 31% | −$715 | [+217, +728] |
| Topstep 50K standard / standard path (adapter, no API fee) | +$132 | [−28, +368] | 40% | 36% | −$541 | [+120, +509] |
| Topstep 50K standard (research file, incl. $29/mo API, 2 min days) | +$74 | [−86, +310] | 40% | 34% | −$599 | [+120, +509] |
| Topstep 50K no-activation-fee (research file) | +$70 | [−103, +337] | 40% | 36% | −$818 | [+169, +583] |

- **Bigger accounts are worse:** Topstep 100K and 150K are negative in every cell (higher fees, same edge per contract).
- **The consistency payout path is worse than standard** at Topstep.

## Reading
The edge clearly beats luck once sizes are large, and the account's capped downside turns that into a small positive average. But the average is about $70–130 per 2-month attempt, the 90% range still includes losing, and about 2 in 3 attempts lose $200–800. This is a positive-expectancy bet at best, not a reliable income, and it is not proven at the frozen gate.

The result points at larger Combine sizes than the menu's 12 MNQ. Testing that now would be post hoc: it needs a new frozen menu, and its trials count.

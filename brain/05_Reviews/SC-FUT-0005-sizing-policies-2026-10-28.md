---
title: SC-FUT-0005 sizing-policy menu v1 — net cash over 2 months
date: 2026-10-28
status: result
menu: brain/_system/prop/sizing-policies.v1.json (sha256 af94e59a…, frozen before results)
workbench_trial: e08a7acd94e9 (noise_area MNQ, volume roll; same $11.49/day as c3ebff0a7e)
result_file: brain/04_Backtest_Reports/workbench/prop/policies/e08a7acd94e9_20261028T061936Z.json
---

# Result: every cell loses money in 2 months

20 cells: 5 policies × 2 pricing plans × 2 payout paths. Settings: 42 trading days, L3 costs, 2,000 paths, paired outer resampling 40 × 300. Practice data 2019-24 only.

| Policy | Mean net cash, 2 months | Chance net > $0 | Any payout | Beats luck (lower 90%) |
|---|---|---|---|---|
| P1 fixed 2 | −$111 to −$196 | 1% | 1.5% | yes, +$2 to +$25 |
| P2 fixed 3 | −$117 to −$212 | 1–5% | 5% | only on the $95 plan |
| P3 cushion | −$107 to −$185 | 1–2% | 2% | only on the $95 plan |
| P4 cushion + DLL | −$105 to −$185 | 1–2% | 2% | only on the $95 plan |
| P5 + profit stop | −$107 to −$182 | 1–2% | 3% | only on the $95 plan |

## What it means
- **The strategy loses less than luck, but it doesn't make money in 2 months.** The losses are mostly subscription fees. "Beats luck" here means losing $20–80 less than random trading.
- **Time is the bottleneck, not risk.** At about $11 per contract per day after costs:
  - passing the $3,000 Combine takes about 2–3 months at 2–3 MNQ;
  - the XFA then needs 5 winning days before the first payout.

  So almost no 42-day run reaches a payout. The risk tools (cushion sizing, DLL, profit stop) change little because breaches are rare at these sizes. Size is capped by risk, and the result is capped by the clock.
- **Size that would be fast enough isn't safe enough.** The worst practice day is $629 per contract, so 4+ MNQ risks most of the $2,000 limit in one day.

## Gap in the frozen selection rule
The rule said: pick the highest lower bound of net cash minus luck. It selected **P2 fixed 3 / no-activation-fee / consistency**, a cell that loses **$212 on average**. The rule never required positive net cash.

It is not rewritten after the fact. Recommendation: **do not spend the 2025-26 exam check on this selection.** Any future menu must also require mean net cash > $0 and a payout chance stated in advance.

## Trials
20 ledger entries in `prop_trials.jsonl` (menu sha256 af94e59a…). Also one workbench re-run of SC-FUT-0005 MNQ, needed to store minute records; same result, new code fingerprint.

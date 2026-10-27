---
card_id: SC-FUT-0001
verdict: not_demonstrated
decided_by: Jason
decided_at: 2026-10-26
held_out: unread
---

# SC-FUT-0001 — closed, not demonstrated

**Rule:** MNQ cash-open 15-minute opening-range breakout, stop at 10% of the 14-session ATR, flat by 15:07 CT, L3 costs. Frozen spec `brain/_system/futures/sc-fut-0001-spec.v1.json` (SHA-256 `e19f1907…30fb`).

## Evidence (authorized development run, `brain/04_Backtest_Reports/SC-FUT-0001/development/`)

| | MNQ 2019–2023 (primary) | MNQ 2024 (diagnostic) | MES 2019–2023 (comparison) |
|---|---|---|---|
| Evaluable days / trades | 1,157 / 1,664 | 252 / 373 | 1,157 / 1,715 |
| Net per day at L3 | **$3.11** (floor $15) | $1.99 | −$5.28 |
| vs 500 random entries per day | +$5.28/day, **p = 0.114** | +$1.90, p = 0.43 | +$2.68, p = 0.18 |
| Verdict | not demonstrated | not demonstrated | not demonstrated |

- **Power:** 86% joint power to detect a true +$20/day, above the 80% target, so this is an adequately powered negative.
- **Data checks:** missing-minute share 0.17% (limit 1%); same-bar stops 1.7% (limit 10%). The verdict is unchanged under the worst-case gap bound.
- **By year:** −$1.45, +$0.48, +$1.95, +$9.87, +$2.93. Profit is concentrated in 2022.
- **Cost ladder:** $5.27 (L1) down to $0.24 (L4).
- **DSR:** 0.74 at N=1 and 0.11 at N=25.
- **Consistency with the source:** this matches Fetna (2026). ORB does not survive trading costs.

## Decision
Jason closed the card on 2026-10-26 without the held-out read. Spending the only clean 2025-01-01..2026-10-21 MNQ minute data on a rule this far below the $15/day floor would mostly leak information into future MNQ intraday cards. The ledger records `card_closed`, and the runner now refuses a held-out read for a closed card.

## Counts toward future selection
One frozen rule (MNQ primary; MES comparison reported, not selectable) and one authorized development run. The run was re-executed once to save control draws, with byte-identical results. Any future card that is a variant of this rule counts this trial.

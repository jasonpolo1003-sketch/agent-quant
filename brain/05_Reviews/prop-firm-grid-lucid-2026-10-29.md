# Lucid plans in the frozen firm grid (SC-FUT-0005), 2026-10-29

This reruns the frozen account-play menu: SC-FUT-0005, MNQ, workbench trial 266777ef, 2019-05..2024-12, L3 costs, 42 trading days, 2,000 paths.

Lucid plans:
- Lucid publishes no official prices. These use indicative prices from blog and affiliate sites, kept in `brain/_system/prop/firms_indicative/`:
  - Flex 50K: $165, the no-daily-loss-limit version.
  - Pro 50K: $192.
- Reset price unknown, so every failed attempt rebuys the account at full price.
- LucidDirect: not run. Its payout share is not stated.
- Output: `brain/04_Backtest_Reports/workbench/prop/firm_grid/266777ef7609_20261029T054205Z.json`.

## Results (mean net cash over 42 days)

| Plan / policy | P1 | P2 | P3 | P4 (12 MNQ eval / 4 funded) |
|---|---|---|---|---|
| LucidFlex 50K @ $165 | −$171 | −$196 | −$292 | −$219 (payout 36%) |
| LucidPro 50K @ $192 | −$216 | −$347 | −$385 | −$481 (payout 2%) |
| For reference: Topstep 50K standard (10-28 grid) | | | | +$74..+132 |

- **No Lucid cell passes.**
- **Why:** there is no cheap reset. A failed attempt costs $165, against Topstep's $49 reset.
- **LucidPro is worse still.** Its funded account pays only above +$2,100, and best days are capped at 40%.

## Price sensitivity: LucidFlex P4 only (post hoc, not a gate)

| Price | Mean net | Lower bound |
|---|---|---|
| $120 | −$41 | |
| $90 | +$77 | −$53 |
| $60 | +$196 | +$69 |

- Break-even is about $110 an attempt.
- The $60 cell technically clears the grid gate. But the price was chosen after seeing results, so it is not a valid pass.

## Reading

- At list prices, Lucid is worse than Topstep for this strategy.
- It becomes competitive only with a deep discount, about 40% or more off. A real discount code and a reset price would need to be confirmed.
- Lucid's advantage is bot permissions, not cost.

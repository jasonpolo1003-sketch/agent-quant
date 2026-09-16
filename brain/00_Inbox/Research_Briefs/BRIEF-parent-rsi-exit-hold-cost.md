---
id: BRIEF-parent-rsi-exit-hold-cost
type: research_brief_parent
status: queued
method_family: mean_reversion
created: 2026-09-07
related_plan: PLAN-research-narrow-rsi-exit
prior_research: RQ-dd7da469
child_research_ids: [RQ-6d9c12f4, RQ-c920baeb, RQ-80be8cf7]
---

# Parent Brief — RSI Exit / Hold / Cost Wave

Prior live run `RQ-dd7da469` / `RUN-rsi-exit-live-v5` was **rejected** (discovery-only sources). Kept as audit receipt. Replaced for scoping by the three child RQs below.

## Freeze

```text
Universe: SPY, QQQ, IWM
Timeframe: daily bars
Entries locked: RSI(14)<30 or RSI(2)<20 at close; fill next bar
This pass: exits, max hold, costs only
Promotion bar: primary or practitioner only
Cap: ≤5 sources total across A/B/C for the first acquisition wave
No strategy card in this plan
```

## Children

| Role | ID | Focus |
|---|---|---|
| RQ-A exit | `RQ-6d9c12f4` | Source-supported exit rules (≤2 candidates) |
| RQ-B hold | `RQ-c920baeb` | Hard max holding periods (≤2 candidates) |
| RQ-C cost | `RQ-80be8cf7` | Fixed commission + slippage table |

## Rules

- Do not change entry candidates.
- Do not create strategy cards or backtests in this wave.
- Cite upstream sources only; never cite Agent Reach.
- Fail closed if nothing promotes.

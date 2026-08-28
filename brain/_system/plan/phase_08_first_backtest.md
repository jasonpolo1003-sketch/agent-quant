---
id: PHASE-08
type: plan_phase
phase: 8
title: Strategy card + first backtest
status: pending
blocked_by: PHASE-06
created: 2026-08-28
---

# Phase 8 — Strategy card + first backtest

Parent plan: [../../../PLAN.md](../../../PLAN.md)

> **This phase is blocked.** Do not start it until Phase 6 has produced curated, source-supported evidence for an exit rule, a maximum holding period, and cost assumptions. If that evidence does not exist, the correct action is another research pass — not a strategy card with guessed parameters.

This doc is intentionally lighter than Phases 0-6. Detail it fully when Phase 6 completes and we know what the evidence actually says. Writing precise backtest specs before knowing the entry/exit rules would be exactly the overengineering the project's design rule forbids.

## Entry gate (all must be true)

- [ ] Phase 6 complete, acceptance run reviewed.
- [ ] Curated source note(s) support a **specific** exit condition.
- [ ] Curated source note(s) support a **maximum holding period**.
- [ ] Fixed transaction-cost and slippage assumptions recorded, with their basis stated (not invented).
- [ ] [../../02_Strategy_Doors/DOOR-etf-mean-reversion.md](../../02_Strategy_Doors/DOOR-etf-mean-reversion.md) updated to reflect resolved gaps.
- [ ] Jason has explicitly approved moving to strategy-card stage.

## What gets built

### 1. Strategy card (frozen before any result is seen)

Per [../research_source_quality_policy.md](../research_source_quality_policy.md), a card requires:

- universe and data fields
- signal calculation
- entry, exit, and maximum holding period
- execution timing
- position sizing and portfolio rules
- costs: spread, slippage, funding, borrow as relevant
- benchmark and validation plan
- **parameter-count and multiple-testing declaration**

The bounded RSI candidates from RQ-17a4103d are:
```
RSI(14) below 30 at the close
RSI(2) below 20 at the close
next-bar entry for either candidate
```

Pick **one**. Testing both and reporting the winner is multiple testing — if both are tested, the card must declare it and the review must penalize it.

Card goes to `brain/03_Strategy_Cards/`, registered in the `strategy_cards` table. **Freeze it before running anything.**

### 2. Backtest runner

`src/quant_brain/backtest/` using `backtesting.py` (already a dependency).

Non-negotiables, enforced in **code** not convention:
- Close-based signals execute **no earlier than the next bar**. This is the one gate in [../pre_backtest_validation_checklist.md](../pre_backtest_validation_checklist.md) and it is enforced, not trusted.
- Transaction costs and slippage included from the card's declared assumptions.
- Benchmark comparison (buy-and-hold SPY) in the same run.
- Exact dataset id and code version recorded in `backtests`.
- Metrics written to the `metrics` table (schema already has the columns).

### 3. Report + adversarial review

- Report Markdown → `brain/04_Backtest_Reports/`.
- Adversarial review → `brain/05_Reviews/`, with a verdict that **can be reject**.
- Review should consider: lookahead, cost realism, sample size, regime dependence, parameter sensitivity, multiple testing, and whether the result is distinguishable from noise.
- Candidate use for `qwen3.8:27b` as the adversarial reviewer — it is the designated escalation/review model.

## Definition of done

- [ ] One strategy card frozen and registered
- [ ] One backtest run with next-bar execution enforced in code
- [ ] Costs and benchmark included
- [ ] Metrics persisted; report written
- [ ] Adversarial review written with an honest verdict
- [ ] `PLAN.md` §10 checkpoint updated

## Do not

- Do not tune parameters after seeing results and then report the tuned version as if it were the original hypothesis.
- Do not report a backtest as evidence the strategy will work. It is evidence about the past, under assumptions.
- Do not paper trade. Do not live trade. Not in this phase, not in any phase.
- Do not expand to more symbols/markets to "get more data." That is Phase 9, deliberately separate.

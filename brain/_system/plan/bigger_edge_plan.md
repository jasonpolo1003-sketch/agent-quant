# Plan: find an edge big and fast enough to pay out in 2 months (2026-10-28)

Status: **approved by Jason 2026-10-28** (order approved; data purchase approved **from free Databento credits only, nothing extra on the card**; push done). Context: SC-FUT-0005 beats luck but loses $105–212 over 42 days under every frozen sizing rule (`brain/05_Reviews/SC-FUT-0005-sizing-policies-2026-10-28.md`).

## Goal
One frozen rule set (or a small portfolio of them) that clears the cash gate on 2019-24 practice data, then one locked 2025-26 exam check.

**Cash gate (fixed now, before any new result):** for the 42-day Topstep 50K + $1,000 DLL lifecycle,
1. mean net cash > $0, AND
2. beats luck at the same sizing (lower 90% bound of the difference > 0), AND
3. the payout chance written on the card before the run, and the result within its range.

Target to aim for: about $100–150/day net at a size whose worst day fits the $1,000 DLL (≈ double SC-FUT-0005's Sharpe).

## The bar (from `scripts/edge_bar.py`, synthetic days, Topstep 50K + $1,000 DLL)
| Mean net per day | Daily sd | Payout within 42 days | Mean net cash |
|---|---|---|---|
| $0 (luck) | $600 | 23% | −$31 |
| $50 | $600 | 39% | +$277 |
| **$100** | **$600** | **57%** | **+$741** |
| $150 | $600 | 73% | +$1,401 |
| SC-FUT-0005 at 3 MNQ | ≈ $34/day | ≈ 5% (real data) | −$117 |

Lessons: (1) volatility alone "pays" under prop rules, so always compare with luck; (2) fewer trades costs time on a 2-month clock.

## Work plan

### Phase A: owned data, $0 (start now)
**A1. Portfolio support in the simulator (~1 session).**
- A "sleeve" = one rule on one market with its own size. The account sees the summed P&L of all sleeves, minute by minute, against one shared MLL/DLL.
- The luck control runs every sleeve with random direction at the same sizes and sums the same way.
- Hand-worked fixtures first (two sleeves, DLL hit by the sum but not by either alone; Combine pass from the sum).

**A2. SC-FUT-0007: MNQ pyramiding (card frozen before any result).**
- Base: the SC-FUT-0005 entry/exit unchanged.
- Start at 1 MNQ. Add 1 MNQ each time open profit on the position grows by a fixed step (one step size, chosen on the card from the noise-band width, not tuned), up to a fixed max (≤ 4 total). All units share the existing trailing stop.
- Risk check on the card: worst day at the max size must fit the $1,000 DLL on 2019-24 *before* the gate runs; if it doesn't, the max is lowered on the card before results.
- Luck gets identical pyramiding (adds on its own open profit).
- Workbench, then the cash gate. Honesty counter: noise-area family trial 2.

**Stop and report to Jason** after A2, whatever the result.

### Phase B: more markets, free credits only
**B1. Confirm the credit, then buy (no card charge).**
- Fresh quote 2026-10-28 (2019-05-01..2025-01-01, ohlcv-1m): whole families incl. spreads ZN $9.07, 6E $10.21, GC $21.10, ZC $30.83, CL $132.15. Last week's outrights-only quote: ZN $8, 6E $9, GC $13, ZC $16, CL $37.
- **Buy outright contracts only for ZN, 6E, GC, ZC (≈ $46). CL is out** (it would push past the ~$55 credit).
- The API does not report the credit balance. **Before buying, Jason confirms the remaining credit in the Databento portal (Billing)**, or sets a $0 overage/spend limit there. Buy only if credit ≥ quote + $5 margin; otherwise drop the most expensive market (ZC, then GC) until it fits.
- The download script re-quotes each market and refuses if the quote exceeds its approved cap; end date hard-capped at 2025-01-01 (exam period never bought).

**B2. Dev partition and checks:** SHA256SUMS + manifest, volume roll by default, timestamp/DST and tick-size checks per market, per-market costs (fees + 1 tick slippage) written before any strategy result.

**B3. SC-FUT-0008: one rule across markets.**
- The SC-FUT-0005 noise-area rule, identical parameters on MNQ + the 4 new markets (no per-market tuning).
- Per-market size set by risk budget on the card (each market's worst day ≈ equal share of the DLL), using daily-bar volatility only.
- Report per market AND as a portfolio (via A1). Cash gate on the portfolio. If A2 passes, also test with pyramiding on MNQ (stated on the card in advance).

**Stop and report to Jason** after B3.

### Phase C: only if needed
- **C1.** A stacked opposite-style rule (mean reversion) on MNQ/MES, kept only if its daily P&L is negatively correlated with the momentum rule on practice data. Low conviction.
- **C2.** Event days (CPI/FOMC/payrolls) as a filter on an existing rule only, never a stand-alone strategy.

### Exam
At most one locked 2025-26 check, only for a cell that clears all three gate conditions, at a size and rule written down beforehand. Buying 2025-26 data for new markets needs Jason's separate approval (not in this budget).

## Rules that apply throughout
- Frozen card before any result; practice data 2019-24 only; matched random-direction control; honesty counter per family.
- No per-market or post-hoc parameter tuning; a failed card is recorded, not rewritten.
- No money spent beyond free credits without Jason.

# Plan: find an edge big and fast enough to pay out in 2 months (2026-10-28, draft)

Status: **proposed, waiting on Jason.** Context: SC-FUT-0005 beats luck but loses $105–212 over 42 days under every frozen sizing rule (`brain/05_Reviews/SC-FUT-0005-sizing-policies-2026-10-28.md`). Jason wants a bigger, faster edge and a rethink of risk management.

## The bar (from `scripts/edge_bar.py`, synthetic days, Topstep 50K + $1,000 DLL)
| Mean net per day | Daily sd | Payout within 42 days | Mean net cash |
|---|---|---|---|
| $0 (luck) | $600 | 23% | −$31 |
| $50 | $600 | 39% | +$277 |
| **$100** | **$600** | **57%** | **+$741** |
| $150 | $600 | 73% | +$1,401 |
| SC-FUT-0005 at 3 MNQ | ≈ $34/day | ≈ 5% (real data) | −$117 |

Lessons:
1. **The target is about $100–150 per day after costs, at a size whose worst day fits the $1,000 DLL.** That is roughly 3–4× SC-FUT-0005's edge per unit of risk, i.e. about double its Sharpe (≈ 2.5 annualised).
2. **Volatility by itself "pays" under prop rules.** No-edge trading at sd $1,000 averages +$346. A volatile idea must beat luck at the same volatility, never just show positive cash.
3. **Fewer trades costs time.** For the same average per day, trading 40% of days halves the payout chance. "Fewer, bigger trades" only works if the per-trade edge is much bigger, not just the same edge concentrated.

## Where a doubled Sharpe can credibly come from (ranked)
1. **Diversify the edge we have, across markets.** One same-day rule on ~4 uncorrelated markets raises Sharpe by up to √4 = 2× without touching risk per market. The free daily-data check found average correlation 0.11. Needs 1-minute data for ZN, CL, GC, 6E, ZC: **$83, about $28 after free credits.** This is the most evidence-backed route.
2. **Pyramid into winners (risk management, data we own).** SC-FUT-0005's best 20 days are 76% of its profit. Start each day small (1–2 MNQ, so the worst day still fits the DLL) and add contracts only as open profit grows. That amplifies trend days without raising the opening risk. New card on MNQ; luck gets the same pyramiding.
3. **Stack a second, opposite-style same-day rule on MNQ/MES.** A mean-reversion rule (e.g. extreme opening-gap fade) whose daily P&L is negatively correlated with the momentum rule smooths the combined curve. Lower conviction: the gap fade has decayed in published work, and our earlier reversal ideas failed.
4. **Event days only (CPI, FOMC, payrolls): fewer, bigger trades.** Big moves, but only about 30–40 days a year, and Topstep limits max size into major news. By the bar above this is likely too slow. Kept as a filter idea, not a strategy.

## How each idea is tested
- Frozen card before any result. Practice data 2019-24 only. Matched random-direction control. Honesty counter per family.
- Workbench, then the Phase 2 cash gate: **mean net cash > $0 AND beats luck (lower 90% bound > 0) AND payout chance stated in advance**. This fixes the gap found in menu v1.
- Portfolio ideas (1, 3) need portfolio support in the simulator: summed daily P&L across rules or markets, with one shared account. About 1 session.
- One locked exam check, only for a cell that clears all three.

## Proposed order
1. Now, with owned data: **pyramiding card on MNQ** (idea 2) and portfolio support in the simulator.
2. In parallel, if Jason approves the spend: **buy the 5-market minute data**, then freeze one rule across markets (idea 1). The noise-area rule itself is the natural first candidate.
3. Then idea 3. Idea 4 only as a filter.

## Decisions for Jason
1. Approve this order?
2. Buy the 5-market 1-minute data (≈ $28 out of pocket after free credits)?

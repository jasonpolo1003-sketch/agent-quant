---
card_id: SC-FUT-0008
status: frozen
frozen: true
frozen_at: 2026-10-28
frozen_spec: brain/_system/futures/sc-fut-0008-spec.v1.json
method_family: noise_area_momentum
primary: MNQ + ZN + M6E + MGC (one account)
parent: SC-FUT-0005
---

# SC-FUT-0008: noise-area momentum on four markets in one account

> **FROZEN 2026-10-28** before any result on the new markets (bigger-edge plan, step B3). Binding rules: brain/_system/futures/sc-fut-0008-spec.v1.json.

**Idea:** the SC-FUT-0005 rule works on MNQ, but one market is too small and too slow for a 2-month prop account. The same rule, unchanged, runs on the 10-year note (ZN), micro euro (M6E) and micro gold (MGC), each in its own day session. These markets move mostly independently (daily correlation with stocks about 0.0–0.3), so the account's swings grow more slowly than its edge.

**Sizes (volatility only, before results):** MNQ 2, ZN 2, M6E 13, MGC 5, each sized to roughly the same typical day range as 2 MNQ. Corn was dropped: the free Databento credit ran out before its download (nothing charged).

**Luck:** each market's random-direction control, summed on the same days.

**How it fails honestly:** the rule has no edge outside equity indexes, or costs eat it (ZN costs $65.80 per round trip with 4 ticks of slippage).

**Gate (cash, 42 days, $1,000 DLL, the book's day low = sum of sleeve lows):** mean net cash > $0, beats luck (lower 90% bound > $0), and a payout chance between 15% and 70% (stated in advance). Four plan/path cells. No changes to markets, sizes or sessions after results.

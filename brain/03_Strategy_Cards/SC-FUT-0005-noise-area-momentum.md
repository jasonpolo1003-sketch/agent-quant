---
card_id: SC-FUT-0005
status: frozen
frozen: true
frozen_at: 2026-10-27
frozen_spec: brain/_system/futures/sc-fut-0005-spec.v1.json
frozen_spec_sha256: 90beea10e7ba88e026b1c9e440e0abb0489726193c5fca3ba2cee58379bc85e5
created: 2026-10-27
method_family: noise_area_momentum
primary: MNQ
second_trial: MES
gate: prop evaluation simulator first, workbench statistics second
---

# SC-FUT-0005 — Noise-area intraday momentum

> **FROZEN 2026-10-27** by Jason before any result. Binding rules: brain/_system/futures/sc-fut-0005-spec.v1.json. If it fails, no variants: next comes the multi-market or prop-goal decision.

**No results had been looked at when this card was frozen.**

**Source:** Zarattini, Aziz & Barbon, "Beat the Market: An Effective Intraday Momentum Strategy for S&P500 ETF (SPY)", SFI working paper 24-97, rules read from the paper's own text. On SPY 2007–2024 they report: base Sharpe 0.61; with the band+VWAP trailing stop **1.24** (constant 100% exposure); 1.33 with volatility-scaled leverage up to 4×. About 7,668 trades in 17 years (about 1.8 per day). Costs were $0.0045 per share per side.

**Caveats:**
- Our 2019–2024 practice years lie inside their sample, so this is a **replication check**, not fresh evidence.
- An independent TradingView reimplementation reported much weaker results.

## Rules (paper version translated to CT futures; every choice is Jason's to fix before any result)
| Item | Proposal |
|---|---|
| Open | the 08:30 CT bar's open (9:30 ET cash open) |
| Noise band | For each minute HH:MM: σ = the average over the previous 14 sessions of \|close(HH:MM) / open(08:30) − 1\|. Upper = max(open, previous regular close) × (1 + σ); Lower = min(open, previous regular close) × (1 − σ). |
| Checks | Only at HH:00 and HH:30 CT, from 09:00 to 14:30, using the close of the bar ending at the check time. Fill at that minute's open. |
| Entry | Above Upper: long. Below Lower: short. Inside: flat. |
| Exit / trailing stop | At each check: a long exits when the price is below max(Upper, VWAP); a short exits when the price is above min(Lower, VWAP). It may reverse at the same check if the opposite band is breached. VWAP uses cash-hours bars from 08:30 (volume-weighted). |
| End of day | Flat at the 15:00 CT cash close (inside Topstep's 3:10 cutoff). Early-close days: 12:00 CT. |
| Size | **Constant exposure: 1 contract** (the paper's 1.24-Sharpe version without leverage). Volatility-scaled leverage would be a later, separately counted trial. |
| Roll | **Volume roll** (lesson from the failure review) |
| Costs | L3 primary; L1–L4 reported |

## Cost check done before any data (from the paper's published figures)
- **MES:** the paper-level edge is about 9.7%/yr on about $25k notional, roughly $9–10/day per contract. 1.8 trades × $6.22 ≈ $11/day in costs, so it can't survive.
- **MNQ:** about $40k notional, roughly $15/day; 1.8 × $3.22 ≈ $6/day in costs, so there is room.

So MNQ is proposed as the primary market on cost grounds alone, and MES is reported as the second trial in the same family.

## How it is judged
1. Trade count reported first.
2. **Prop simulator gate:** first-account pass rate vs a random-direction version at the same checks, at the frozen size (proposed: **1 MNQ**), over a 6-month budget, with a 90% range above zero.
3. **Workbench:** vs matched random direction at the honesty-adjusted bar, with grades $5/$10/$15 and Sharpe ≥ 1.0; by year, volatility regime and cost level.

## Engineering needed
- Carry 1-minute volume in the loader (for VWAP).
- A plug-in with multiple trades per day and reversals.
- A matched control with random direction at the same check times.
- Fixtures written first.

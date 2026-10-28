---
card_id: SC-FUT-0005
review: independent rebuild + adversarial review of the MNQ workbench pass
date: 2026-10-27
data: practice only (2019-05-01..2024-12-31 dev partition); 2025-26 exam untouched
script: scripts/sc_fut_0005_independent_rebuild.py
---

# SC-FUT-0005: independent rebuild and adversarial review

**Verdict: the MNQ result is real on practice data, not a code or data artefact.** It is fragile in two ways that matter for a prop account:
- it depends heavily on a handful of big trend days;
- it loses about a third of its edge if orders go in one minute late.

The clean test that remains is the locked 2025-26 exam.

## 1. Independent rebuild (written from the frozen spec only, before reading `noise.py`)

The rebuild shares no code with `quant_brain`:
- it decodes the raw DBN with `databento_dbn`, not the project's struct reader;
- it derives its own volume roll from minute volumes;
- it implements the rule from the spec text.

| | Workbench | Rebuild |
|---|---|---|
| MNQ trades | 1,274 | 1,274 |
| MNQ net $/day (L3) | 11.49 | 11.49 |
| MES net $/day | 2.11 | 2.12 (1,258 trades) |
| Day-by-day gross and trade count | — | **identical on all 1,424 shared days** |
| Volume-roll dates | `roll_volume_check.csv` | identical (derived from same-day volume, applied next session: no look-ahead) |

Only difference: 2019-05-06, the first day of the data, has no previous session. The workbench counts it as a no-trade day; the rebuild skips it. The effect is under 1 cent/day.

Spec ambiguities, which made no difference on any day:
- the σ window: the last 14 sessions with data (workbench) vs 14 calendar sessions filtered (rebuild);
- a missing flatten bar while flat: the workbench says no-trade, the rebuild says non-evaluable.

Engine read-through (`noise.py`) found no defects. Specifically:
- σ uses only earlier sessions;
- the decision uses the close of the bar ending at the check;
- the fill is the check-minute open;
- VWAP stops at the bar before the check;
- a reversal is allowed only to the opposite side;
- the control flips each leg's direction independently, with the same times and prices.

## 2. Is the edge in the direction choice? (independent sign-flip test)

| | Value |
|---|---|
| Gross, random direction on the same legs | $0.00/day |
| Gross, strategy | $14.37/day |
| Edge | **+$14.37/day, z = 3.8, p = 0.0001** (20,000 flips) |

The workbench's own figure was +$14.15/day, p = 0.0001.

Across every family tried so far (ORB, late momentum, shock reversal, TSMOM shelved, noise area), a Šidák bar for 5 trials is p < 0.0102. The result clears it by two orders of magnitude.

## 3. Fill realism (MNQ, $/day after L3 costs)

| Fill assumption | $/day |
|---|---|
| Check-minute open (frozen) | 11.49 |
| Close of the signal bar (no bid-ask bounce benefit) | 11.58 |
| +2 ticks against us per side | 9.70 |
| **One minute late** (open of the next minute) | **7.94** |
| Buy at the minute's high, sell at its low (absurd bound) | -18.15 |

- Break-even extra slippage: **12.8 ticks per side** ($12.85 net per trade). Normal slippage is not a threat.
- **Latency is the threat.** A one-minute delay costs 31% of the edge, so the edge is concentrated right after the signal. Any live version must send orders within seconds of HH:00/HH:30, never on a polling loop that can lag a minute.

## 4. Where the money comes from

- Right-skewed, as trend-following usually is:
  - the best 5 days give 25% of profit, 10 days 44%, 20 days 76%;
  - dropping the best 10 days leaves $6.47/day; dropping the best 20 leaves $2.79/day.
- Both sides make money: longs 650 trades at $15.06/trade; shorts 624 trades at $10.54/trade. It is not just the 2019-24 bull market.
- Getting stronger over time:
  - first half $6.65/day, second half $16.33/day;
  - by year: 2019 -1.53, 2020 8.38, 2021 7.44, 2022 15.71, 2023 15.56, 2024 19.02.
  - Higher-volatility years carry it.
- At 1 MNQ: max drawdown $1,128; worst day -$629; 1%/0.5%/0.1% worst days -$329/-$447/-$578.

## 5. What this means for the prop route

- **Consistency rule risk:** Topstep raises the target if the best day exceeds 55% of total profit. A strategy whose profit comes from a few big days runs straight into that rule. The simulator already models it; Phase 2 payouts should model it too.
- **Size, on risk alone (no P&L used):**
  - the worst practice day at 2 MNQ is about $1,258, which is 63% of the $2,000 max loss;
  - at 3 MNQ it is about $1,887, which is 94%: one bad day from failing.
  - So **2 MNQ is the largest risk-defensible size**. It must still be pre-registered *before* the exam: the 2-MNQ pass rate was already seen (about 50% vs about 18% luck), so practice data can no longer judge that choice.
- **Replication caveat stands:** 2019-24 sits inside the paper's own sample. Only 2025-26 is fresh.

## 6. Recommended next steps (unchanged order)

1. ~~Independent rebuild and adversarial review~~ (this note).
2. Jason pre-registers the prop size (recommend 2 MNQ, by the risk rule above) and the latency rule (orders within 5 s of the check).
3. Simulator Phase 2 (XFA payouts, net cash).
4. One locked 2025-26 exam check (uses 1 of the 3 proctor checks).
5. Only then: forward paper trading.

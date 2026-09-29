---
id: phase_08_strategy_card
type: phase_plan
status: proposed
created: 2026-09-29
parent: PROP-007 step 4
---

# Strategy card: plan (PROP-007 step 4)

## Goal
One **frozen, hashed** strategy card that fixes everything the first backtest will do, written and committed **before any result is seen**. After freezing, nothing on it can change. A different idea is a new card, and every tested variant is logged. This step writes and freezes the card. It does not run a backtest (that is step 5, planned separately).

## Sourced rules available (preserved snapshots, exact quotes on the card)
| ID | Source (snapshot) | Filter | Entry | Exit | Stops |
|---|---|---|---|---|---|
| **A** | ChartSchool, Connors RSI(2) (`2026-09-28/061e9f293b7f-e90b0420.md`) | close > 200-day SMA | "buying opportunities when 2-period RSI moves below 10" | "exiting long positions on a move above the 5-day SMA" | "Connors does not advocate using stops" |
| B | Connors Research "RSI 25" (`f57de4fc3101-1bb9664e.md`) | close > 200-day MA | "4-period RSI is less than 25" (a second unit below 20) | "Sell when the 4-period RSI closes above 55" | none stated |
| C | Arthur Hill, StockCharts (`b047e0cb9183-f90199dd.md`) | 50-day SMA > 200-day SMA | RSI(5) cross below 30 | cross above 70 (4 variants published) | none stated |
| D | NAAIM, Pagonidis (`c5f9673f32a4-97d0dbd7.md`) | none (IBS variant optional) | "Go long at the close if RSI(3) < 10" (**Cutler's** RSI) | "Maintain the position while RSI(3) ≤ 40" | none stated |

## Recommended card: one primary hypothesis, few pre-registered variants
Every extra variant raises the multiple-testing penalty, so the card stays small.

- **Primary hypothesis: rule A, exactly as sourced,** long-only on **SPY**.
- **Pre-registered comparison: rules B and D, exactly as sourced.** They are reported alongside A, never swapped in after the fact. Rule C is left out: it adds four more variants for little gain.
- **Robustness: the same rules on QQQ and IWM.** These are reported, not used to pick a winner.
- **RSI formulas are stated per rule:** Wilder smoothing for A and B (the StockCharts/Connors convention), and Cutler's simple average for D, as the paper specifies.
- **Maximum holding period: none,** because the sources specify none and Connors explicitly rejects stops. The holding-time distribution is reported instead. This replaces PROP-007's example 5/10-day time stops, because inventing a stop would add an unsourced parameter.
- **Execution (AGENTS.md: shift close-based signals to the next bar):** a signal on day *t*'s close is traded at day *t+1*'s open, for both entries and exits. ChartSchool names the next open as an accepted alternative to Connors's before-the-close entry. The card records this deviation from Connors.
- **Price basis:** dividend-adjusted OHLC (`adj_open`, `adj_close`), so strategy and benchmark are both total-return. The split-adjusted basis is recorded, per Gate F.
- **Costs (labelled `assumption`, not sourced):** 2, 5 and 10 bps per side, plus 0 slippage beyond that. Every level is always reported; **5 bps is the headline.**
- **Data:** the Gate F dataset IDs are pinned by ID and content hash.
- **Periods, fixed now:** in-sample **2000-01-03 to 2015-12-31**, held-out **2016-01-04 to 2026-09-25**. The held-out period is read **once**, after the in-sample review.
- **Benchmarks, same engine and same costs:** buy-and-hold SPY; and **random entry**, with the same number of trades and the same holding-time distribution, over the same filter-eligible days, using 1,000 fixed seeds and reporting the strategy's percentile.
- **Pre-declared verdict criteria:** held-out, at 5 bps, the primary is judged **"promising"** only if all of these hold:
  1. average trade > 0 after costs;
  2. it beats the random-entry distribution at or above the 95th percentile;
  3. the deflated Sharpe across all variants on the card is ≥ 0.95;
  4. its maximum drawdown is no worse than buy-and-hold's.

  Otherwise it is **"no edge shown"**. Either result is valid. "Promising" is still not proof of future profit.

## Format and freezing
- **File:** `brain/03_Strategy_Cards/SC-0001-rsi2-connors-spy.md`. Human-readable prose, one fenced JSON block holding the machine-readable spec, and the source quotes with their snapshot paths and content hashes.
- **Schema:** a small pydantic model (`src/quant_brain/strategy/card.py`) with `extra="forbid"`. It requires sources for every rule field, and `assumption` labels on costs and execution deviations.
- **Freeze:**
  - `status: frozen` plus the sha256 of the JSON spec, recorded in the SQLite `strategy_cards` table and committed to git **before** any backtest code reads it.
  - The step-5 runner will refuse a card that is not frozen, or whose hash differs from the recorded one.
- **Quote check:** every quoted passage must still be found in its preserved snapshot's fetched content, using the receipts verifier's resolution.

## Tests (light, hermetic)
- The schema refuses unknown fields, a rule field without a source, and an unlabelled cost.
- The freeze hash is stable, and any change to the spec changes it.
- Every quote on the real card exists verbatim in its snapshot content.

## Decisions for Jason (recommended defaults in bold)
1. **Primary A, with B and D as pre-registered comparisons**; or A alone (smaller penalty, less learned).
2. **Next-open execution** (conservative, sourced as an alternative); or the close (Connors's own, but it needs a same-close fill assumption).
3. **The 2016 split and the verdict criteria above.**

## Out of scope
The backtest runner and any results (step 5), parameter sweeps, the prop-firm check, and any change to the research harness or the market data.

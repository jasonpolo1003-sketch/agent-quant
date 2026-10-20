---
card_id: SC-0001
status: frozen-on-commit
created: 2026-09-29
plan: brain/_system/plan/phase_08_strategy_card.md
approved_by: Jason (2026-09-29)
---

# SC-0001: Connors RSI(2) mean reversion on SPY (with two sourced comparisons)

**This card is written and frozen before any backtest result exists.** Nothing on it may change after freezing. A different idea is a new card, and every tested variant below is logged and counted.

## Hypothesis
On SPY, buying Connors's RSI(2) oversold dips in an uptrend and exiting on a move above the 5-day SMA earns more per trade than chance entries with the same holding times, after realistic costs, on data it was not designed on.

## Rules (exactly as the sources state them; exact quotes in the spec below)
- **A (primary): ChartSchool, Connors RSI(2).**
  - Trade only while the close is above its 200-day SMA.
  - Buy when Wilder RSI(2) is below 10.
  - Exit on a move above the 5-day SMA.
  - No stops.
- **B (comparison): Connors Research "RSI 25".**
  - Trade only while the close is above its 200-day MA.
  - Buy when RSI(4) is below 25, and add a second unit if RSI(4) closes below 20 while in the trade.
  - Sell when RSI(4) closes above 55.
- **D (comparison): NAAIM, Pagonidis.**
  - Buy when Cutler RSI(3) is below 10.
  - Hold while Cutler RSI(3) is at or below 40.
  - No trend filter (the IBS variant is not used).

## Declared assumptions (not sourced; labelled)
- **Execution:** every close-based signal (entry or exit) is traded at the **next day's open**. This deviates from Connors's before-the-close entry. ChartSchool names the next open as an accepted alternative, and it is the project's no-lookahead rule.
- **Costs:** 2, 5 and 10 bps per side, with no extra slippage. All three are always reported, and **5 bps is the headline**.
- **No maximum holding period:** the sources give none, and Connors rejects stops. The holding-time distribution is reported instead.

## Test design (fixed now)
- **Periods:** in-sample 2000-01-03..2015-12-31. Held-out 2016-01-04..2026-09-25, **read once**, after the in-sample review.
- **Symbols:** SPY is primary. QQQ and IWM are robustness checks only, reported and never used to pick a rule.
- **Prices:** dividend-adjusted OHLC (`adj_open`, `adj_close`) for the strategies and benchmarks alike. The datasets are Yahoo split-adjusted (Gate F).
- **Benchmarks, same engine and same costs:**
  - buy-and-hold;
  - 1,000 random-entry runs (seeds 20260929..20261928), matching the trade count and holding-time distribution on filter-eligible days.
- **Multiple testing:** 3 rules × 3 cost levels on SPY make 9 trials, for the deflated Sharpe. The robustness symbols are reported separately.
- **Verdict:** "promising" only if **all** of the following hold on the held-out period at 5 bps. Otherwise the verdict is "no edge shown". Either is a valid result, and neither is proof of future profit.
  1. The average trade is above 0 after costs.
  2. It beats the random-entry distribution at or above the 95th percentile.
  3. The deflated Sharpe across the 9 trials is at least 0.95.
  4. Its maximum drawdown is no worse than buy-and-hold's.

## Spec (machine-readable; hashed at freeze)

```json
{
  "card_id": "SC-0001",
  "title": "Connors RSI(2) mean reversion on SPY (with two sourced comparisons)",
  "hypothesis": "On SPY, buying Connors RSI(2) oversold dips in an uptrend and exiting on a move above the 5-day SMA earns more per trade than chance entries with the same holding times, after realistic costs, on held-out data.",
  "method_family": "mean_reversion",
  "timeframe": "1d",
  "direction": "long_only",
  "universe": {"primary": ["SPY"], "robustness": ["QQQ", "IWM"]},
  "data": [
    {"symbol": "SPY", "dataset_id": "SPY-1d-yfinance-20260929T024440Z-472338d8", "content_sha256": "3a206c0ee32e65a946fa195489f51bca29f83db06990f656907a8f27e920cc13"},
    {"symbol": "QQQ", "dataset_id": "QQQ-1d-yfinance-20260929T024440Z-d0bbceb5", "content_sha256": "c71ff5ead6cc477863ae5c2fe87beaadef6f2044aa5fd911b56a43a0afae1fa0"},
    {"symbol": "IWM", "dataset_id": "IWM-1d-yfinance-20260929T024441Z-9857eca7", "content_sha256": "c1f05b762170fdebed035b95f13cb8bc2a258a891d31e3fa5ed739637646aa04"}
  ],
  "price_basis": {
    "signals_and_fills": "dividend-adjusted OHLC: adj_open for fills, adj_close for indicators and marks",
    "dataset_basis": "yahoo_split_adjusted (Gate F); adj_* = split-adjusted price x Yahoo dividend factor"
  },
  "execution": {
    "text": "A signal computed on day t's close (entry or exit) is filled at day t+1's open. No same-bar fills.",
    "basis": "assumption",
    "rationale": "The project's no-lookahead rule (AGENTS.md). It deviates from Connors's before-the-close entry; ChartSchool names the subsequent open as an accepted alternative.",
    "sources": [
      {"quote": "Chartists watching the market can establish a position either just before the close or on the subsequent open", "snapshot": "brain/00_Inbox/Source_Snapshots/2026-09-28/061e9f293b7f-e90b0420.md", "content_sha256": "061e9f293b7f33eb5df0e5ad01ddf2d3d9c24bf1724bc7e9c64c5dc647e3462c"},
      {"quote": "Connors advocates the before-the-close approach", "snapshot": "brain/00_Inbox/Source_Snapshots/2026-09-28/061e9f293b7f-e90b0420.md", "content_sha256": "061e9f293b7f33eb5df0e5ad01ddf2d3d9c24bf1724bc7e9c64c5dc647e3462c"}
    ]
  },
  "max_holding": {"days": null, "basis": "not specified by the sources; none applied; holding-time distribution reported"},
  "rules": [
    {
      "rule_id": "A",
      "role": "primary",
      "name": "ChartSchool / Connors RSI(2)",
      "rsi": {"period": 2, "method": "wilder", "sources": []},
      "filter": {
        "text": "Long setups only while the close is above its 200-day SMA.",
        "params": {"sma_days": 200},
        "sources": [
          {"quote": "Connors recommends the 200-day moving average", "snapshot": "brain/00_Inbox/Source_Snapshots/2026-09-28/061e9f293b7f-e90b0420.md", "content_sha256": "061e9f293b7f33eb5df0e5ad01ddf2d3d9c24bf1724bc7e9c64c5dc647e3462c"},
          {"quote": "Traders should look for buying opportunities when above the 200-day SMA", "snapshot": "brain/00_Inbox/Source_Snapshots/2026-09-28/061e9f293b7f-e90b0420.md", "content_sha256": "061e9f293b7f33eb5df0e5ad01ddf2d3d9c24bf1724bc7e9c64c5dc647e3462c"}
        ]
      },
      "entry": {
        "text": "Buy when RSI(2) closes below 10.",
        "params": {"rsi_below": 10},
        "sources": [
          {"quote": "Traders should look for buying opportunities when 2-period RSI moves below 10", "snapshot": "brain/00_Inbox/Source_Snapshots/2026-09-28/061e9f293b7f-e90b0420.md", "content_sha256": "061e9f293b7f33eb5df0e5ad01ddf2d3d9c24bf1724bc7e9c64c5dc647e3462c"}
        ]
      },
      "exit": {
        "text": "Exit when the close moves above its 5-day SMA.",
        "params": {"sma_days": 5},
        "sources": [
          {"quote": "Connors advocates exiting long positions on a move above the 5-day SMA", "snapshot": "brain/00_Inbox/Source_Snapshots/2026-09-28/061e9f293b7f-e90b0420.md", "content_sha256": "061e9f293b7f33eb5df0e5ad01ddf2d3d9c24bf1724bc7e9c64c5dc647e3462c"}
        ]
      },
      "stops": {
        "text": "No stop-loss.",
        "params": {},
        "sources": [
          {"quote": "Connors does not advocate using stops", "snapshot": "brain/00_Inbox/Source_Snapshots/2026-09-28/061e9f293b7f-e90b0420.md", "content_sha256": "061e9f293b7f33eb5df0e5ad01ddf2d3d9c24bf1724bc7e9c64c5dc647e3462c"}
        ]
      }
    },
    {
      "rule_id": "B",
      "role": "comparison",
      "name": "Connors Research RSI 25",
      "rsi": {"period": 4, "method": "wilder", "sources": []},
      "filter": {
        "text": "Only while the close is above its 200-day moving average.",
        "params": {"sma_days": 200},
        "sources": [
          {"quote": "Its closing price is greater than the 200-day moving average", "snapshot": "brain/00_Inbox/Source_Snapshots/2026-09-28/f57de4fc3101-1bb9664e.md", "content_sha256": "f57de4fc310105b9b638052882a3592c5d0b9e4506eae3ed87f4f8efe69e69db"}
        ]
      },
      "entry": {
        "text": "Buy one unit when RSI(4) closes below 25.",
        "params": {"rsi_below": 25, "units": 1},
        "sources": [
          {"quote": "one unit at the close when", "snapshot": "brain/00_Inbox/Source_Snapshots/2026-09-28/f57de4fc3101-1bb9664e.md", "content_sha256": "f57de4fc310105b9b638052882a3592c5d0b9e4506eae3ed87f4f8efe69e69db"},
          {"quote": "Its 4-period RSI is less than 25", "snapshot": "brain/00_Inbox/Source_Snapshots/2026-09-28/f57de4fc3101-1bb9664e.md", "content_sha256": "f57de4fc310105b9b638052882a3592c5d0b9e4506eae3ed87f4f8efe69e69db"}
        ]
      },
      "add": {
        "text": "Buy a second unit (maximum two) if RSI(4) closes below 20 while the position is open.",
        "params": {"rsi_below": 20, "max_units": 2},
        "sources": [
          {"quote": "a second unit if the 4-period RSI closes below 20 at any time while the position is open", "snapshot": "brain/00_Inbox/Source_Snapshots/2026-09-28/f57de4fc3101-1bb9664e.md", "content_sha256": "f57de4fc310105b9b638052882a3592c5d0b9e4506eae3ed87f4f8efe69e69db"}
        ]
      },
      "exit": {
        "text": "Sell all units when RSI(4) closes above 55.",
        "params": {"rsi_above": 55},
        "sources": [
          {"quote": "when the 4-period RSI closes above 55", "snapshot": "brain/00_Inbox/Source_Snapshots/2026-09-28/f57de4fc3101-1bb9664e.md", "content_sha256": "f57de4fc310105b9b638052882a3592c5d0b9e4506eae3ed87f4f8efe69e69db"}
        ]
      },
      "stops": null
    },
    {
      "rule_id": "D",
      "role": "comparison",
      "name": "NAAIM / Pagonidis RSI(3)",
      "rsi": {
        "period": 3,
        "method": "cutler",
        "sources": [
          {"quote": "Cutler’s RSI(3) indicator", "snapshot": "brain/00_Inbox/Source_Snapshots/2026-09-28/c5f9673f32a4-97d0dbd7.md", "content_sha256": "c5f9673f32a482a2940a96e28c8281db9247393e5fefb2cc907d81a410ca7c37"}
        ]
      },
      "filter": null,
      "entry": {
        "text": "Buy when Cutler RSI(3) closes below 10.",
        "params": {"rsi_below": 10},
        "sources": [
          {"quote": "Go long at the close if RSI(3) < 10", "snapshot": "brain/00_Inbox/Source_Snapshots/2026-09-28/c5f9673f32a4-97d0dbd7.md", "content_sha256": "c5f9673f32a482a2940a96e28c8281db9247393e5fefb2cc907d81a410ca7c37"}
        ]
      },
      "exit": {
        "text": "Hold while Cutler RSI(3) is at or below 40; exit when it closes above 40.",
        "params": {"hold_while_rsi_at_or_below": 40},
        "sources": [
          {"quote": "Maintain the position while RSI(3) ≤ 40", "snapshot": "brain/00_Inbox/Source_Snapshots/2026-09-28/c5f9673f32a4-97d0dbd7.md", "content_sha256": "c5f9673f32a482a2940a96e28c8281db9247393e5fefb2cc907d81a410ca7c37"}
        ]
      },
      "stops": null
    }
  ],
  "costs": {
    "bps_per_side": [2, 5, 10],
    "headline_bps": 5,
    "slippage_bps": 0,
    "basis": "assumption",
    "rationale": "No cost source cleared the evidence bar (RQ-80be8cf7 source-insufficient); a small, pre-declared range is tested and every level reported."
  },
  "periods": {
    "in_sample": {"start": "2000-01-03", "end": "2015-12-31"},
    "held_out": {"start": "2016-01-04", "end": "2026-09-25"},
    "held_out_reads": 1
  },
  "benchmarks": {
    "buy_and_hold": {"same_costs": true},
    "random_entry": {"runs": 1000, "seed_start": 20260929, "match": ["trade_count", "holding_time_distribution"], "eligible_days": "days where the rule's filter is true"}
  },
  "multiple_testing": {"trials_counted": 9, "trial_grid": "3 rules x 3 cost levels on SPY", "method": "deflated Sharpe ratio", "robustness_symbols": "reported separately, not counted as selection"},
  "verdict_criteria": [
    "held-out, 5 bps: average trade > 0 after costs",
    "held-out, 5 bps: beats the random-entry distribution at or above the 95th percentile",
    "deflated Sharpe across the 9 trials >= 0.95",
    "held-out maximum drawdown no worse than buy-and-hold's"
  ]
}
```

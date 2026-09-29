---
card_id: SC-0002
supersedes: SC-0001 (retired before any backtest; see "Why SC-0002")
created: 2026-09-29
plan: brain/_system/plan/phase_08_strategy_card.md
approved_by: Jason (direction 2026-09-29; freeze pending review)
---

# SC-0002: Connors RSI(2) mean reversion on SPY (with two sourced comparisons)

**Written before any backtest result exists.** Once frozen, nothing on it changes. A different idea is a new card.

## Why SC-0002
SC-0001 was frozen before its independent review. That review found three problems:
- It labelled two unsourced choices as sourced: the RSI method for rules A and B, and a close-based reading of A's exit.
- Its pass test was ambiguous.
- It left implementation details open.

No backtest had read SC-0001 and no result had been seen, so correcting the card is not result-driven. SC-0001 stays on record, marked superseded.

## Rules: what the sources say, and what this card assumes
- **A (primary): ChartSchool, Connors RSI(2).**
  - *Sourced:* buy when 2-period RSI is below 10, above the 200-day SMA; exit "on a move above the 5-day SMA"; no stops.
  - *Assumed:* the RSI uses Wilder smoothing (the source names no method), and "a move above" means the close is above the 5-day SMA.
  - *Noted, not used:* the source's own DIA example uses "RSI(2) moves to 5 or lower", and its buy scan crosses below 5. This card uses the stated headline rule, below 10.
- **B (comparison): Connors Research "RSI 25".**
  - *Sourced:* buy at the close above the 200-day MA when RSI(4) is below 25; add a second unit when RSI(4) closes below 20 while in the position; sell when RSI(4) closes above 55.
  - *Assumed:* Wilder smoothing, and that the "200-day moving average" is a simple average (the source names neither).
- **D (comparison): NAAIM, Pagonidis.**
  - *Sourced:* Cutler's RSI(3); long at the close when RSI(3) is below 10; hold while it is at or below 40. No trend filter.

## Declared assumptions
- **Execution:** close signals are filled at the next day's open. This deviates from every source's at-the-close entry (A, B and D); ChartSchool names the next open as an accepted alternative.
- **Prices:** indicators use dividend-adjusted closes, not the sources' unadjusted prices.
- **Costs:** 2, 5 or 10 bps per side, with 5 as the headline. There is no interest on cash.
- **No time stop:** none of the sources gives one.
- **Implementation details** are all fixed in the spec's `implementation` block.

## The test
- **Periods:** in-sample 2000–2015. Held-out 2016-01-04..2026-09-25, read **once**.
- **Pass test ("promising"):** it applies to **rule A only**, on the **held-out** period at **5 bps**. All four must hold:
  1. The average trade after costs is above 0.
  2. The average trade is at or above the **95th percentile** of 1,000 random-entry runs.
  3. The **deflated Sharpe ratio, as a probability**, is at least 0.95. It uses 3 trials (A, B and D at 5 bps).
  4. Rule A's Sharpe is **above buy-and-hold's**.

  Otherwise the verdict is "no edge shown". Rules B and D and the QQQ/IWM runs are reported but can never earn the label. "Promising" is still not proof of future profit.

## Spec (machine-readable; hashed at freeze)

```json
{
  "card_id": "SC-0002",
  "supersedes": "SC-0001",
  "title": "Connors RSI(2) mean reversion on SPY (with two sourced comparisons)",
  "hypothesis": "On SPY, Connors RSI(2) oversold entries in an uptrend, exited on a move above the 5-day SMA, earn more per trade than random entries with the same holding times, after costs, on held-out data.",
  "method_family": "mean_reversion",
  "timeframe": "1d",
  "direction": "long_only",
  "universe": {
    "primary": [
      "SPY"
    ],
    "robustness": [
      "QQQ",
      "IWM"
    ]
  },
  "data": [
    {
      "symbol": "SPY",
      "dataset_id": "SPY-1d-yfinance-20260929T024440Z-472338d8",
      "content_sha256": "3a206c0ee32e65a946fa195489f51bca29f83db06990f656907a8f27e920cc13"
    },
    {
      "symbol": "QQQ",
      "dataset_id": "QQQ-1d-yfinance-20260929T024440Z-d0bbceb5",
      "content_sha256": "c71ff5ead6cc477863ae5c2fe87beaadef6f2044aa5fd911b56a43a0afae1fa0"
    },
    {
      "symbol": "IWM",
      "dataset_id": "IWM-1d-yfinance-20260929T024441Z-9857eca7",
      "content_sha256": "c1f05b762170fdebed035b95f13cb8bc2a258a891d31e3fa5ed739637646aa04"
    }
  ],
  "price_basis": {
    "signals_and_fills": "dividend-adjusted OHLC: adj_close for indicators and marks, adj_open for fills",
    "dataset_basis": "yahoo_split_adjusted (Gate F); adj_* = split-adjusted price x Yahoo dividend factor",
    "deviation": "the sources used unadjusted prices; this card uses dividend-adjusted prices so strategy and benchmark are both total return"
  },
  "execution": {
    "text": "A signal computed on day t's close (entry, add or exit) is filled at day t+1's open. No same-bar fills.",
    "basis": "assumption",
    "rationale": "The project's no-lookahead rule (AGENTS.md). It deviates from every source's at-the-close entry: Connors's before-the-close approach (A), 'one unit at the close' (B) and 'Go long at the close' (D). ChartSchool names the subsequent open as an accepted alternative.",
    "sources": [
      {
        "quote": "Chartists watching the market can establish a position either just before the close or on the subsequent open",
        "snapshot": "brain/00_Inbox/Source_Snapshots/2026-09-28/061e9f293b7f-e90b0420.md",
        "content_sha256": "061e9f293b7f33eb5df0e5ad01ddf2d3d9c24bf1724bc7e9c64c5dc647e3462c"
      },
      {
        "quote": "Connors advocates the before-the-close approach",
        "snapshot": "brain/00_Inbox/Source_Snapshots/2026-09-28/061e9f293b7f-e90b0420.md",
        "content_sha256": "061e9f293b7f33eb5df0e5ad01ddf2d3d9c24bf1724bc7e9c64c5dc647e3462c"
      }
    ]
  },
  "max_holding": {
    "days": null,
    "basis": "not specified by the sources; none applied; the holding-time distribution is reported"
  },
  "rules": [
    {
      "rule_id": "A",
      "role": "primary",
      "name": "ChartSchool / Connors RSI(2)",
      "rsi": {
        "period": 2,
        "method": "wilder",
        "basis": "assumption",
        "sources": [],
        "rationale": "The source does not name an RSI smoothing method; Wilder's original 1978 definition is the conventional default and is assumed."
      },
      "filter": {
        "text": "Enter only when the close is above its 200-day SMA (checked on the entry signal day; never an exit condition).",
        "params": {
          "sma_days": 200
        },
        "sources": [
          {
            "quote": "Connors recommends the 200-day moving average",
            "snapshot": "brain/00_Inbox/Source_Snapshots/2026-09-28/061e9f293b7f-e90b0420.md",
            "content_sha256": "061e9f293b7f33eb5df0e5ad01ddf2d3d9c24bf1724bc7e9c64c5dc647e3462c"
          },
          {
            "quote": "Traders should look for buying opportunities when above the 200-day SMA",
            "snapshot": "brain/00_Inbox/Source_Snapshots/2026-09-28/061e9f293b7f-e90b0420.md",
            "content_sha256": "061e9f293b7f33eb5df0e5ad01ddf2d3d9c24bf1724bc7e9c64c5dc647e3462c"
          }
        ]
      },
      "entry": {
        "text": "Buy when RSI(2) at the close is below 10.",
        "params": {
          "rsi_below": 10
        },
        "sources": [
          {
            "quote": "Traders should look for buying opportunities when 2-period RSI moves below 10",
            "snapshot": "brain/00_Inbox/Source_Snapshots/2026-09-28/061e9f293b7f-e90b0420.md",
            "content_sha256": "061e9f293b7f33eb5df0e5ad01ddf2d3d9c24bf1724bc7e9c64c5dc647e3462c"
          }
        ]
      },
      "exit": {
        "text": "Exit on a move above the 5-day SMA.",
        "params": {
          "sma_days": 5
        },
        "sources": [
          {
            "quote": "Connors advocates exiting long positions on a move above the 5-day SMA",
            "snapshot": "brain/00_Inbox/Source_Snapshots/2026-09-28/061e9f293b7f-e90b0420.md",
            "content_sha256": "061e9f293b7f33eb5df0e5ad01ddf2d3d9c24bf1724bc7e9c64c5dc647e3462c"
          }
        ],
        "interpretation": {
          "text": "A 'move above the 5-day SMA' is read as: the close (adj_close) is above the 5-day SMA of adj_close.",
          "basis": "assumption",
          "rationale": "The source does not say whether the move is intraday or at the close; a close-based test matches the card's close-signal, next-open execution.",
          "sources": []
        }
      },
      "stops": {
        "text": "No stop-loss.",
        "params": {},
        "sources": [
          {
            "quote": "Connors does not advocate using stops",
            "snapshot": "brain/00_Inbox/Source_Snapshots/2026-09-28/061e9f293b7f-e90b0420.md",
            "content_sha256": "061e9f293b7f33eb5df0e5ad01ddf2d3d9c24bf1724bc7e9c64c5dc647e3462c"
          }
        ]
      }
    },
    {
      "rule_id": "B",
      "role": "comparison",
      "name": "Connors Research RSI 25",
      "rsi": {
        "period": 4,
        "method": "wilder",
        "basis": "assumption",
        "sources": [],
        "rationale": "The source does not name an RSI smoothing method; Wilder's original definition is assumed, as for rule A."
      },
      "filter": {
        "text": "Enter only when the close is above its 200-day moving average (checked on the entry signal day; never an exit condition).",
        "params": {
          "sma_days": 200
        },
        "sources": [
          {
            "quote": "Its closing price is greater than the 200-day moving average",
            "snapshot": "brain/00_Inbox/Source_Snapshots/2026-09-28/f57de4fc3101-1bb9664e.md",
            "content_sha256": "f57de4fc310105b9b638052882a3592c5d0b9e4506eae3ed87f4f8efe69e69db"
          }
        ],
        "interpretation": {
          "text": "The '200-day moving average' is read as the 200-day simple moving average of adj_close.",
          "basis": "assumption",
          "rationale": "The source does not say which moving average; a simple average matches rule A's sourced 200-day SMA.",
          "sources": []
        }
      },
      "entry": {
        "text": "Buy one unit when RSI(4) at the close is below 25.",
        "params": {
          "rsi_below": 25,
          "units": 1
        },
        "sources": [
          {
            "quote": "one unit at the close when",
            "snapshot": "brain/00_Inbox/Source_Snapshots/2026-09-28/f57de4fc3101-1bb9664e.md",
            "content_sha256": "f57de4fc310105b9b638052882a3592c5d0b9e4506eae3ed87f4f8efe69e69db"
          },
          {
            "quote": "Its 4-period RSI is less than 25",
            "snapshot": "brain/00_Inbox/Source_Snapshots/2026-09-28/f57de4fc3101-1bb9664e.md",
            "content_sha256": "f57de4fc310105b9b638052882a3592c5d0b9e4506eae3ed87f4f8efe69e69db"
          }
        ]
      },
      "add": {
        "text": "Buy a second unit (maximum two) when RSI(4) closes below 20 while the position is open.",
        "params": {
          "rsi_below": 20,
          "max_units": 2
        },
        "sources": [
          {
            "quote": "a second unit if the 4-period RSI closes below 20 at any time while the position is open",
            "snapshot": "brain/00_Inbox/Source_Snapshots/2026-09-28/f57de4fc3101-1bb9664e.md",
            "content_sha256": "f57de4fc310105b9b638052882a3592c5d0b9e4506eae3ed87f4f8efe69e69db"
          }
        ]
      },
      "exit": {
        "text": "Sell all units when RSI(4) closes above 55.",
        "params": {
          "rsi_above": 55
        },
        "sources": [
          {
            "quote": "when the 4-period RSI closes above 55",
            "snapshot": "brain/00_Inbox/Source_Snapshots/2026-09-28/f57de4fc3101-1bb9664e.md",
            "content_sha256": "f57de4fc310105b9b638052882a3592c5d0b9e4506eae3ed87f4f8efe69e69db"
          }
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
        "basis": "sourced",
        "sources": [
          {
            "quote": "Cutler’s RSI(3) indicator",
            "snapshot": "brain/00_Inbox/Source_Snapshots/2026-09-28/c5f9673f32a4-97d0dbd7.md",
            "content_sha256": "c5f9673f32a482a2940a96e28c8281db9247393e5fefb2cc907d81a410ca7c37"
          }
        ],
        "rationale": null
      },
      "filter": null,
      "entry": {
        "text": "Buy when Cutler RSI(3) at the close is below 10.",
        "params": {
          "rsi_below": 10
        },
        "sources": [
          {
            "quote": "Go long at the close if RSI(3) < 10",
            "snapshot": "brain/00_Inbox/Source_Snapshots/2026-09-28/c5f9673f32a4-97d0dbd7.md",
            "content_sha256": "c5f9673f32a482a2940a96e28c8281db9247393e5fefb2cc907d81a410ca7c37"
          }
        ]
      },
      "exit": {
        "text": "Hold while Cutler RSI(3) is at or below 40; exit when it closes above 40.",
        "params": {
          "hold_while_rsi_at_or_below": 40
        },
        "sources": [
          {
            "quote": "Maintain the position while RSI(3) ≤ 40",
            "snapshot": "brain/00_Inbox/Source_Snapshots/2026-09-28/c5f9673f32a4-97d0dbd7.md",
            "content_sha256": "c5f9673f32a482a2940a96e28c8281db9247393e5fefb2cc907d81a410ca7c37"
          }
        ]
      },
      "stops": null
    }
  ],
  "costs": {
    "bps_per_side": [
      2,
      5,
      10
    ],
    "headline_bps": 5,
    "slippage_bps": 0,
    "basis": "assumption",
    "rationale": "No cost source cleared the evidence bar (RQ-80be8cf7 source-insufficient); a small pre-declared range is a sensitivity check, and every level is reported."
  },
  "periods": {
    "in_sample": {
      "start": "2000-01-03",
      "end": "2015-12-31"
    },
    "held_out": {
      "start": "2016-01-04",
      "end": "2026-09-25"
    },
    "held_out_reads": 1
  },
  "implementation": {
    "basis": "assumption",
    "indicator_price": "adj_close for every RSI and SMA.",
    "fill_price": "adj_open of the next trading day after the signal close.",
    "warmup": "Indicators run on the full continuous dataset from its first bar (2000-01-03). A signal is valid only once every indicator it uses has a full lookback (SMA200 needs 200 closes, so the first A/B signals fall in October 2000). The held-out period uses the same continuous series; nothing restarts in 2016.",
    "rsi_wilder": "Average gain and loss seeded with the simple mean of the first n price changes, then smoothed as avg = (prev * (n - 1) + current) / n. RSI = 100 - 100 / (1 + avg_gain / avg_loss), and RSI = 100 when avg_loss = 0.",
    "rsi_cutler": "Simple n-day means of gains and of losses. RSI = 100 - 100 / (1 + mean_gain / mean_loss), and RSI = 100 when mean_loss = 0.",
    "filter_scope": "Trend filters are tested only on the entry signal day and never force an exit.",
    "entry_evaluation": "Level tests at each close while flat (for example RSI(2) < 10), not crosses.",
    "reentry_and_same_bar": "While flat, only the entry is evaluated; while in a position, only the exit (and B's add) is evaluated. After an exit fills at the open of day t+1, the close of t+1 is the first bar evaluated for a new entry. An entry and an exit can never fill on the same bar.",
    "sizing": "Equity compounds. A and D: each trade invests 100% of equity at the entry fill. B: each unit is 50% of equity at unit 1's entry fill. Unit 1 fills on the entry signal. Unit 2 is evaluated from the first close after unit 1's fill: an RSI(4) below 20 on the entry signal day itself does not add, so the earliest add fills at the open two trading days after the entry signal. The add has no trend filter ('at any time while the position is open'). Both units exit together.",
    "cash_return": "Uninvested capital earns 0%.",
    "period_boundary": "Each period is simulated separately over the continuous indicator series. A trade belongs to the period containing its entry signal. A signal on a period's last bar is dropped, because its fill would fall outside the period. A trade still open on the period's last bar is closed at that bar's adj_close, with exit costs.",
    "cost_application": "The card's bps per side are charged on the notional of every fill: entry, add, exit and forced close.",
    "sma": "Simple mean of the last n adj_close values including the current bar. 'Above' means strictly greater, and 'below' strictly less, for every SMA and RSI comparison.",
    "trade_return": "Multiplicative per unit: (1 - c) * (exit_price / entry_price) * (1 - c) - 1, where c = bps/10,000. B's trade return is the equity-weighted P&L of its units on the equity at unit 1's entry fill.",
    "daily_returns": "Daily equity returns on every held-out trading day, with flat days as 0, marked to adj_close. A fill day's return runs from adj_open (after cost) to adj_close; an exit day's from the prior adj_close to adj_open (after cost). Risk-free rate = 0. Buy-and-hold is computed the same way: day 1 from adj_open to adj_close after the entry cost, and the last day including the exit cost.",
    "edge_cases": "Zero held-out A trades means the verdict is 'no edge shown'. Datasets are already validated (no missing prices), so no rows are skipped."
  },
  "benchmarks": {
    "buy_and_hold": {
      "text": "Buy SPY at the period's first adj_open and hold to its last adj_close, with one entry and one exit cost.",
      "same_costs": true
    },
    "random_entry": {
      "runs": 1000,
      "rng": "numpy.random.default_rng(seed_start + i) for run i = 0..999",
      "seed_start": 20260929,
      "applies_to": "A",
      "statistic": "average trade return after costs, computed exactly as for rule A",
      "holding_time_definition": "the number of trading days from the entry fill (open) to the exit fill (open); a force-closed trade counts to its closing bar",
      "holding_times": "rule A's own held-out holding times, including any force-closed trade, shuffled with the run's generator and each used once",
      "entries": "for each holding time in shuffled order: an entry fill day drawn uniformly from held-out days, other than the period's first day, on which A's filter was true at the prior close; the whole trade must fit inside the period, and its entry fill must come at least one trading day after the exit fill of any earlier random trade in the run (as for A)",
      "retry_limit": "up to 10,000 draws per trade; a run that cannot place every trade is discarded, the number of discarded runs is reported, and the percentile uses the completed runs",
      "fills_and_costs": "the same next-open fills, costs and trade-return formula as rule A",
      "percentile": "100 x (number of completed runs whose average trade is strictly below A's) / (number of completed runs); if no run completes, the criterion fails"
    }
  },
  "multiple_testing": {
    "trials_counted": 3,
    "trials": "rules A, B and D on SPY at the headline 5 bps",
    "not_trials": "cost levels (a fixed sensitivity check) and QQQ/IWM (robustness, never used for selection)",
    "method": "deflated Sharpe ratio as a probability (Bailey and Lopez de Prado, 2014)",
    "limitation": "With only 3 trials the cross-trial variance is a rough estimate. If it is near 0, the DSR reduces to the probabilistic Sharpe against 0.",
    "formula": {
      "returns": "each trial's daily equity returns over all held-out trading days, flat days = 0 (implementation.daily_returns); T = number of held-out trading days",
      "sharpe": "per-period (not annualised) SR = mean / sample standard deviation (ddof = 1)",
      "V": "sample variance (ddof = 1) of the 3 trials' per-period SRs; SR* = 0 if V = 0",
      "expected_max": "SR* = sqrt(V) * ((1 - g) * Phi^-1(1 - 1/N) + g * Phi^-1(1 - 1/(N * e))), where g = 0.5772156649 (Euler-Mascheroni), N = 3 and Phi^-1 is the standard normal quantile",
      "dsr": "Phi(((SR_A - SR*) * sqrt(T - 1)) / sqrt(1 - skew_A * SR_A + ((kurt_A - 1) / 4) * SR_A^2)), where skew_A is the biased sample skewness and kurt_A the biased raw (non-excess) sample kurtosis (scipy.stats skew and kurtosis with bias=True, fisher=False) of A's daily returns"
    }
  },
  "verdict": {
    "applies_to": "A",
    "period": "held_out",
    "cost_bps": 5,
    "criteria": [
      {
        "name": "positive average trade",
        "metric": "average trade return after costs",
        "comparator": ">",
        "threshold": 0.0,
        "detail": "the mean of rule A's held-out trade returns at 5 bps"
      },
      {
        "name": "beats random entry",
        "metric": "percentile of A's average trade within the 1,000 random-entry runs",
        "comparator": ">=",
        "threshold": 95.0,
        "detail": "benchmarks.random_entry.percentile"
      },
      {
        "name": "deflated Sharpe",
        "metric": "deflated Sharpe ratio (a probability)",
        "comparator": ">=",
        "threshold": 0.95,
        "detail": "multiple_testing.formula, on held-out daily returns at 5 bps"
      },
      {
        "name": "beats buy-and-hold risk-adjusted",
        "metric": "annualised Sharpe of daily returns (flat days count as 0; sqrt(252) scaling)",
        "comparator": ">",
        "threshold": 0.0,
        "detail": "rule A's held-out Sharpe minus buy-and-hold SPY's held-out Sharpe, at the same costs"
      }
    ],
    "if_all_pass": "promising (not proof of future profit)",
    "otherwise": "no edge shown",
    "other_rules": "Rules B and D and every QQQ/IWM run are reported descriptively. None of them can earn a verdict under this card."
  }
}
```

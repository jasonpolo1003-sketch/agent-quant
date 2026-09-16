---
id: RQ-dd7da469
type: raw_research
status: raw_saved
scoping_status: superseded-for-scoping
replaced_by: RQ-6d9c12f4, RQ-c920baeb, RQ-80be8cf7
scoping_note: Prior live run rejected; narrower acquisition uses child RQs (see BRIEF-parent-rsi-exit-hold-cost).
method_family: mean_reversion
assigned_agent: live_research_executor
run_id: RUN-rsi-exit-live-v5
---

# Raw Research Note â€” RQ-dd7da469

## Research Question

Find high-quality sources for simple non-optimized exit conditions and maximum holding periods that could pair with daily ETF RSI oversold entries. Compare at most two source-supported choices, explain timing and regime risks, and propose fixed transaction-cost assumptions for a future SPY, QQQ, and IWM strategy card. Do not backtest or optimize.

## Live Research Run

- Run ID: `RUN-rsi-exit-live-v5`
- Discovery router: Agent Reach / upstream web search
- Evidence worker attempts:
- qwen3:14b: False
- qwen3:14b: False
- qwen3.8:27b: True

## Scout Decision

rejected

## Required JSON Block

```json
{
  "research_id": "RQ-dd7da469",
  "status": "raw_saved",
  "sources": [
    {
      "title": "Swing Trading ETFs Strategy | Best 1-Week Plays",
      "source_type": "discovery-only",
      "source_quality": "discovery-only",
      "main_claim": "Proposes a 2-5 day swing trading window with a 1% trailing stop exit rule for liquid ETFs like SPY, QQQ, and IWM.",
      "possible_strategy_rule": "",
      "risks": [
        "Discovery-only source cannot independently support a durable strategy rule.",
        "The 2-5 day holding period is a general guideline, not a fixed maximum, and may not align with RSI oversold mean-reversion dynamics."
      ],
      "confidence": "low",
      "asset_classes": [
        "SPY",
        "QQQ",
        "IWM"
      ],
      "data_required": [
        "Daily OHLCV",
        "RSI(14)"
      ],
      "data_access": "not-realistic",
      "mvp_testable": false,
      "url_or_citation": "https://www.alphaexcapital.com/etfs/etf-investing-strategies/short-term-trading-and-tactical-etf-strategies/swing-trading-etfs-strategy",
      "evidence": "swing trading etfs over a 2-5 day window can be surprisingly effective"
    },
    {
      "title": "RSI Trading Strategy 2026: Settings, Entries, Exits ...",
      "source_type": "discovery-only",
      "source_quality": "discovery-only",
      "main_claim": "Explains RSI mechanics and suggests using RSI as a context filter rather than a standalone trigger, noting that in strong trends RSI can stay oversold for extended periods.",
      "possible_strategy_rule": "",
      "risks": [
        "Discovery-only source cannot independently support a durable strategy rule.",
        "Does not provide specific exit conditions or maximum holding periods for a daily ETF RSI oversold entry strategy."
      ],
      "confidence": "low",
      "asset_classes": [
        "General"
      ],
      "data_required": [
        "RSI(14)"
      ],
      "data_access": "not-realistic",
      "mvp_testable": false,
      "url_or_citation": "https://www.tradewink.com/learn/rsi-trading-strategy-guide",
      "evidence": "in strong trends, RSI can stay overbought or oversold for extended periods"
    },
    {
      "title": "RSI-25 ETF Strategy: Mean Reversion for Exchange-Traded Funds",
      "source_type": "discovery-only",
      "source_quality": "discovery-only",
      "main_claim": "Describes the RSI-25 strategy for ETFs with an exit when 4-period RSI rises above 55 and an average holding period of 3-7 days.",
      "possible_strategy_rule": "",
      "risks": [
        "Discovery-only source cannot independently support a durable strategy rule.",
        "The strategy uses a 4-period RSI, which differs from the daily RSI oversold entry specified in the research question (typically 14-period).",
        "The 3-7 day holding period is an average, not a fixed maximum."
      ],
      "confidence": "low",
      "asset_classes": [
        "SPY",
        "QQQ",
        "IWM"
      ],
      "data_required": [
        "Daily OHLCV",
        "RSI(4)",
        "200-SMA"
      ],
      "data_access": "not-realistic",
      "mvp_testable": false,
      "url_or_citation": "https://swingfolio.com/education/level-6-advanced-strategies/rsi-25-strategy-etfs",
      "evidence": "Exit when 4-period RSI rises above 55; optional scale-in if RSI drops below 20"
    }
  ],
  "open_questions": [
    "No source provides a fixed maximum holding period for a daily RSI(14) oversold entry strategy.",
    "No source provides a simple non-optimized exit condition specifically for daily RSI(14) oversold entries on SPY, QQQ, and IWM.",
    "No source provides fixed transaction-cost assumptions for a future SPY, QQQ, and IWM strategy card."
  ],
  "curator_recommendation": "rejected"
}
```


---
id: RQ-4ddd4ef4
type: raw_research
status: raw_saved
method_family: mean_reversion
assigned_agent: research_scout
---

# Raw Research Note — RQ-4ddd4ef4

## Research Question

Find useful sources for ETF mean reversion strategies and summarize only methods that can be tested with daily SPY QQQ IWM data

## Scout Prompt

# Research Scout Task

You are the Research Scout for Quant Agent Brain.

## Research ID

RQ-4ddd4ef4

## Research Question

Find useful sources for ETF mean reversion strategies and summarize only methods that can be tested with daily SPY QQQ IWM data

## Method Family

mean_reversion

## Mission

Find useful sources that answer the research question. Prioritize books, papers, reputable blogs, public repos, official documentation, credible practitioner writeups, and user-provided files.

## Hard Boundaries

- Do not create strategy cards.
- Do not run backtests.
- Do not paper trade or live trade.
- Do not claim a strategy works just because a source says so.
- Do not illegally download copyrighted books.
- Save messy findings under `brain/00_Inbox` only.

## What To Extract

For each source, separate:

1. Source URL / citation.
2. Main claim.
3. Evidence quote or exact passage when available.
4. Possible testable strategy rule.
5. Required data.
6. Risks and caveats.
7. Confidence: low / medium / high.
8. Whether this can be tested with current MVP data: daily SPY, QQQ, IWM.

## Required JSON Block

At the end of the raw note, include a fenced JSON block exactly like this shape:

```json
{
  "research_id": "RQ-4ddd4ef4",
  "status": "raw_saved",
  "sources": [
    {
      "title": "",
      "source_type": "book|paper|blog|repo|docs|other",
      "url_or_citation": "",
      "main_claim": "",
      "evidence": "",
      "possible_strategy_rule": "",
      "risks": [],
      "confidence": "low|medium|high",
      "mvp_testable": true
    }
  ],
  "open_questions": [],
  "curator_recommendation": "promote_source|update_door|create_strategy_card|needs_more_work|rejected"
}
```

## Output Location

Write raw findings to `brain/00_Inbox/Raw_Research/RQ-4ddd4ef4.md`.


## Paste / Agent Findings

## Scout Findings

This first Research Scout executor is intentionally conservative: it gathers a small, reviewable source set instead of flooding the brain with hundreds of links.

### Source 1: Relative Strength Index (RSI) — Investopedia overview

- Source URL / citation: https://www.investopedia.com/terms/r/rsi.asp
- Source type: web
- Main claim: RSI is a momentum oscillator commonly used to identify overbought or oversold conditions.
- Evidence: Use as a plain-English source for RSI definition; verify exact formula and claims before final citation.
- Possible strategy rule: For an exploratory ETF mean-reversion test: define oversold using RSI below a threshold, then enter on the next bar rather than the same close.
- Risks / caveats:
  - RSI oversold can stay oversold during strong downtrends.
  - Indicator definitions are not a trading edge by themselves.
- Confidence: medium
- MVP testable with daily SPY/QQQ/IWM data: true

### Source 2: QuantConnect glossary — Look-Ahead Bias

- Source URL / citation: https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/glossary#Look-Ahead-Bias
- Source type: docs
- Main claim: Backtests must avoid using information that would not have been available at the time of the simulated trade.
- Evidence: Use as bias-control source; exact quote should be captured during curation.
- Possible strategy rule: Close-based signals should normally enter no earlier than the next bar in the MVP backtester.
- Risks / caveats:
  - If this is ignored, a strategy can appear profitable only because it cheats with future data.
- Confidence: high
- MVP testable with daily SPY/QQQ/IWM data: true

### Source 3: QuantConnect glossary — Survivorship Bias

- Source URL / citation: https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/glossary#Survivorship-Bias
- Source type: docs
- Main claim: Universe selection can be biased if the backtest only includes assets that survived until today.
- Evidence: Use as validation-control source; exact quote should be captured during curation.
- Possible strategy rule: The first MVP should use fixed broad ETFs and explicitly label that this avoids stock-selection survivorship questions but does not prove broad market edge.
- Risks / caveats:
  - Stock-picking strategies need survivorship-bias-aware datasets later.
- Confidence: high
- MVP testable with daily SPY/QQQ/IWM data: true

### Source 4: backtesting.py documentation

- Source URL / citation: https://kernc.github.io/backtesting.py/
- Source type: docs
- Main claim: backtesting.py is a small Python framework for testing trading strategies with features such as commissions, statistics, and plotting.
- Evidence: Use as tooling source for the first readable event-style MVP backtests.
- Possible strategy rule: Implement first strategy classes in backtesting.py after research and strategy-card stages are complete.
- Risks / caveats:
  - Framework convenience does not prevent bad signal timing, bad data, or overfitting.
- Confidence: medium
- MVP testable with daily SPY/QQQ/IWM data: true

### Source 5: vectorbt documentation

- Source URL / citation: https://vectorbt.dev/
- Source type: docs
- Main claim: vectorbt is useful for fast vectorized research and parameter sweeps over pandas/NumPy data.
- Evidence: Use as tooling source for fast exploration, not as proof of edge.
- Possible strategy rule: Use vectorbt later to compare parameter regions, then validate promising settings in a more explicit backtest.
- Risks / caveats:
  - Large parameter sweeps can create data-mining bias.
  - Vectorized tests can hide execution timing mistakes if signals are not shifted correctly.
- Confidence: medium
- MVP testable with daily SPY/QQQ/IWM data: true

### Source 6: Ernest P. Chan — Algorithmic Trading book

- Source URL / citation: Chan, Ernest P. Algorithmic Trading: Winning Strategies and Their Rationale. Wiley, 2013.
- Source type: book
- Main claim: A practitioner book commonly used for learning systematic strategy research, including mean-reversion and momentum concepts.
- Evidence: Book citation only; use user-owned copy or legal preview/notes for exact quotes.
- Possible strategy rule: Use as background reading, but do not promote any specific rule unless exact evidence is captured from an accessible copy.
- Risks / caveats:
  - Do not treat book reputation as evidence for a specific ETF strategy without a sourced passage and backtest.
- Confidence: medium
- MVP testable with daily SPY/QQQ/IWM data: false

## Required JSON Block

```json
{
  "research_id": "RQ-4ddd4ef4",
  "status": "raw_saved",
  "sources": [
    {
      "title": "Relative Strength Index (RSI) \u2014 Investopedia overview",
      "source_type": "web",
      "url_or_citation": "https://www.investopedia.com/terms/r/rsi.asp",
      "main_claim": "RSI is a momentum oscillator commonly used to identify overbought or oversold conditions.",
      "evidence": "Use as a plain-English source for RSI definition; verify exact formula and claims before final citation.",
      "possible_strategy_rule": "For an exploratory ETF mean-reversion test: define oversold using RSI below a threshold, then enter on the next bar rather than the same close.",
      "risks": [
        "RSI oversold can stay oversold during strong downtrends.",
        "Indicator definitions are not a trading edge by themselves."
      ],
      "confidence": "medium",
      "mvp_testable": true
    },
    {
      "title": "QuantConnect glossary \u2014 Look-Ahead Bias",
      "source_type": "docs",
      "url_or_citation": "https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/glossary#Look-Ahead-Bias",
      "main_claim": "Backtests must avoid using information that would not have been available at the time of the simulated trade.",
      "evidence": "Use as bias-control source; exact quote should be captured during curation.",
      "possible_strategy_rule": "Close-based signals should normally enter no earlier than the next bar in the MVP backtester.",
      "risks": [
        "If this is ignored, a strategy can appear profitable only because it cheats with future data."
      ],
      "confidence": "high",
      "mvp_testable": true
    },
    {
      "title": "QuantConnect glossary \u2014 Survivorship Bias",
      "source_type": "docs",
      "url_or_citation": "https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/glossary#Survivorship-Bias",
      "main_claim": "Universe selection can be biased if the backtest only includes assets that survived until today.",
      "evidence": "Use as validation-control source; exact quote should be captured during curation.",
      "possible_strategy_rule": "The first MVP should use fixed broad ETFs and explicitly label that this avoids stock-selection survivorship questions but does not prove broad market edge.",
      "risks": [
        "Stock-picking strategies need survivorship-bias-aware datasets later."
      ],
      "confidence": "high",
      "mvp_testable": true
    },
    {
      "title": "backtesting.py documentation",
      "source_type": "docs",
      "url_or_citation": "https://kernc.github.io/backtesting.py/",
      "main_claim": "backtesting.py is a small Python framework for testing trading strategies with features such as commissions, statistics, and plotting.",
      "evidence": "Use as tooling source for the first readable event-style MVP backtests.",
      "possible_strategy_rule": "Implement first strategy classes in backtesting.py after research and strategy-card stages are complete.",
      "risks": [
        "Framework convenience does not prevent bad signal timing, bad data, or overfitting."
      ],
      "confidence": "medium",
      "mvp_testable": true
    },
    {
      "title": "vectorbt documentation",
      "source_type": "docs",
      "url_or_citation": "https://vectorbt.dev/",
      "main_claim": "vectorbt is useful for fast vectorized research and parameter sweeps over pandas/NumPy data.",
      "evidence": "Use as tooling source for fast exploration, not as proof of edge.",
      "possible_strategy_rule": "Use vectorbt later to compare parameter regions, then validate promising settings in a more explicit backtest.",
      "risks": [
        "Large parameter sweeps can create data-mining bias.",
        "Vectorized tests can hide execution timing mistakes if signals are not shifted correctly."
      ],
      "confidence": "medium",
      "mvp_testable": true
    },
    {
      "title": "Ernest P. Chan \u2014 Algorithmic Trading book",
      "source_type": "book",
      "url_or_citation": "Chan, Ernest P. Algorithmic Trading: Winning Strategies and Their Rationale. Wiley, 2013.",
      "main_claim": "A practitioner book commonly used for learning systematic strategy research, including mean-reversion and momentum concepts.",
      "evidence": "Book citation only; use user-owned copy or legal preview/notes for exact quotes.",
      "possible_strategy_rule": "Use as background reading, but do not promote any specific rule unless exact evidence is captured from an accessible copy.",
      "risks": [
        "Do not treat book reputation as evidence for a specific ETF strategy without a sourced passage and backtest."
      ],
      "confidence": "medium",
      "mvp_testable": false
    }
  ],
  "open_questions": [
    "Which exact RSI thresholds and holding period should be tested first?",
    "Which claims have exact quotes versus only high-level citation notes?",
    "Should the curator promote one source note per source or one combined source digest first?"
  ],
  "curator_recommendation": "promote_source"
}
```


## Required JSON Block

The scout must finish with the JSON block requested in the prompt.

## Scout Findings

This first Research Scout executor is intentionally conservative: it gathers a small, reviewable source set instead of flooding the brain with hundreds of links.

### Source 1: Relative Strength Index (RSI) — Investopedia overview

- Source URL / citation: https://www.investopedia.com/terms/r/rsi.asp
- Source type: web
- Main claim: RSI is a momentum oscillator commonly used to identify overbought or oversold conditions.
- Evidence: Use as a plain-English source for RSI definition; verify exact formula and claims before final citation.
- Possible strategy rule: For an exploratory ETF mean-reversion test: define oversold using RSI below a threshold, then enter on the next bar rather than the same close.
- Risks / caveats:
  - RSI oversold can stay oversold during strong downtrends.
  - Indicator definitions are not a trading edge by themselves.
- Confidence: medium
- MVP testable with daily SPY/QQQ/IWM data: true

### Source 2: QuantConnect glossary — Look-Ahead Bias

- Source URL / citation: https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/glossary#Look-Ahead-Bias
- Source type: docs
- Main claim: Backtests must avoid using information that would not have been available at the time of the simulated trade.
- Evidence: Use as bias-control source; exact quote should be captured during curation.
- Possible strategy rule: Close-based signals should normally enter no earlier than the next bar in the MVP backtester.
- Risks / caveats:
  - If this is ignored, a strategy can appear profitable only because it cheats with future data.
- Confidence: high
- MVP testable with daily SPY/QQQ/IWM data: true

### Source 3: QuantConnect glossary — Survivorship Bias

- Source URL / citation: https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/glossary#Survivorship-Bias
- Source type: docs
- Main claim: Universe selection can be biased if the backtest only includes assets that survived until today.
- Evidence: Use as validation-control source; exact quote should be captured during curation.
- Possible strategy rule: The first MVP should use fixed broad ETFs and explicitly label that this avoids stock-selection survivorship questions but does not prove broad market edge.
- Risks / caveats:
  - Stock-picking strategies need survivorship-bias-aware datasets later.
- Confidence: high
- MVP testable with daily SPY/QQQ/IWM data: true

### Source 4: backtesting.py documentation

- Source URL / citation: https://kernc.github.io/backtesting.py/
- Source type: docs
- Main claim: backtesting.py is a small Python framework for testing trading strategies with features such as commissions, statistics, and plotting.
- Evidence: Use as tooling source for the first readable event-style MVP backtests.
- Possible strategy rule: Implement first strategy classes in backtesting.py after research and strategy-card stages are complete.
- Risks / caveats:
  - Framework convenience does not prevent bad signal timing, bad data, or overfitting.
- Confidence: medium
- MVP testable with daily SPY/QQQ/IWM data: true

### Source 5: vectorbt documentation

- Source URL / citation: https://vectorbt.dev/
- Source type: docs
- Main claim: vectorbt is useful for fast vectorized research and parameter sweeps over pandas/NumPy data.
- Evidence: Use as tooling source for fast exploration, not as proof of edge.
- Possible strategy rule: Use vectorbt later to compare parameter regions, then validate promising settings in a more explicit backtest.
- Risks / caveats:
  - Large parameter sweeps can create data-mining bias.
  - Vectorized tests can hide execution timing mistakes if signals are not shifted correctly.
- Confidence: medium
- MVP testable with daily SPY/QQQ/IWM data: true

### Source 6: Ernest P. Chan — Algorithmic Trading book

- Source URL / citation: Chan, Ernest P. Algorithmic Trading: Winning Strategies and Their Rationale. Wiley, 2013.
- Source type: book
- Main claim: A practitioner book commonly used for learning systematic strategy research, including mean-reversion and momentum concepts.
- Evidence: Book citation only; use user-owned copy or legal preview/notes for exact quotes.
- Possible strategy rule: Use as background reading, but do not promote any specific rule unless exact evidence is captured from an accessible copy.
- Risks / caveats:
  - Do not treat book reputation as evidence for a specific ETF strategy without a sourced passage and backtest.
- Confidence: medium
- MVP testable with daily SPY/QQQ/IWM data: false

## Required JSON Block

```json
{
  "research_id": "RQ-4ddd4ef4",
  "status": "raw_saved",
  "sources": [
    {
      "title": "Relative Strength Index (RSI) \u2014 Investopedia overview",
      "source_type": "web",
      "url_or_citation": "https://www.investopedia.com/terms/r/rsi.asp",
      "main_claim": "RSI is a momentum oscillator commonly used to identify overbought or oversold conditions.",
      "evidence": "Use as a plain-English source for RSI definition; verify exact formula and claims before final citation.",
      "possible_strategy_rule": "For an exploratory ETF mean-reversion test: define oversold using RSI below a threshold, then enter on the next bar rather than the same close.",
      "risks": [
        "RSI oversold can stay oversold during strong downtrends.",
        "Indicator definitions are not a trading edge by themselves."
      ],
      "confidence": "medium",
      "source_quality": "practitioner",
      "mvp_testable": true
    },
    {
      "title": "QuantConnect glossary \u2014 Look-Ahead Bias",
      "source_type": "docs",
      "url_or_citation": "https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/glossary#Look-Ahead-Bias",
      "main_claim": "Backtests must avoid using information that would not have been available at the time of the simulated trade.",
      "evidence": "Use as bias-control source; exact quote should be captured during curation.",
      "possible_strategy_rule": "Close-based signals should normally enter no earlier than the next bar in the MVP backtester.",
      "risks": [
        "If this is ignored, a strategy can appear profitable only because it cheats with future data."
      ],
      "confidence": "high",
      "source_quality": "primary",
      "mvp_testable": true
    },
    {
      "title": "QuantConnect glossary \u2014 Survivorship Bias",
      "source_type": "docs",
      "url_or_citation": "https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/glossary#Survivorship-Bias",
      "main_claim": "Universe selection can be biased if the backtest only includes assets that survived until today.",
      "evidence": "Use as validation-control source; exact quote should be captured during curation.",
      "possible_strategy_rule": "The first MVP should use fixed broad ETFs and explicitly label that this avoids stock-selection survivorship questions but does not prove broad market edge.",
      "risks": [
        "Stock-picking strategies need survivorship-bias-aware datasets later."
      ],
      "confidence": "high",
      "source_quality": "primary",
      "mvp_testable": true
    },
    {
      "title": "backtesting.py documentation",
      "source_type": "docs",
      "url_or_citation": "https://kernc.github.io/backtesting.py/",
      "main_claim": "backtesting.py is a small Python framework for testing trading strategies with features such as commissions, statistics, and plotting.",
      "evidence": "Use as tooling source for the first readable event-style MVP backtests.",
      "possible_strategy_rule": "Implement first strategy classes in backtesting.py after research and strategy-card stages are complete.",
      "risks": [
        "Framework convenience does not prevent bad signal timing, bad data, or overfitting."
      ],
      "confidence": "medium",
      "source_quality": "primary",
      "mvp_testable": true
    },
    {
      "title": "vectorbt documentation",
      "source_type": "docs",
      "url_or_citation": "https://vectorbt.dev/",
      "main_claim": "vectorbt is useful for fast vectorized research and parameter sweeps over pandas/NumPy data.",
      "evidence": "Use as tooling source for fast exploration, not as proof of edge.",
      "possible_strategy_rule": "Use vectorbt later to compare parameter regions, then validate promising settings in a more explicit backtest.",
      "risks": [
        "Large parameter sweeps can create data-mining bias.",
        "Vectorized tests can hide execution timing mistakes if signals are not shifted correctly."
      ],
      "confidence": "medium",
      "source_quality": "primary",
      "mvp_testable": true
    },
    {
      "title": "Ernest P. Chan \u2014 Algorithmic Trading book",
      "source_type": "book",
      "url_or_citation": "Chan, Ernest P. Algorithmic Trading: Winning Strategies and Their Rationale. Wiley, 2013.",
      "main_claim": "A practitioner book commonly used for learning systematic strategy research, including mean-reversion and momentum concepts.",
      "evidence": "Book citation only; use user-owned copy or legal preview/notes for exact quotes.",
      "possible_strategy_rule": "Use as background reading, but do not promote any specific rule unless exact evidence is captured from an accessible copy.",
      "risks": [
        "Do not treat book reputation as evidence for a specific ETF strategy without a sourced passage and backtest."
      ],
      "confidence": "medium",
      "source_quality": "practitioner",
      "mvp_testable": false
    }
  ],
  "open_questions": [
    "Which exact RSI thresholds and holding period should be tested first?",
    "Which claims have exact quotes versus only high-level citation notes?",
    "Should the curator promote one source note per source or one combined source digest first?"
  ],
  "curator_recommendation": "promote_source"
}
```

## Scout Findings

This first Research Scout executor is intentionally conservative: it gathers a small, reviewable source set instead of flooding the brain with hundreds of links.

### Source 1: Relative Strength Index (RSI) — Investopedia overview

- Source URL / citation: https://www.investopedia.com/terms/r/rsi.asp
- Source type: web
- Main claim: RSI is a momentum oscillator commonly used to identify overbought or oversold conditions.
- Evidence: Use as a plain-English source for RSI definition; verify exact formula and claims before final citation.
- Possible strategy rule: For an exploratory ETF mean-reversion test: define oversold using RSI below a threshold, then enter on the next bar rather than the same close.
- Risks / caveats:
  - RSI oversold can stay oversold during strong downtrends.
  - Indicator definitions are not a trading edge by themselves.
- Confidence: medium
- MVP testable with daily SPY/QQQ/IWM data: true

### Source 2: QuantConnect glossary — Look-Ahead Bias

- Source URL / citation: https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/glossary#Look-Ahead-Bias
- Source type: docs
- Main claim: Backtests must avoid using information that would not have been available at the time of the simulated trade.
- Evidence: Use as bias-control source; exact quote should be captured during curation.
- Possible strategy rule: Close-based signals should normally enter no earlier than the next bar in the MVP backtester.
- Risks / caveats:
  - If this is ignored, a strategy can appear profitable only because it cheats with future data.
- Confidence: high
- MVP testable with daily SPY/QQQ/IWM data: true

### Source 3: QuantConnect glossary — Survivorship Bias

- Source URL / citation: https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/glossary#Survivorship-Bias
- Source type: docs
- Main claim: Universe selection can be biased if the backtest only includes assets that survived until today.
- Evidence: Use as validation-control source; exact quote should be captured during curation.
- Possible strategy rule: The first MVP should use fixed broad ETFs and explicitly label that this avoids stock-selection survivorship questions but does not prove broad market edge.
- Risks / caveats:
  - Stock-picking strategies need survivorship-bias-aware datasets later.
- Confidence: high
- MVP testable with daily SPY/QQQ/IWM data: true

### Source 4: backtesting.py documentation

- Source URL / citation: https://kernc.github.io/backtesting.py/
- Source type: docs
- Main claim: backtesting.py is a small Python framework for testing trading strategies with features such as commissions, statistics, and plotting.
- Evidence: Use as tooling source for the first readable event-style MVP backtests.
- Possible strategy rule: Implement first strategy classes in backtesting.py after research and strategy-card stages are complete.
- Risks / caveats:
  - Framework convenience does not prevent bad signal timing, bad data, or overfitting.
- Confidence: medium
- MVP testable with daily SPY/QQQ/IWM data: true

### Source 5: vectorbt documentation

- Source URL / citation: https://vectorbt.dev/
- Source type: docs
- Main claim: vectorbt is useful for fast vectorized research and parameter sweeps over pandas/NumPy data.
- Evidence: Use as tooling source for fast exploration, not as proof of edge.
- Possible strategy rule: Use vectorbt later to compare parameter regions, then validate promising settings in a more explicit backtest.
- Risks / caveats:
  - Large parameter sweeps can create data-mining bias.
  - Vectorized tests can hide execution timing mistakes if signals are not shifted correctly.
- Confidence: medium
- MVP testable with daily SPY/QQQ/IWM data: true

### Source 6: Ernest P. Chan — Algorithmic Trading book

- Source URL / citation: Chan, Ernest P. Algorithmic Trading: Winning Strategies and Their Rationale. Wiley, 2013.
- Source type: book
- Main claim: A practitioner book commonly used for learning systematic strategy research, including mean-reversion and momentum concepts.
- Evidence: Book citation only; use user-owned copy or legal preview/notes for exact quotes.
- Possible strategy rule: Use as background reading, but do not promote any specific rule unless exact evidence is captured from an accessible copy.
- Risks / caveats:
  - Do not treat book reputation as evidence for a specific ETF strategy without a sourced passage and backtest.
- Confidence: medium
- MVP testable with daily SPY/QQQ/IWM data: false

## Required JSON Block

```json
{
  "research_id": "RQ-4ddd4ef4",
  "status": "raw_saved",
  "sources": [
    {
      "title": "Relative Strength Index (RSI) \u2014 Investopedia overview",
      "source_type": "web",
      "url_or_citation": "https://www.investopedia.com/terms/r/rsi.asp",
      "main_claim": "RSI is a momentum oscillator commonly used to identify overbought or oversold conditions.",
      "evidence": "Use as a plain-English source for RSI definition; verify exact formula and claims before final citation.",
      "possible_strategy_rule": "For an exploratory ETF mean-reversion test: define oversold using RSI below a threshold, then enter on the next bar rather than the same close.",
      "risks": [
        "RSI oversold can stay oversold during strong downtrends.",
        "Indicator definitions are not a trading edge by themselves."
      ],
      "confidence": "medium",
      "source_quality": "practitioner",
      "mvp_testable": true
    },
    {
      "title": "QuantConnect glossary \u2014 Look-Ahead Bias",
      "source_type": "docs",
      "url_or_citation": "https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/glossary#Look-Ahead-Bias",
      "main_claim": "Backtests must avoid using information that would not have been available at the time of the simulated trade.",
      "evidence": "Use as bias-control source; exact quote should be captured during curation.",
      "possible_strategy_rule": "Close-based signals should normally enter no earlier than the next bar in the MVP backtester.",
      "risks": [
        "If this is ignored, a strategy can appear profitable only because it cheats with future data."
      ],
      "confidence": "high",
      "source_quality": "primary",
      "mvp_testable": true
    },
    {
      "title": "QuantConnect glossary \u2014 Survivorship Bias",
      "source_type": "docs",
      "url_or_citation": "https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/glossary#Survivorship-Bias",
      "main_claim": "Universe selection can be biased if the backtest only includes assets that survived until today.",
      "evidence": "Use as validation-control source; exact quote should be captured during curation.",
      "possible_strategy_rule": "The first MVP should use fixed broad ETFs and explicitly label that this avoids stock-selection survivorship questions but does not prove broad market edge.",
      "risks": [
        "Stock-picking strategies need survivorship-bias-aware datasets later."
      ],
      "confidence": "high",
      "source_quality": "primary",
      "mvp_testable": true
    },
    {
      "title": "backtesting.py documentation",
      "source_type": "docs",
      "url_or_citation": "https://kernc.github.io/backtesting.py/",
      "main_claim": "backtesting.py is a small Python framework for testing trading strategies with features such as commissions, statistics, and plotting.",
      "evidence": "Use as tooling source for the first readable event-style MVP backtests.",
      "possible_strategy_rule": "Implement first strategy classes in backtesting.py after research and strategy-card stages are complete.",
      "risks": [
        "Framework convenience does not prevent bad signal timing, bad data, or overfitting."
      ],
      "confidence": "medium",
      "source_quality": "primary",
      "mvp_testable": true
    },
    {
      "title": "vectorbt documentation",
      "source_type": "docs",
      "url_or_citation": "https://vectorbt.dev/",
      "main_claim": "vectorbt is useful for fast vectorized research and parameter sweeps over pandas/NumPy data.",
      "evidence": "Use as tooling source for fast exploration, not as proof of edge.",
      "possible_strategy_rule": "Use vectorbt later to compare parameter regions, then validate promising settings in a more explicit backtest.",
      "risks": [
        "Large parameter sweeps can create data-mining bias.",
        "Vectorized tests can hide execution timing mistakes if signals are not shifted correctly."
      ],
      "confidence": "medium",
      "source_quality": "primary",
      "mvp_testable": true
    },
    {
      "title": "Ernest P. Chan \u2014 Algorithmic Trading book",
      "source_type": "book",
      "url_or_citation": "Chan, Ernest P. Algorithmic Trading: Winning Strategies and Their Rationale. Wiley, 2013.",
      "main_claim": "A practitioner book commonly used for learning systematic strategy research, including mean-reversion and momentum concepts.",
      "evidence": "Book citation only; use user-owned copy or legal preview/notes for exact quotes.",
      "possible_strategy_rule": "Use as background reading, but do not promote any specific rule unless exact evidence is captured from an accessible copy.",
      "risks": [
        "Do not treat book reputation as evidence for a specific ETF strategy without a sourced passage and backtest."
      ],
      "confidence": "medium",
      "source_quality": "practitioner",
      "mvp_testable": false
    }
  ],
  "open_questions": [
    "Which exact RSI thresholds and holding period should be tested first?",
    "Which claims have exact quotes versus only high-level citation notes?",
    "Should the curator promote one source note per source or one combined source digest first?"
  ],
  "curator_recommendation": "promote_source"
}
```

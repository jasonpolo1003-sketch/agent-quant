# Quant Agent Brain

A budget-first side project for agent-assisted quantitative strategy research.

## Goal

Build a shared second brain where agents can:

1. Research trading/quant strategy ideas from cited sources.
2. Turn messy research into structured strategy cards.
3. Backtest strategies with real historical data.
4. Review results for lookahead bias, overfitting, costs, and bad assumptions.
5. Promote only reviewed candidates to paper trading later.

## MVP Scope

Start small:

- Market: US ETFs only
- Symbols: SPY, QQQ, IWM
- Timeframe: daily bars only
- Data: yfinance first, Stooq cross-check later
- Strategy families: mean reversion and trend following
- Paper trading: later
- Live trading: disabled

## Core Rule

Agents should not read the whole brain. They should retrieve only the few relevant notes/chunks needed for the current task, cite sources, and write structured outputs back.

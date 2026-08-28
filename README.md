# Quant Agent Brain

Budget-first agent-assisted quantitative research, second-brain, and backtesting system.

## Scope

- Research universe is cross-asset: equities/ETFs, futures, rates, FX, commodities, options, crypto, market microstructure, alternative data, and portfolio research.
- Current tracer implementation uses daily SPY, QQQ, and IWM data to prove the research-to-backtest pipeline cheaply.
- A market enters implementation only after provenance, source quality, data feasibility, instrument-specific risks, and testability are documented.
- Research before strategy creation.
- Frozen strategy cards before backtesting.
- Backtesting and adversarial review before paper trading.
- No live trading.
- Agent Reach (`https://github.com/Panniantong/Agent-Reach`) is the preferred live-discovery router; durable notes cite upstream sources.

## Core Loop

Research queue -> raw brief -> source note -> method door -> strategy card -> backtest -> review -> paper candidate later.

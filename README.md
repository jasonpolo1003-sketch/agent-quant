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

The canonical production path is registry/dispatcher -> `quant_brain.discovery` ->
validated output -> recommendation only. The harness or a human authorizes any later stage.

## Preserved Experimental Local Work

The following commands belong to an unaccepted live-research/dashboard prototype retained
for audit history. They are not the production interface or Scout acceptance path.

```bash
# Experimental dashboard
uv run python scripts/serve_agent_dashboard.py

# Experimental live-research prototype
uv run python scripts/live_research_executor.py --research-id RQ-xxxx --run-id RUN-name
```

Experimental dashboard URL: `http://127.0.0.1:8765`

## Data notice

This product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis.

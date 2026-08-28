# Agent Rules for Quant Agent Brain

These rules apply to every AI agent working in this project.

## Safety

- Do not place live trades.
- Do not suggest that a backtest proves future profits.
- Do not promote a strategy to paper trading without a review note.
- Do not use paid APIs/models unless the task explicitly allows escalation.

## Research Rules

- Every durable claim needs a source URL, book/paper citation, or clear `unverified` label.
- Save raw messy findings in `brain/00_Inbox/` first.
- Convert only useful findings into structured source notes or strategy cards.
- Do not download copyrighted books illegally. Use legal/free sources, public papers, docs, repos, previews, or user-provided files.

## Backtesting Rules

- Always shift close-based signals to the next bar.
- Always include transaction cost/slippage assumptions.
- Always compare against a benchmark.
- Track data source, date range, symbols, parameters, and code version.
- Reject strategies that only work after repeated tuning.

## Write Locations

- Raw findings: `brain/00_Inbox/`
- Sources: `brain/01_Sources/`
- Strategy family doors: `brain/02_Strategy_Doors/`
- Strategy cards: `brain/03_Strategy_Cards/`
- Backtest reports: `brain/04_Backtest_Reports/`
- Review notes: `brain/05_Reviews/`
- Paper trading notes: `brain/06_Paper_Trading/`
- Decision logs: `brain/07_Decision_Log/`

## Model Budget

Use local/cheap models first:

- `qwen3:8b` for quick research/classification
- `qwen3:14b` for local reasoning
- `qwen2.5-coder:14b` for code/backtest help

Escalate to Claude/Codex/GPT only when local work fails objective checks or needs final review.

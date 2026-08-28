# Agent Rules for Quant Agent Brain

## System Principle

Agents do not read the whole brain. They receive specific task briefs and retrieve only relevant notes/chunks.

## Safety

- Do not place live trades.
- Do not claim a backtest proves future profit.
- Do not download copyrighted books illegally.
- Do not use paid APIs/models unless escalation is explicitly allowed.

## Write Locations

- Raw findings and briefs: `brain/00_Inbox/`
- Source notes: `brain/01_Sources/`
- Method doors: `brain/02_Strategy_Doors/`
- Strategy cards: `brain/03_Strategy_Cards/`
- Backtest reports: `brain/04_Backtest_Reports/`
- Reviews: `brain/05_Reviews/`
- Paper trading: `brain/06_Paper_Trading/`
- Decisions: `brain/07_Decision_Log/`

## Research Rules

- Every durable claim needs source/provenance or `unverified`.
- Raw research lands in inbox first.
- Curated research becomes a source note.
- Strategy cards need precise testable rules before backtesting.
- The research universe is cross-asset: equities, futures, rates, FX, commodities, options, crypto, market microstructure, alternative data, and portfolio research are allowed.
- Broad discovery is not automatic promotion. Apply `brain/_system/research_source_quality_policy.md`.
- Use Agent Reach (`https://github.com/Panniantong/Agent-Reach`) for live discovery when available, but cite upstream pages, transcripts, repositories, or datasets.
- Blogs, YouTube, and social posts may create leads; durable claims need Tier A or defensible Tier B evidence.
- Reject untraceable performance claims, hidden rules, cherry-picked screenshots, and copied summaries without provenance.

## Backtest Rules

- Shift close-based signals to next bar.
- Include transaction costs/slippage.
- Compare to benchmark.
- Record exact dataset and code version.

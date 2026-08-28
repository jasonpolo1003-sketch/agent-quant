# Research Intake Workflow

This is the first improvement loop for the project.

## Purpose

The system should research deeply before creating strategy cards or writing backtests.

## Flow

```text
1. Human or manager agent adds research question.
2. System creates a research queue row.
3. System creates a research brief in brain/00_Inbox/Research_Briefs/.
4. Research Scout collects useful sources and writes raw findings.
5. Knowledge Curator reviews raw findings.
6. Good sources become source notes in brain/01_Sources/.
7. Useful patterns update method doors in brain/02_Strategy_Doors/.
8. Only clearly testable methods become strategy cards.
```

## Agent Rule

Agents should not skip directly from vague research to backtesting. A strategy must pass through:

```text
research brief -> source note -> method door -> strategy card -> backtest -> review
```

## Status Values

- `queued`: waiting for research
- `researching`: scout is working
- `raw_saved`: raw findings saved
- `curating`: curator is reviewing
- `curated`: accepted into the brain
- `rejected`: not useful or not trustworthy

## CLI Examples

Add a question and create a brief:

```bash
uv run python scripts/research_intake.py add "Find useful sources for ETF mean reversion strategies" --family mean_reversion --priority 1 --brief
```

List queue:

```bash
uv run python scripts/research_intake.py list
```

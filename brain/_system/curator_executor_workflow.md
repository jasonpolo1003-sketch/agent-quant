# Curator Executor Workflow

This is the first deterministic Knowledge Curator executor.

## Design Principle

Do not use an agent for every little step.

The executor is a simple, auditable gate:

```text
raw research JSON
  -> parse source list
  -> promote MVP-testable sources
  -> skip background-only sources
  -> write curator review
  -> record curated findings in SQLite
```

## Why This Is Not Overengineered

A real quant research process needs evidence gates, not endless agents. This executor is deliberately small:

- one raw research task at a time
- no web crawler yet
- no vector DB yet
- no autonomous strategy creation yet
- no backtest until curation passes

## Command

```bash
uv run python scripts/curator_executor.py execute --research-id RQ-xxxx
```

## Outputs

Promoted source notes:

```text
brain/01_Sources/<source_type>s/
```

Curator review:

```text
brain/00_Inbox/Curator_Reviews/RQ-xxxx-curated.md
```

Database updates:

```text
research_questions.status = curated
research_findings rows added
sources rows added
notes rows added
```

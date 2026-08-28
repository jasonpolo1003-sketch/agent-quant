# Research Scout Runner Workflow

This runner does not blindly research everything. It prepares one bounded work packet at a time.

## Why

Agents perform better when they get one clear research question, one write location, and one required output format.

## Flow

```text
research_questions table
  -> claim highest-priority queued task
  -> mark it researching
  -> build Research Scout prompt
  -> create raw note scaffold
  -> scout fills raw findings
  -> curator reviews/promotes later
```

## Command

```bash
uv run python scripts/research_scout_runner.py prepare
```

## Output

Creates:

```text
brain/00_Inbox/Raw_Research/RQ-xxxx.md
```

## Agent Contract

The scout must end with a JSON block containing:

- research_id
- status
- sources
- open_questions
- curator_recommendation

## Important

This runner prepares the task. It does not yet automate web browsing or book/PDF ingestion. That comes after the source ingestion/indexer is built.

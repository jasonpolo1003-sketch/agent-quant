# Retrieval Context Builder Workflow

The retrieval context builder turns vector search results into clean packets an agent can safely use.

## Why This Exists

Agents should not directly dump database rows into their prompt. They need a small evidence packet with:

- query
- file path
- heading
- chunk id
- score
- chunk text
- instructions to cite sources and avoid guessing

## Flow

```text
agent task question
  -> search embeddings
  -> select top chunks
  -> format context packet
  -> optionally log retrieval
  -> agent uses packet as evidence
```

## Command

```bash
uv run python scripts/build_context.py "lookahead bias future data" --limit 3 --log --agent-id curator --task-id RQ-xxxx
```

## Output

A Markdown context packet like:

```text
# Retrieved Context Packet
## Query
...
## Retrieved Chunks
### Context 1
- chunk_id
- note_id
- path
- heading
- score
chunk text
```

## Important Rule

Retrieved context is evidence, not proof. Agents must cite paths/headings and admit when the retrieved context is weak.

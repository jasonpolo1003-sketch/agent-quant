# Markdown Indexer Workflow

The Markdown indexer turns readable brain notes into database chunks that agents can retrieve later.

## Design Principle

Do not make agents read the whole brain.

Instead:

```text
Markdown files stay human-readable
SQLite notes table tracks each file
SQLite chunks table stores heading-sized sections
future retrieval picks only relevant chunks
```

## What Gets Indexed

By default it indexes Markdown files under:

```text
brain/
```

It skips:

```text
brain/_system/
```

because system templates/workflow docs should not pollute research retrieval unless explicitly included.

## Command

```bash
uv run python scripts/index_markdown.py index
```

## Database Tables Updated

```text
notes
chunks
```

## Next ML Step Later

The chunks are marked:

```text
embedding_status = pending
```

Later an embedding worker can turn them into vectors for semantic search.

# Embedding Indexer Workflow

The embedding indexer turns Markdown chunks into vectors so agents can retrieve relevant evidence before answering or editing.

## What We Are Building

Yes: this project now has both structures:

```text
research structure = queue -> scout -> raw note -> curator -> source notes
RAG structure      = markdown notes -> chunks -> embeddings -> retrieval
```

## Current Embedding Model

The first model is:

```text
local-hash-embedding-v1
```

This is intentionally simple, local, and free. It uses deterministic feature hashing instead of a paid API or heavy model download.

## Why Start This Way

A real quant/research team would first prove the data flow:

```text
can we index notes?
can we embed chunks?
can we retrieve relevant evidence?
can we cite file paths?
```

Only after that should we upgrade to a stronger semantic model.

## Later Upgrade Path

Once the plumbing is proven, swap the embedding backend to one of:

```text
sentence-transformers/all-MiniLM-L6-v2
Ollama nomic-embed-text
Ollama mxbai-embed-large
LanceDB / Chroma vector store
```

## Commands

Index markdown first:

```bash
uv run python scripts/index_markdown.py index
```

Embed pending chunks:

```bash
uv run python scripts/embed_chunks.py embed
```

Search chunks:

```bash
uv run python scripts/embed_chunks.py search "lookahead bias future data"
```

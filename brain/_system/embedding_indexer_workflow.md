# Embedding Indexer Workflow

## Purpose

Turn indexed Markdown chunks into vectors so agents can retrieve evidence by meaning rather than by shared vocabulary.

## Backends

| Model | Dimensions | Role |
|---|---|---|
| `nomic-embed-text` | 768 | **Default.** Semantic retrieval via local Ollama. |
| `local-hash-embedding-v1` | 256 | **Test-only.** Deterministic SHA-256 feature hash, offline. |

The hash backend is **lexical, not semantic**: it buckets tokens by hash, so two chunks match only when they share literal tokens. It proved the RAG plumbing cheaply and now keeps pytest hermetic — the test suite must never require Ollama or the network.

Both models coexist in the `embeddings` table. `PRIMARY KEY (chunk_id, model)` plus the `WHERE model = ? AND dimensions = ?` filter in search means switching backends is a **parameter**, not a migration.

## Measured quality (2026-08-28, 233 chunks)

| Backend | Recall@1 | Recall@5 | MRR |
|---|---|---|---|
| `nomic-embed-text` | 0.71 | **1.00** | 0.790 |
| `local-hash-embedding-v1` | 0.57 | 0.71 | 0.619 |

Fixture queries are deliberately **non-lexical** — they avoid sharing rare tokens with their target. Both hash-backend misses are exactly that case: *"can a backtest accidentally use tomorrow's information"* shares no vocabulary with "look-ahead bias", and *"when should a trade be closed"* shares none with "exit conditions". That gap is the whole reason for the swap.

Full report: `brain/00_Inbox/Model_Evaluations/retrieval-eval-2026-08-28.json`

## Commands

```bash
# Embed chunks marked pending (normal path after indexing).
uv run python scripts/embed_chunks.py embed

# Backfill a new backend across every chunk, pending or not.
uv run python scripts/embed_chunks.py embed --model nomic-embed-text --reembed-all

# Search directly.
uv run python scripts/embed_chunks.py search "lookahead bias" --limit 5

# Measure retrieval quality; --compare runs the lexical baseline too.
uv run python scripts/retrieval_eval.py --compare --save
```

## Gotchas

**Re-embedding is slow.** One HTTP call per chunk: 233 chunks took ~8.5 minutes. Batch the API call if the corpus grows substantially.

**Always follow `index_markdown.py index` with `embed_chunks.py embed`.** Indexing re-chunks and resets every chunk to `embedding_status='pending'`, dropping existing vectors.

**Dimension mismatch fails loudly.** Querying a model/width combination with no stored vectors raises with the available combinations listed, rather than silently returning zero results that look like "nothing relevant found".

**`brain/_system/` is NOT indexed.** `markdown_indexer` defaults to `exclude_dirs={"_system"}`. So the pre-backtest validation checklist, the source-quality policy, and every workflow doc — including this one — are invisible to retrieval. `index_markdown.py index --include-system` overrides it. This is an open decision: workflow docs are arguably not research evidence, but the validation checklist plausibly should be retrievable. Not changed during Phase 3 to avoid altering indexer behavior inside a RAG phase.

## Scale note

Brute-force cosine similarity in SQLite is correct at 233 chunks — a vector database would be overhead here. Revisit around ~50k chunks.

## Files

```text
src/quant_brain/indexing/embeddings.py
src/quant_brain/llm/ollama_client.py
scripts/embed_chunks.py
scripts/retrieval_eval.py
tests/test_embedding_indexer.py
tests/test_retrieval_eval.py
```

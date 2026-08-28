---
id: PHASE-03
type: plan_phase
phase: 3
title: Real semantic RAG
status: pending
created: 2026-08-28
---

# Phase 3 — Real semantic RAG

Parent plan: [../../../PLAN.md](../../../PLAN.md)

## Why this phase exists

[../../../src/quant_brain/indexing/embeddings.py](../../../src/quant_brain/indexing/embeddings.py) currently uses `local-hash-embedding-v1`: a SHA-256 feature-hash into 256 dimensions, one bucket per token, ±1 sign, then L2 normalize.

That is **not semantic**. Two chunks match only when they literally share tokens. A query like *"how long should I hold a mean-reversion trade"* will not retrieve a chunk that says *"maximum holding period of five sessions"* — no shared rare tokens. Cosine similarity over a bag of hashed tokens is a lexical overlap score wearing a vector costume.

The docstring in that file is honest about this — it says "good enough to test the RAG plumbing before swapping in a semantic model." The plumbing is now proven. This phase does the swap.

**This phase must land before Phase 6.** The Research Scout's work packets carry retrieved context into Qwen. Garbage retrieval → garbage evidence → wasted local-LLM cycles and a validator that rejects everything.

## Entry gate

Phase 0 complete (test suite green). Independent of Phases 1-2 — may run in parallel with them.

## Exit gate

- All existing tests still green.
- A new evaluation script reports **Recall@5 ≥ 0.8** on a small hand-labeled fixture set, and beats the hash baseline on the same set.
- Every chunk in `db/brain.sqlite` is re-embedded with the new model and `chunks.embedding_model` reflects it.

## Design

### Model choice

**Primary: Ollama `nomic-embed-text`.**
- 768 dimensions, runs locally, free, fast on an RTX 5070.
- Consistent with §9 of PLAN.md (local-first) and with the already-planned Ollama dependency in Phase 5 — one runtime serves both.
- Pull with `ollama pull nomic-embed-text`.

**Fallback: `sentence-transformers/all-MiniLM-L6-v2`** (384-dim) via the `rag` optional dependency group already declared in `pyproject.toml`. Use if Ollama proves unreliable for batch embedding.

**Keep `local-hash-embedding-v1`** as a registered backend named `test-only`. pytest must never require Ollama.

### Backend abstraction

Keep it small. A dict of named embedder callables is enough — do not build a plugin system.

```python
# src/quant_brain/indexing/embeddings.py
EMBEDDING_BACKENDS = {
    "local-hash-embedding-v1": (hash_embed_text, 256),      # test-only
    "nomic-embed-text": (ollama_embed_text, 768),           # default
}
DEFAULT_MODEL = "nomic-embed-text"
```

The existing schema already stores `model` and `dimensions` per embedding row and has `PRIMARY KEY (chunk_id, model)` — so **both** models can coexist in the table. That is deliberate: it lets the eval script compare them without a re-index dance.

`search_similar_chunks` already filters on `WHERE e.model = ? AND e.dimensions = ?`. Keep that. It means switching models is a parameter, not a migration.

### Re-embedding

`embed_pending_chunks` only picks up `embedding_status = 'pending'`. To re-embed everything under a new model, add a `--reembed-all` flag that ignores status and upserts for the given model (the `ON CONFLICT(chunk_id, model) DO UPDATE` clause already handles it).

Do not delete the hash vectors. They cost nothing and the eval script wants them.

### Chunking — check before changing

The current chunker is heading-based ([markdown_indexer.py](../../../src/quant_brain/indexing/markdown_indexer.py)), producing 233 chunks from 21 files (~11 per file). Before touching chunk strategy, **measure**: if Recall@5 hits the exit gate with heading chunks, leave it alone. Only if retrieval underperforms should you consider a token-window chunker with overlap. Do not preemptively rewrite the chunker.

## Evaluation harness

Create `scripts/retrieval_eval.py` + a fixture file.

Fixtures: 5-8 hand-written queries paired with the note path that *should* be the top hit. Draw from what is actually in the brain right now:

| query (paraphrased, NOT lexically matching) | expected note |
|---|---|
| "can a backtest accidentally use tomorrow's information" | `SRC-2830f8cd41-quantconnect-glossary-look-ahead-bias.md` |
| "why do only the winners show up in my stock list" | `SRC-7691c731ac-quantconnect-glossary-survivorship-bias.md` |
| "how is the RSI formula actually calculated" | `SRC-1ea110cb46-stockcharts-...-rsi.md` or the TA-Lib note |
| "library for fast parameter sweeps over price data" | `SRC-022c5bed68-vectorbt-documentation.md` |
| "what should I check before trusting a backtest result" | `pre_backtest_validation_checklist.md` |

**The queries must be deliberately non-lexical** — that is the whole point. If a query shares rare tokens with the target chunk, the hash baseline will pass it too and the eval proves nothing.

Report per-model: Recall@1, Recall@5, MRR. Print a small table. Store the run output under `brain/00_Inbox/Model_Evaluations/retrieval-eval-{date}.json` alongside the existing Qwen evals.

## Files to create/modify

| Path | Action |
|---|---|
| `src/quant_brain/indexing/embeddings.py` | modify — backend registry, Ollama embedder, `--reembed-all` |
| `src/quant_brain/llm/ollama_client.py` | create early if convenient (Phase 5 also needs it) — or inline a minimal embed call and refactor in Phase 5 |
| `scripts/retrieval_eval.py` | create |
| `tests/test_retrieval_eval.py` | create — runs eval against the **hash** backend only, so CI needs no Ollama |
| `brain/_system/embedding_indexer_workflow.md` | update — document the new default model |

## Verification steps

```bash
ollama pull nomic-embed-text
cd C:/Users/jason/OneDrive/Desktop/quant-agent-brain
uv run python scripts/embed_chunks.py embed --model nomic-embed-text --reembed-all
uv run python scripts/retrieval_eval.py --compare
uv run python scripts/build_context.py "how long should a mean reversion trade be held" --limit 3
uv run pytest -q
```

That third command is the human smoke test — the returned chunks should be *about* holding periods, not merely share the word "mean."

## Definition of done

- [ ] `nomic-embed-text` is the default embedding backend
- [ ] Hash backend still present and used by pytest (no network/Ollama in CI)
- [ ] All chunks re-embedded; `chunks.embedding_model` updated
- [ ] `scripts/retrieval_eval.py` exists and reports Recall@1/Recall@5/MRR for both backends
- [ ] Recall@5 ≥ 0.8 on the fixture set, and semantic beats hash
- [ ] Eval output saved to `brain/00_Inbox/Model_Evaluations/`
- [ ] `PLAN.md` §10 checkpoint updated

## Do not

- Do not introduce LanceDB/Chroma yet. 233 chunks is a rounding error — brute-force cosine in SQLite is correct at this scale. Revisit past ~50k chunks.
- Do not add a reranker in this phase. Get base retrieval honest first; measure before adding a second stage.
- Do not delete the hash backend. It keeps the test suite hermetic.
- Do not rewrite the chunker without measuring first.

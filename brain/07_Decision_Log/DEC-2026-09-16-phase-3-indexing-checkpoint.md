---
id: DEC-2026-09-16-phase-3-indexing-checkpoint
type: decision
date: 2026-09-16
related_plan: PLAN-phase-3-semantic-rag
related_commit: b236175
related_pr: pending
---

# Decision — Phase 3 indexing accepted; experimental work moved to a preserve branch

## Decision

The Phase 3 indexing and retrieval-evaluation edits that were held back from the Gate B
checkpoint are **accepted** and committed to `phase-3/indexing-and-retrieval-eval`
(`b236175`), pending Jason's review of the PR. The experimental live-research and dashboard
work is **preserved** on `preserve/live-research-and-dashboard-20260916` (`7a7209e`) and is
explicitly not promoted into production.

This clears the working tree so `main` is a trustworthy baseline for Gate C.

## How the working tree was classified

| Work | Disposition | Reason |
|---|---|---|
| `indexing/markdown_indexer.py`, `indexing/embeddings.py`, `scripts/retrieval_eval.py`, `tests/test_markdown_indexer.py`, `tests/test_retrieval_eval.py` | Accepted → Phase 3 PR | Substantive, tested, correct on its own merits |
| `research/live_{discovery,executor,worker}.py`, `ops/dashboard.py`, `ui/`, 3 scripts, 4 tests | Preserved on a branch | Audit history, never reviewed in PR #2, not the accepted architecture |
| `src/quant_agent_brain.egg-info/` | Untracked + gitignored | Regenerated on every editable install; produced pure diff noise |
| `.hermes/` | Gitignored, kept on disk | Local planning scratch, not project history |

`tests/test_retrieval_eval.py` was grouped with Phase 3 rather than the experimental bucket
because it calls `evaluate(..., dimensions=64)` — a parameter that only exists in the
modified `retrieval_eval.py`.

## Why the Phase 3 changes were accepted

**Excluding `Source_Snapshots` is right.** `brain/00_Inbox/Source_Snapshots/` holds raw,
uncurated scraped pages (9 files under `RQ-66078766` and `RQ-dd7da469`). Indexing them would
let unvetted scrape text surface as retrieved evidence inside Scout work packets. AGENTS.md
requires that raw research lands in the inbox and only *curated* research becomes a durable
source note; retrieval should draw on curated notes, not the raw capture.

The same change replaces `exclude_dirs or {...}` with an explicit `is None` check, fixing a
latent bug: a caller passing `exclude_dirs=set()` to mean "exclude nothing" was silently
overridden, because an empty set is falsy.

**The removed eval fixture was unreachable, not inconvenient.** The
`pre_backtest_validation_checklist` fixture targeted a file in `brain/_system/`, which the
indexer excludes. It was never in the database, so no query could ever retrieve it — it
scored as a permanent miss that silently depressed Recall@1 and MRR. This was verified
against the live database before accepting. It was replaced with two fixtures whose targets
*are* indexed (`quant-research-universe`, `DOOR-etf-mean-reversion`). Removing an impossible
fixture is a correctness fix, not metric-gaming.

**Failing loudly on a dimension mismatch is right.** Returning an empty list reads as
"nothing relevant found" when the real cause is vectors stored at one width and a query built
at another.

## Verified result

Re-run on the real database, 7 fixtures, `nomic-embed-text`:

```
Recall@1: 0.71   Recall@5: 1.00   MRR: 0.790
```

Recall@5 still clears the Phase 3 exit gate of ≥0.8, and every fixture is now genuinely
reachable. **199 passed, 1 skipped.** Ruff clean on both invocations. `db/brain.sqlite`
SHA-256 unchanged (`43fa24b0…3069bb`) before and after all work.

## Known issue accepted, not fixed

`retrieval_eval.py --compare` does not work. It evaluates the semantic backend against the
`local-hash-embedding-v1` lexical baseline, but the hash vectors are absent from
`db/brain.sqlite` (only `nomic-embed-text@768`, 260 rows), despite the Phase 3 design note
saying to keep them for exactly this comparison. The likely cause is the documented
re-index behavior that resets chunks and drops embeddings.

This is **pre-existing, not caused by this change**. Before the dimension-mismatch error
existed it failed silently as recall 0.00, which is the worse failure. Restoring it requires
re-embedding every chunk under the hash model, which writes to the database — deliberately
not done, since database state was to remain unchanged. Documented in the module docstring.

## What remains open

`brain/_system/` indexing is **still Jason's call** and is deliberately unresolved here. The
pre-backtest validation checklist and the source-quality policy remain unretrievable. This
checkpoint narrowed the change to `Source_Snapshots` specifically so it would not quietly
settle that question.

## What this does not authorize

Gate C is not started. No research question was executed — `RQ-6d9c12f4`, `RQ-c920baeb`, and
`RQ-80be8cf7` remain `queued`. No curation, promotion, strategy card, backtest, dataset, or
paper trade. `strategy_cards`, `backtests`, `price_datasets`, and `reviews` are all zero.

The preserve branch is audit history. Promoting any of it into production requires its own
reviewed change, not a carry-over from this checkpoint.

Recovery tag for this work: `pre-phase3-checkpoint-20260916`.

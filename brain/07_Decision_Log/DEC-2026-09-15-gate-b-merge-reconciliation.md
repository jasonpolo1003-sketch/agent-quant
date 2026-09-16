---
id: DEC-2026-09-15-gate-b-merge-reconciliation
type: decision
date: 2026-09-15
related_plan: PLAN-gate-b-validated-scout
related_commit: fb3ecc339293299232b8f5c0682ac157397deb6a
related_pr: 2
---

# Decision — Gate B merged; experimental work stays out of production

## Decision

Local `main` is synchronized with the merged Gate B checkpoint (`fb3ecc3`, PR #2) by
fast-forward. Gate C-adjacent scaffolding and Phase 3 indexing edits are **preserved in the
working tree and deliberately left uncommitted**, not promoted into production.

## Why fast-forward was safe

The merge introduced no upstream edits: `git diff 8308cb3 origin/main` is empty, and the
checkpoint tip is an ancestor of the merge commit. Every locally-modified tracked file was
verified identical between the two commits before switching, so the checkout could not
alter preserved work. Confirmed afterward by SHA-256 comparison of all 21 preserved files —
byte-for-byte unchanged.

Recovery point: tag `pre-gatec-reconcile-20260915`.

## What stays out of production, and why

| Work | Status | Reason |
|---|---|---|
| `research/live_{discovery,executor,worker}.py`, `ops/dashboard.py`, `ui/`, related scripts/tests | preserved, uncommitted | Gate C-adjacent scaffolding; passes 13 tests but was excluded from PR #2 review |
| `indexing/{embeddings,markdown_indexer}.py`, `scripts/retrieval_eval.py`, `tests/test_markdown_indexer.py` | preserved, uncommitted | Substantive Phase 3 semantic-RAG work (excludes `Source_Snapshots` from indexing); belongs to Phase 3, not the Gate B checkpoint |
| `.hermes/`, `src/quant_agent_brain.egg-info/` | preserved, uncommitted | Planning notes and build metadata |

Promoting any of these requires its own reviewed change. A reconciliation is not a review.

## Verified state

- **210 passed, 1 skipped**; Ruff clean on `.` and on `src tests scripts`
- Accepted Gate A/B code byte-identical to the merged checkpoint
- Qwen ladder `qwen3:14b → qwen3.8:27b`; no cloud fallback, no retry loop
- `use_qwen` / `qwen_runner` absent from the executor signature
- Negation reversal blocked in both directions
- `RQ-6d9c12f4`, `RQ-c920baeb`, `RQ-80be8cf7` **queued and unexecuted**; `RQ-66078766` **rejected**
- `strategy_cards` / `backtests` / `price_datasets` / `reviews` = **0**

## Consequence

The repository is a clean, recoverable foundation for Gate C. Gate C was **not** started
here. Phase 6 / research acceptance remains unmet — see
[[DEC-2026-09-07-scout-experiment-not-acceptance]].

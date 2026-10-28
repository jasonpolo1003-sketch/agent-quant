---
title: Phase B research preservation checkpoint
status: preserved
promoted: false
date: 2026-10-28
---
# Phase B research preservation checkpoint

This note records what was preserved on the `testing` branch. It is a provenance/status receipt, not a strategy approval and not evidence of future profitability.

## Preserved research and plans

- Phase A was completed and merged through PR #12 (`7d00e4c5d856ffe4c79a1bfee02171baf4961ab2`); its last recorded verification was 853 passed, 1 skipped, with CI passing.
- The Grok intake reviewed 95 notes/transcripts and 46 PDFs, producing 141 catalog entries: 51 Phase B items, 33 later-research items, and 56 YouTube learning leads. One scanned PDF still required OCR at intake close.
- The curated MES/MNQ research is tracked under `brain/sources/mes_mnq/`, including contracts/roll, events, execution costs, fill models, providers, validation, venue rules, and synthesis. The tracked corpus is authoritative; the former temporary master catalog was a working index, not the source of truth.
- The independently reviewed Phase B plan is preserved at `.hermes/plans/2026-10-22-phase-b-mes-mnq-testing-foundation.md`. Its plan review outcome was Quant PASS and Engineering PASS.
- Later Phase B implementation, research, strategy cards, trial ledgers, negative findings, and reviews are preserved in their normal governed locations. The latest state remains in `SESSION_HANDOFF.md`.

## Historical B0 security status

The first B0 persistence implementation passed 892 tests with 2 skipped, but an independent review still demonstrated that replacing a run directory with a Windows junction could let `state()` / `fail()` follow the junction outside the store root. That checkpoint was rejected and was not represented as secure or complete. Later integration of futures code does not, by itself, erase that historical finding; any claim that this storage boundary is secure requires a fresh focused review against the current code.

## Boundaries

- No live trading or broker/account changes are authorized by this preservation checkpoint.
- Backtests do not prove future profits.
- Paid data actions remain approval-gated. Historical Databento activity and current data state are documented in the tracked provider manifests and `SESSION_HANDOFF.md`; this note does not authorize another purchase or download.
- Raw licensed data and copyrighted source copies remain outside Git when required by licensing or repository policy.

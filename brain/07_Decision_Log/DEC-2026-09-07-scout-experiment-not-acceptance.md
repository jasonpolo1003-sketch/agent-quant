---
id: DEC-2026-09-07-scout-experiment-not-acceptance
type: decision
date: 2026-09-07
related_research: RQ-66078766
related_run: RUN-seeded-primary-v1
related_plan: PLAN-scout-reconciliation
---

# Decision — RQ-66078766 is experimental audit, not Scout acceptance

## Decision

Treat `RQ-66078766` / `RUN-seeded-primary-v1` as an **experimental audit receipt** only.

It does **not** count as formal Research Scout acceptance.

## Why

- Combined question ran instead of the three narrowed children (`RQ-6d9c12f4`, `RQ-c920baeb`, `RQ-80be8cf7`), which remain queued.
- Path used seeded bypass + manual extract (`assigned_agent: seeded_primary_pass_plus_manual_extract`), not registered `research_scout` via dispatcher.
- Qwen fail-closed, then manual raw JSON; curator correctly rejected all sources (0 promotions). Quality gate passed; automated Scout pipeline unverified.
- Manual raw note used illegal `data_access: "partial"` relative to live schema — evidence of a curator schema hole.

## Consequences

- Keep raw note, failed-run receipt, and curator rejection on disk.
- Do not update the strategy door from this experiment.
- Next work is harness reconciliation (`brain/_system/plan/scout_reconciliation_plan.md`), not another research wave.
- Canonical snapshot folder chosen: `brain/00_Inbox/Source_Snapshots/`.

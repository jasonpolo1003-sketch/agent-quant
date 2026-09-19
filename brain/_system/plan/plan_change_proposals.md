---
id: PLAN-CHANGES
type: plan_change_log
status: active
created: 2026-08-28
---

# Plan Change Proposals

Parent plan: [../../../PLAN.md](../../../PLAN.md)

## How this file works

`PLAN.md` is the source of truth. **Agents do not silently rewrite it.**

If you are an agent working on this project and you believe the plan is wrong — a phase is in the wrong order, a design will not work, a constraint is counterproductive, a dependency is missing — **write your case here and stop**. Jason approves plan changes.

This exists because the project's core design rule is *move slowly, one verified step at a time*. A plan that any agent can quietly rewrite mid-run is not a plan.

### What counts as a plan change (propose it here)

- Reordering, adding, splitting, or removing a phase
- Changing a model choice in PLAN.md §8
- Changing the Agent Reach usage contract in PLAN.md §7
- Relaxing a hard cap (5 sources, 1 repair, no cloud fallback, no live trading)
- Changing an exit gate or definition of done

### What does not need a proposal (just do it)

- Implementation details inside a phase that the phase doc left open
- Fixing a bug in code you are writing
- Adding a test
- Correcting a factual error in a doc (e.g. a wrong file path) — fix it and note it below

## Proposal template

```markdown
### PROP-NNN — <short title>
- **Date:** YYYY-MM-DD
- **Proposed by:** <agent / session>
- **Affects:** <PLAN.md section or phase doc>
- **Current plan says:** <quote it>
- **Problem:** <what breaks, or what is now known that was not known when the plan was written>
- **Proposed change:** <specific>
- **Cost of not changing:** <what happens if we proceed as planned>
- **Status:** proposed | accepted | rejected
- **Jason's decision:** <filled in by Jason>
```

---

## Proposals

### PROP-001 — Canonical snapshot folder is Source_Snapshots
- **Date:** 2026-09-07
- **Proposed by:** scout reconciliation R1–R3
- **Affects:** PLAN.md Phase 4 deliverables line; phase table is unchanged
- **Current plan says:** snapshots to `brain/00_Inbox/Snapshots/`
- **Problem:** Jason approved `brain/00_Inbox/Source_Snapshots/` as the canonical snapshot folder. The registry, live snapshot writer, and tests now use that path. PLAN.md still names `Snapshots/`.
- **Proposed change:** When PLAN.md is next edited, replace `brain/00_Inbox/Snapshots/` with `brain/00_Inbox/Source_Snapshots/` in the Phase 4 deliverables sentence. Do not reorder phases or change exit gates.
- **Cost of not changing:** the master plan disagrees with the approved canonical path and with `agents/research_scout.md`.
- **Status:** accepted and applied 2026-09-07
- **Jason's decision:** path approved via `scout_reconciliation_plan.md`; applied to PLAN.md during authorized Gate A factual reconciliation.

---

### PROP-002 — Bounded external research intake for manually-collected reports
- **Date:** 2026-09-18
- **Proposed by:** external research intake session (branch `testing`)
- **Affects:** PLAN.md §5 (new "Authorized narrow amendment" section); no phase, gate, cap, or model choice changes
- **Current plan says:** durable evidence enters only through the Scout's live discovery path, and `research_findings` is rewritten on every curation run, so there is nowhere to retain research the Scout did not produce.
- **Problem:** Gate D is blocked on an unconfigured search lane (`exa_search: off`; GitHub returns 0 results for all three children). Three manually-collected external reports about `RQ-6d9c12f4` exist and contain usable material the blocked Scout cannot re-derive. Without a retention lane this research is either lost or, worse, pasted into the trusted layer without provenance.
- **Proposed change:** add a read-mostly external intake library + CLI that retains original PDFs, native extracted text, per-report citations, deduplicated source targets, and an append-only per-claim review history in an **isolated workspace database outside the repository and vault**. Claims reach the existing, unmodified curator eligibility gate only after an attributed human scope review. Adds `pypdf` as the extraction dependency.
- **Cost of not changing:** externally collected research stays unmanaged, unverifiable, and indistinguishable from curated evidence; the project's only options become "discard it" or "trust it".
- **Status:** accepted — authorized by Jason before implementation; recorded here because the entry point is new even though no plan constraint is relaxed.
- **Jason's decision:** authorized as a bounded retention feature. Explicitly **not** authorized: executing Gate D, promoting trusted evidence, changing production question state, creating strategy cards, running backtests, paid services, or account automation.

**Deliberately not done (would need separate approval):**
- OCR or any further extraction dependency beyond `pypdf`.
- Relaxing Phase 6's ≥3-upstream-sources bar so external claims could satisfy Gate D — that is on the "relaxing a hard cap" list above and needs its own proposal.
- Any write into `brain/01_Sources/` or `db/brain.sqlite` from this lane.

---

## Accepted changes log

Once Jason accepts a proposal, apply it to `PLAN.md`, then record the applied change here with the date, so the plan's history stays readable.

| Date | Proposal | Applied to | Summary |
|---|---|---|---|
| 2026-09-07 | PROP-001 | `PLAN.md` Phase 4 deliverables | Replaced stale `Snapshots/` with canonical `Source_Snapshots/` path during Gate A factual reconciliation. |
| 2026-09-18 | PROP-002 | `PLAN.md` §5 amendment section | Added the authorized external-report retention intake. Isolated workspace only; no production promotion, no Gate D execution. |

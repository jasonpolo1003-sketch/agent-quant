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
- **Status:** proposed
- **Jason's decision:** path itself is already approved via `scout_reconciliation_plan.md`; PLAN.md wording still needs a human edit.

---

## Accepted changes log

Once Jason accepts a proposal, apply it to `PLAN.md`, then record the applied change here with the date, so the plan's history stays readable.

| Date | Proposal | Applied to | Summary |
|---|---|---|---|
| — | — | — | — |

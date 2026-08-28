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

*(none yet — plan written 2026-08-28)*

---

## Accepted changes log

Once Jason accepts a proposal, apply it to `PLAN.md`, then record the applied change here with the date, so the plan's history stays readable.

| Date | Proposal | Applied to | Summary |
|---|---|---|---|
| — | — | — | — |

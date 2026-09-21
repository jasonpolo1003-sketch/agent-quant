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

### PROP-003 — Independent zero-account arXiv discovery lane, distinct-URL source minimum, sparse-result quarantine
- **Date:** 2026-09-19
- **Proposed by:** Gate D readiness assessment session (branch `testing`)
- **Affects:** Phase 6 implementation shape (adds a discovery lane); **no** change to the ≥3-source bar, the 5-fetched-source cap, source tiers, validators, the curator threshold, or snapshot-before-model. Two of the three parts are *tightenings*.
- **Current plan says:** Phase 6 step 3 names "Exa / GitHub / web search" as the discovery lanes, and the ≥3-upstream-source bar is an exit-gate requirement.
- **Problem:** three separate findings, all verified live at `51979f6`:
  1. **No lane can produce URLs.** `gate_readiness.py` exits **4** with **0 candidates** for all three children. Only `search_exa` and `search_github` turn a question into URLs (`agent_reach.py:498-520`, `SEARCH_CHANNELS = ("exa_search",)`). Exa is `off` by Jason's decision; GitHub is authenticated and working but searches *code repositories* — `gh search repos "RSI exit rules backtest"` returns `[]`. The plan's "web search" was never implemented as search: `fetch_web(self, url)` takes one already-known URL and has no query parameter. RSS/YouTube have no search code at all. `SEARCH_LANES` is decorative — `operational_lanes()` is never called from `src/`.
  2. **The ≥3-source bar is not enforced in the pipeline.** It exists only in `scripts/gate_readiness.py:41` (a read-only probe) and in Phase 6 prose. `executor.py:481` checks only `if not sources` — i.e. ≥1. A run with 1-2 sources completes and writes a raw note that *looks* valid while violating the Phase 6 exit gate.
  3. **Counting `len(sources)` is inflatable.** `normalize_candidate_url` does not unify `http://arxiv.org/abs/1909.04327v1` with `https://arxiv.org/abs/1909.04327`, so one paper in two forms counts as two sources and could satisfy a 3-source minimum with two works.
- **Proposed change:** (a) add `src/quant_brain/discovery/arxiv_search.py`, an independent zero-account lane over arXiv's free Atom API, owning its own hardened transport (fixed HTTPS host, timeout, User-Agent, bounded read, DOCTYPE/entity rejection, strict arXiv-host validation, canonical `https://arxiv.org/abs/<id>` with version stripped), used as a top-up after GitHub and returning the existing hit contract so all ranking/tiering/caps are untouched; (b) enforce the minimum over **distinct normalized upstream URLs**, with one shared constant imported by both the executor and the readiness probe; (c) quarantine sparse results through the existing `_write_failed_run_note` path with canonical URLs, snapshot paths/hashes, tiers, rejection reasons, actual/required counts, the generated query expression and follow-up guidance — producing **no `raw_saved` note and no curator recommendation**.
- **Honest coverage estimate:** under **one fixed query rule** (no per-question tuning), distinct canonical `/abs/` candidates are **RQ-6d9c12f4: 5**, **RQ-80be8cf7: 1**, **RQ-c920baeb: 1**. A three-phrase conjunction returns 0 for all three. **This lane plausibly makes one of three questions probe-ready, and does not complete Gate D.** An earlier informal probe suggested wider coverage; that came from hand-tuned per-question queries and is withdrawn.
- **Why arXiv is a defensible lane:** `/abs/` URLs already classify as `primary`/promotable under the existing unmodified `source_quality.classify_source` ("structural primary signal: arxiv-abs"), and a real abstract page fetched through the existing `jina_fetch` returns 722 words, passing the 600-char/120-word content floor. No new fetch dependency, no account, no API key, no paid service.
- **Cost of not changing:** Gate D stays blocked indefinitely unless Jason configures a third-party service he has declined; and the two enforcement defects remain latent, so whenever a lane *is* restored the first child run could write an under-evidenced raw note that passes silently.
- **Status:** accepted and implemented 2026-09-19 on `testing`. **No child run was executed.**
- **Jason's decision:** approved as proposed. Explicitly **not** authorized by that approval: running any of the three child questions, which remains a separate decision after independent review.
- **Verified outcome after implementation** (`391 passed, 1 skipped`; Ruff clean on `.` and on `src tests scripts`):

  | Question | unique URLs | `gate_readiness` exit |
  |---|---|---|
  | RQ-6d9c12f4 exit rules | 3 | **0 — ready** |
  | RQ-c920baeb max holding period | 1 | 4 — still blocked |
  | RQ-80be8cf7 costs/slippage | 1 | 4 — still blocked |

  The estimate held exactly: one of three questions is now probe-ready. The generated expression for RQ-6d9c12f4 was `all:"mean reversion" AND all:"exit"`, yielding three distinct `primary`-tier works (`arxiv.org/abs/1411.5062`, `/2309.16008`, `/1601.04210`). No query was tuned per question to change any of these outcomes; the two blocked questions are an honest finding about reachable literature, not a lane failure.

  `db/brain.sqlite` is byte-identical after the probes; `strategy_cards`/`backtests`/`price_datasets`/`reviews` all remain 0; all three questions remain `queued` with `raw_note_path NULL`.

**Deliberately not proposed (would need separate approval):**
- Executing any of the three child questions. That remains a separate authorization after implementation, independent review, and fresh readiness checks.
- Relaxing the ≥3-source bar, the 5-source cap, tiers, validators, or the curator threshold.
- Configuring Exa, any paid API, or any account-backed service.
- Per-question query tuning to reach a passing candidate count.

---

## Accepted changes log

Once Jason accepts a proposal, apply it to `PLAN.md`, then record the applied change here with the date, so the plan's history stays readable.

| Date | Proposal | Applied to | Summary |
|---|---|---|---|
| 2026-09-07 | PROP-001 | `PLAN.md` Phase 4 deliverables | Replaced stale `Snapshots/` with canonical `Source_Snapshots/` path during Gate A factual reconciliation. |
| 2026-09-18 | PROP-002 | `PLAN.md` §5 amendment section | Added the authorized external-report retention intake. Isolated workspace only; no production promotion, no Gate D execution. |
| 2026-09-19 | PROP-003 | `PLAN.md`, `src/quant_brain/discovery/arxiv_search.py`, `agent_reach.py`, `research/executor.py`, `scripts/{gate_readiness,agent_reach_check}.py` | Added the zero-account arXiv lane; made the ≥3-source bar enforceable over distinct upstream works; quarantined sparse results in Failed_Runs. One of three questions became probe-ready; no child run executed. |

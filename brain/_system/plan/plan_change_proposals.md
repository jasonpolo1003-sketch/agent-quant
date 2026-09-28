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

### PROP-004 — Pre-registered seed lane for known candidate URLs (plus DOI-alias collapse)
- **Date:** 2026-09-26
- **Proposed by:** Gate D source-blocker planning, checkpoint E1 (branch `testing`)
- **Affects:** Phase 6 implementation shape (adds a discovery lane). **No** change to the ≥3 distinct-upstream bar, the 5-fetched-source cap, tiers, validators, the curator threshold, snapshot-before-model or any harness code (dispatcher/registry/paths).
- **Current plan says:** Phase 6 step 3, "discover candidates -> Exa / GitHub / web search". Discovery is search-only (`agent_reach.search_for_question`); there is no path for an already-known URL.
- **Problem (verified in E1, see `brain/00_Inbox/Gate_D_Seed_Dossier_2026-09-26.md`):**
  - `exa_search` is `off` by Jason's decision.
  - GitHub searches code.
  - The arXiv lane now fails with HTTP 406 from Python `urllib`, while curl succeeds for the same URL; the cause is not established.
  - As a result, `gate_readiness.py` returns 0 URLs for all three child questions.
  - Relevant exit-rule sources exist and are accessible, but only as human-collected report citations. No Scout lane can reach them.
- **Proposed change:**
  - (a) An optional frozen seed file `brain/00_Inbox/Scout_Seeds/<RQ>.md` lists at most 10 URLs. Each URL records where it was found, who added it, the date, and the declared rule that built the list.
  - (b) The Scout merges seeds into the candidate pool before the unchanged classify → rank → cap → content floor → snapshot → Qwen → validators steps. A seed cannot set a tier, relevance or any payload field.
  - (c) The lane is recorded as `seeded` in the discovery events, the raw note and any Failed_Runs receipt.
  - (d) **Tightening:** DOI-alias collapse. `distinct_upstream_keys` currently counts `doi.org/<doi>` and a publisher landing page that contains the same DOI as two works.
- **Guards against cherry-picking:**
  - The seed file is committed before the run.
  - It contains every lead that matches the declared rule, not only those likely to pass.
  - It is never edited after a run.
  - Seeds found by a human are labelled as human discovery. Source *support* still comes only from the Scout's own snapshot and extractive validation.
  - Intake-catalog verification is never counted as Scout validation.
- **Cost of not changing:** no approved lane reaches relevant sources, so every child run is quarantined at 0 candidates and Phase 6 cannot progress. The zero-code alternative is to configure Exa, which is account-backed and was previously declined.
- **Status:** accepted for **E2 implementation scope only**, via the E2 instruction (2026-09-26). Implemented on `testing` and uncommitted, pending Drew's review. **No Scout or curator run is authorized.** No real candidate list exists yet: the RQ-6d9c12f4 list waits on the Malaysian-chapter scope decision.
- **Jason's decision:** E2 implementation authorized. Separate authorization is still required for any list registration, any live run (E3), and PROP-005.
- **As implemented (differences from the proposal text above):**
  - **Name:** "pre-registered candidate list", not "seed". `seeded` already names the offline stub backend. Lists live in `brain/00_Inbox/Scout_Candidates/<RQ>.md`, and the lane label is `preregistered_candidate_list`.
  - **Search is replaced, not merged, in list mode.** The candidate pool is exactly the list, so off-topic search hits cannot displace screened entries.
  - **The budget is ≤5 accepted sources, not ≤5 fetch attempts.** Thin pages are backfilled, and attempts are bounded by the list length (≤10).
  - **DOI identity is a host-anchored table** (`discovery/work_identity.py`): the doi.org/dx.doi.org resolvers, the arXiv DataCite DOI, European Proceedings `/article/`, Wiley `/doi/…`, and SSRN abstracts on SSRN hosts only. It is used for the source minimum and for list validation. Candidate dedupe on the search lane was **deliberately left unchanged** because `test_duplicates_cannot_buy_a_passing_run` pins the existing layering. An alias on an unlisted publisher is not collapsed.

**Explicitly not proposed:** fixing or working around the arXiv 406 (a separate diagnosis task), adding hosts to tier allowlists, lowering `MIN_UPSTREAM_SOURCES`, or turning the external-intake catalog into a trusted lane.

---

### PROP-005 — Narrow clarification: "source-insufficient" child outcome for Phase 6 pipeline acceptance
- **Date:** 2026-09-26
- **Proposed by:** Gate D source-blocker planning, checkpoint E1
- **Affects:** `phase_06_research_scout_agent.md` exit gate and "On outcome (5) vs research outcome". Phase 8 entry is **unchanged**.
- **Current plan says:** success requires, for each child, "Raw research note citing ≥3 upstream sources" and "All Phase 5 validators pass", and "If 1-3 and 5 pass but the curator finds the evidence insufficient, the phase still succeeded."
- **Problem:** the live pipeline writes a raw note only when ≥3 distinct upstream sources are fetched **and** the validators pass. Otherwise it quarantines the run to `Failed_Runs`. The written clause blesses only a *curator-level* negative. A question whose reachable literature holds fewer than 3 relevant sources, which the E1 dossier indicates for `RQ-c920baeb` and `RQ-80be8cf7`, can therefore never satisfy the gate, however honest and well-evidenced the negative is. That leaves Phase 6 open indefinitely, and the gate says nothing about whether the harness works.
- **Proposed change:** a child question counts toward Phase 6 **pipeline** acceptance with the outcome `source-insufficient` only if **all** of these hold:
  - (a) It was dispatched through an approved lane with a pre-registered seed or query set.
  - (b) A pre-run dossier shows fewer than 3 relevant, accessible, distinct candidates.
  - (c) A full-provenance `Failed_Runs` receipt and a complete event trail exist.
  - (d) The quarantine reason is **source count**. A model or validator failure never qualifies.
  - (e) Jason signs the review of the outcome.
  - (f) **At least one** child question completed the full raw-note → validators → separately dispatched curator path.

  A source-insufficient outcome never counts as research acceptance. It never unlocks Phase 8, whose entry gate still requires a source-supported exit rule, maximum holding period and cost assumptions.
- **Cost of not changing:** Phase 6 stays pending until the approved lanes can reach ≥3 relevant sources for every child. That is a legitimate choice: the alternative is to keep the gate as written.
- **Status:** proposed
- **Jason's decision:** _pending_

### PROP-006 — Window-only extraction outcome for a single oversize source
- **Date:** 2026-09-27
- **Proposed by:** oversize-source windowing checkpoint (PLAN.md §10 "What to do next" item 2)
- **Affects:** Phase 6 extraction internals (`research/executor.py` `qwen_extract`). The curator-facing raw research contract (`research/schema.py`) and every validator in `llm/validators.py` are **unchanged**.
- **Current plan says:** "Design deterministic, evidence-preserving windowing for an oversize single source … must keep exact quotations verifiable against the immutable full snapshot, remain all-or-nothing, and stay inside the shared 15-minute run deadline. It must not silently select only favorable passages."
- **Problem:** the NAAIM snapshot (56,018 bytes, about 31,330 tokens) cannot fit the 11,571-token per-call budget. When it is split into windows, some windows will honestly contain nothing relevant. The existing one-source payload cannot say that. `evidence` must be non-empty, `main_claim` needs `min_length=1`, and the validator rejects any supplied source the model leaves out. The only way a window like that could pass is if the model quoted an arbitrary sentence and wrote a filler claim, which is fabrication.
- **Proposed change:**
  - Add a **window-only** `WindowOutcome` contract, used only inside extraction and never written to a note or read by the curator. Its `outcome` is either `evidence` (carrying one ordinary `RawResearchSource`, validated by the unchanged `validate_research_output` against the window text, and then with every quotation re-checked against the full snapshot) or `no_relevant_evidence` (no quotation, no claim and no recommendation, validated structurally).
  - Windows are deterministic, ordered and overlapping, and each has a stable ID, offsets and a sha256. All of them are processed, with no keyword pre-selection.
  - Every window must produce a validated outcome. Any failure fails the run.
  - If no window finds evidence, the source fails, and so does the run.
  - Evidence windows merge by deterministic, non-generative rules: verbatim unions, minimum confidence, AND for `mvp_testable`, and fail on a `source_type` disagreement. The merge produces exactly one ordinary source record, which must pass the unchanged whole-bundle validator.
  - Windowing applies only to a source the existing pre-flight already refuses. At most 10 windows are allowed per source, and a source above that is refused before any model call.
  - Model calls per windowed source rise to (windows × the per-call ladder), all under the same shared 15-minute deadline.
- **Cost of not changing:** a rerun on the committed RQ-6d9c12f4 list fails closed before its first model call. Phase 6 / Gate D cannot progress on that list without editing it, which is forbidden.
- **Status:** accepted for implementation (Jason approved the design plan, 2026-09-27). **No RQ-6d9c12f4 rerun is authorized by this acceptance.**
- **Jason's decision:** approved the windowing design, 2026-09-27.

---

## Accepted changes log

Once Jason accepts a proposal, apply it to `PLAN.md`, then record the applied change here with the date, so the plan's history stays readable.

| Date | Proposal | Applied to | Summary |
|---|---|---|---|
| 2026-09-07 | PROP-001 | `PLAN.md` Phase 4 deliverables | Replaced stale `Snapshots/` with canonical `Source_Snapshots/` path during Gate A factual reconciliation. |
| 2026-09-18 | PROP-002 | `PLAN.md` §5 amendment section | Added the authorized external-report retention intake. Isolated workspace only; no production promotion, no Gate D execution. |
| 2026-09-19 | PROP-003 | `PLAN.md`, `src/quant_brain/discovery/arxiv_search.py`, `agent_reach.py`, `research/executor.py`, `scripts/{gate_readiness,agent_reach_check}.py` | Added the zero-account arXiv lane; made the ≥3-source bar enforceable over distinct upstream works; quarantined sparse results in Failed_Runs. One of three questions became probe-ready; no child run executed. |
| 2026-09-26 | PROP-004 (E2 scope only) | `discovery/{work_identity,candidate_list}.py`, `live_discovery.py`, `research/executor.py`, `harness/handlers.py` (Scout handler only), `scripts/{dispatch_task,gate_readiness}.py` | Added a pre-registered candidate-list lane through the unchanged live path, and DOI-alias collapse in the source minimum. No list registered, no run executed. PROP-005 remains proposed. |

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
- **Status:** accepted
- **Jason's decision:** accepted as written, 2026-09-28. Claude builds it; the scheduler is always-on (Windows Task Scheduler); Claude CLI is the only backend for now.

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
- **Amendment A (2026-09-28, approved by Jason after the E4 failure):**
  - **Window recommendation removed.** The window contract no longer asks the model for a `curator_recommendation`. Every windowed source carries the fixed, most conservative value `needs_more_work`, both when a window is validated and after the merge.
  - **Source identity required.** The window source's `source_id` is now mandatory in the schema sent to the model, where it had been legacy-optional.
  - **Failed runs keep diagnostics.** A failed run keeps its failed model responses as untrusted diagnostics in `Failed_Runs/diagnostics/<run>.responses.json`, separate from research.
  - **Evidence validators unchanged.** No Scout rerun is authorized by this amendment.

### PROP-007 — Scale down: freeze the research harness and move to data and the first honest backtest
- **Date:** 2026-09-28
- **Proposed by:** Claude session, at Jason's request
- **Affects:** PLAN.md §7 (Phase 6 exit, Phase 8 entry), §9 (model policy), §10; `phase_08_first_backtest.md` entry gate. The evidence rules in AGENTS.md are **unchanged**.
- **Current plan says:**
  - Phase 6 exit needs all three child Scout runs to produce honestly validated outcomes.
  - Phase 8 entry needs "Phase 6 produced source-supported exit rule + max holding period + cost assumptions, **and** Jason approved moving to card stage".
- **Problem:**
  - About a month went into the research harness: scraping, local-Qwen extraction, windowing, validators and receipts. It works and fails safe.
  - Nothing yet tests whether a strategy makes money (`price_datasets = 0`, no card, no backtest).
  - The holding-period and cost questions are source-insufficient (E1 dossier), so the current gate may never open.
  - Jason no longer needs 24/7 scraping, the main reason local Qwen was chosen.
- **Proposed change:**
  1. **Freeze the research harness.** Validators, receipts and the verifier stay; no new harness features and no further Qwen tuning; the 24/7 scraping goal is dropped. A Claude or Codex subscription-CLI backend would be a separate §9 proposal, made only if research is needed again.
  2. **Close Phase 6 as "pipeline verified, research partial".** At most one more RQ-6d9c12f4 rerun, as the end-to-end check with no retry. `RQ-c920baeb` and `RQ-80be8cf7` are closed as source-insufficient. This is not research acceptance and not evidence of edge.
  3. **Gate F: market data.** Daily OHLCV for SPY, QQQ and IWM, fetched with the existing yfinance/pandas/pyarrow/DuckDB dependencies.
     - Stored as Parquet and registered in `price_datasets`.
     - Records the source, download time, adjustment method, sha256 and date range.
     - Tests use a small committed fixture and no network.
  4. **Phase 8 entry, relaxed honestly.**
     - Exit rules come only from quoted, preserved sources: ChartSchool/Connors RSI(2) (exit above 70, or close above the 5-day MA) and NAAIM RSI(3) ≤ 40.
     - Holding period and costs are **declared assumptions**, labelled as such, over a small grid fixed in advance (for example 5 or 10-day time stops, and 2, 5 or 10 bps per side plus slippage). Every combination is run and logged.
  5. **One frozen, hashed strategy card, then one backtest** with a small, readable in-repo pandas runner.
     - Close-based signals execute at the next bar, enforced in code.
     - Costs apply to every trade.
     - Same-engine comparisons against buy-and-hold and random entry.
     - The in-sample/held-out split is fixed on the card.
     - An immutable trial ledger records every run.
     - No vectorbt (Commons Clause) or backtesting.py (AGPL).
  6. **Adversarial review with a verdict that can be "reject".** It covers lookahead, costs, sample size, regimes, multiple testing (deflated Sharpe across the grid) and the benchmark and random-entry comparisons.
  7. **Prop-firm fit only if the strategy survives,** as a later separate step. No paper or live trading.
- **Still forbidden:** live trading and brokers, paid APIs, claiming a backtest proves profit, editing the committed candidate list, lowering validators.
- **Honest expectation:** RSI(2) ETF mean reversion may show no edge after costs. That is a valid outcome.
- **Status:** accepted
- **Jason's decision:** approved the direction, 2026-09-28. The optional Phase 6 rerun was not yet chosen.

### PROP-008 — Local read-mostly "Brain Terminal" UI
- **Date:** 2026-09-28
- **Proposed by:** Claude session, from a brainstorm with Jason
- **Affects:** PLAN.md §6 (non-goals), §10. Detail: [ui_terminal_plan.md](ui_terminal_plan.md).
- **Current plan says:** "A GUI/dashboard/TUI. CLI + Markdown + SQLite is the interface." (§6 non-goals)
- **Problem:**
  - Jason builds in Codex and cannot see what the harness, the data or the agents are doing while work happens.
  - The backtest stage (PROP-007 steps 4–6) will produce equity curves and trial ledgers that are hard to judge as text.
  - Jason also wants to understand the system well enough to rebuild it.
- **Proposed change:**
  - Remove "GUI/dashboard" from §6 and add a bounded, local-only terminal (127.0.0.1) per `ui_terminal_plan.md`.
  - **Reads by default.** `brain.sqlite` is opened read-only, and the only writes into it are `agent_events` through `ops.events`.
  - UI state lives in a separate `db/terminal.sqlite`.
  - **Actions:** a fixed job allowlist (health_check, data_refresh, agent_prompt; research_run disabled while PROP-007's freeze holds), with caps and events.
  - **Tutor:** a NotebookLM-style tutor with no tools; its notes are `trusted: false` and never indexed as evidence.
  - **Model calls:** only through official subscription CLIs (`claude -p`, `codex exec`) or local Ollama. No token handling.
  - **Not a harness change:** the harness extraction model policy (§9) is unchanged.
  - **No cross-over:** builds only in its own paths; never edits the data, harness or research code, `schema.sql`, or `brain/03`–`07`.
- **Cost of not changing:** work stays invisible between handoffs, backtest judgement relies on reading tables, and the learning goal has no home.
- **Still forbidden:** trading buttons, market feeds or brokers, remote or multi-user access, arbitrary shell from the UI, token extraction, and promoting UI-generated text to evidence.
- **Status:** accepted
- **Jason's decision:** accepted as written, 2026-09-28. Claude builds it; the scheduler is always-on (Windows Task Scheduler); Claude CLI is the only backend for now.

### PROP-009 — FRED macro and rate series, with provenance, for risk-free returns and regime analysis
- **Date:** 2026-09-29
- **Proposed by:** Claude session, at Jason's request (he is requesting a free FRED API key)
- **Affects:** PLAN.md §6/§10 scope after PROP-007; Gate F data rules (`gate_f_market_data.md`), extended to a second source; `.env.example`; the backtest runner's cash and Sharpe definitions **for future cards only**. The evidence rules in AGENTS.md are unchanged.
- **Current plan says:**
  - PROP-007 limits data to "daily OHLCV for SPY, QQQ and IWM".
  - The engine states that "cash earns 0%" (`backtest/engine.py`), and Sharpe uses "risk-free 0" (`backtest/stats.py`).
- **Problem:** the SC-0002 adversarial review, `brain/05_Reviews/SC-0002-adversarial-review.md`, names two gaps that price data alone cannot close:
  1. **Risk-free rate.**
     - Rule A is flat about 85% of the time, but cash earns 0% on the card.
     - The review's sensitivity check "uses flat rates, not the actual T-bill history" (2% and 5% assumed).
     - A fair comparison against buy-and-hold needs the real daily T-bill rate for each day.
  2. **Regimes.**
     - The held-out edge was concentrated in 2020–2022.
     - The review could not say whether that is a volatility, rate or recession effect, because the brain holds no regime data.
- **Proposed change:**
  1. **Key handling.**
     - `FRED_API_KEY` goes in the git-ignored project `.env`, with a blank placeholder in `.env.example`.
     - The key is read from the environment only. It is never logged, and never written to manifests, reports or notes.
  2. **A second Gate F lane,** `fred`, reusing the same guarantees:
     - immutable Parquet, a manifest with sha256, an accepted-only loader, and SQLite registration;
     - a read-only verifier, hermetic tests on a small committed fixture, and no network in pytest.
     - It calls the FRED REST API directly with the existing `requests`/`pandas`. There is **no OpenBB dependency** in the project.
  3. **Start with market-priced series only,** which are not revised after publication:
     - `DTB3` (3-month T-bill), `DGS10` and `DGS2` (Treasury yields), `T10Y2Y` (curve spread);
     - `USREC` (NBER recession flag, marked `analysis_only` because NBER dates recessions after the fact);
     - `VIXCLS` (VIX, marked `analysis_only`).
  4. **Revised series** (CPI, unemployment, GDP and the like) are **out of scope** until a follow-up adds ALFRED point-in-time vintages and release-date lags. Using today's revised values in a backtest is lookahead.
  5. **Use in backtests.**
     - Future cards may declare `cash_rate: DTB3` so that flat days earn the real T-bill return, and report Sharpe on excess returns.
     - Regime splits (recession, curve inversion, VIX terciles) may be reported **as analysis**.
     - A macro condition may appear as a trading rule only if the card declares it before any result is seen, and every variant tried counts toward the multiple-testing adjustment.
  6. **SC-0002 stays closed.**
     - Its result is not re-scored, rescued or re-run under the new definitions.
     - A regime re-analysis of its existing trades may be written as a clearly labeled **post-hoc note** that feeds only the design of a new card.
- **Cost of not changing:** every future card inherits the 0% cash assumption, which penalizes low-exposure strategies against buy-and-hold by a varying and unmeasured amount. Regime dependence, the review's main open question, stays unanswerable.
- **Still forbidden:**
  - paid data or APIs;
  - live trading and brokers;
  - revised macro series without point-in-time vintages;
  - editing or re-running SC-0002 under new rules;
  - committing the key.
- **Status:** accepted
- **Jason's decision:** accepted 2026-09-29. His free FRED key is in the project `.env` and verified live (DTB3, T10Y2Y, USREC, VIXCLS).

---

### PROP-010 — Quant Learning Terminal: a local, beginner-first TradingView + QuantConnect
- **Date:** 2026-09-29
- **Proposed by:** Claude session, at Jason's request ("almost 1-1 with TradingView … free resources … for a beginner to understand how quant trading works, risk management and everything").
- **Affects:**
  - PROP-008's Brain Terminal (branch `ui-terminal`). Its decision "no market feed, no quotes" would change to "labelled live data for display and practice only".
  - PROP-007's "no paper or live trading": only if Jason chooses D3 (a local simulated practice account, no broker).
  - Data scope beyond SPY/QQQ/IWM; it builds on PROP-009 (FRED).
  - The evidence rules in AGENTS.md are **unchanged**.
- **Current plan says:**
  - PROP-007 limits work to one card and one backtest, with no paper or live trading.
  - PROP-008 is a read-mostly window onto the brain, with no market feed.
- **Problem:**
  - Jason wants to learn how quants think (risk first, exact rules, honest testing), and to have a tool a beginner can learn from.
  - The terminal shows the brain's state, but it does not teach markets, risk or strategy testing.
  - Neither TradingView (no honest-testing lessons) nor QuantConnect (not beginner-simple, cloud-first) does both.
- **Proposed change:** the plan in `brain/_system/plan/learning_terminal_plan.md`, summarised:
  1. **A TradingView-style workspace** in the existing terminal, using the bundled Lightweight Charts: charts, watchlist, replay with a blind mode, trade replay of backtests, screener, heatmap, calendars, symbol pages and news.
  2. **A QuantConnect-style spine:** universe → signal → sizing → risk → execution → evaluation. It serves as both the Lab's navigation and the Academy's chapters.
  3. **An Academy** (12 modules, risk before signals, SC-0002 as the case study), a **Risk Center** (sizing, risk of ruin, drawdown, correlation), and Explain-this on every screen.
  4. **A free data stack with visible provenance:** Yahoo EOD (personal use), FRED, SEC EDGAR, Fed FOMC dates, Nasdaq symbol directory, Coinbase live crypto (no key), Alpaca or Finnhub free live US stocks (IEX, labelled).
  5. **A rule builder** whose exploratory runs are counted by a live trial counter. Only frozen cards through the gated runner earn verdicts.
  6. **Seven phases:** see → data → learn → test → live → practice (optional) → paid upgrades (optional). Each phase stops for Jason.
  7. **Paid options researched but not bought:** the recommendation is $0 through Phase 5. Norgate first if money is spent, for survivorship-free history.
- **Honest limits:** 1-to-1 with TradingView is **not** achievable for free on data. There are no free global markets, futures, options, Level 2 stocks or deep intraday history. The plan says so on-screen rather than hiding it.
- **Still forbidden:**
  - live trading and broker order routing;
  - paid APIs without Jason's decision;
  - public hosting or sharing personal-use data;
  - live data feeding backtests or cards;
  - TradingView Advanced Charts (its licence requires public use) and TradingView data resellers.
- **Decisions for Jason:** D1–D8 in the plan's §11 (scope order, live stock feed, practice account, starter universe, engine, who builds, look, audience).
- **Status:** accepted
- **Jason's decision (2026-09-29):**
  - "Let's create the free one first."
  - The recommended defaults D1–D8 are taken; D2 (live stock feed) and D3 (practice account) come when their phases start.
  - He relaxed the process for this direction change: "we can step away from the ruling as we are changing directions". This means lighter plan-before-build and no per-step stop gates for the terminal's free build.
  - **Kept regardless:** no live trading or broker order routing, no paid data or APIs without Jason's decision, provenance labels on data, and SC-0002 stays closed.

---

### PROP-011 — Single-rule futures replication: make PBO inapplicable, not passed
- **Date:** 2026-10-25
- **Proposed by:** Drew, following Jason's approval of the lean MNQ ORB *engineering direction*
- **Affects:** The MES/MNQ ORB handoff's OOS > 0 / DSR >= 0.95 / PBO < 0.5 promotion rule; a new futures strategy card only. Does not retroactively change SC-0002, RX-0001, or any multi-variant experiment.
- **Current plan says:** The MES/MNQ handoff requires all three thresholds, including PBO < 0.5 at L3. The handoff is currently an unreviewed research note under `brain/sources/mes_mnq/` in the separate `testing` worktree; the master `PLAN.md` does not yet specify a futures ORB gate.
- **Problem:** CSCV/PBO measures the chance of overfitting a *selection* from a tested family. A single literature-derived rule frozen before local ORB P&L has no local winner-selection step and no meaningful PBO estimate. Inventing neighboring variants merely to calculate PBO would create avoidable trials; claiming `PBO < 0.5` for one rule would be false.
- **Proposed change:** For **one predeclared, fixed MNQ ORB rule only**, record `PBO: not applicable (no local selection)` and do not treat this as a passing score. Require an approved, hashed strategy/statistics card before implementation or local ORB P&L; inventory all prior ORB looks and inherited published selection, specify an honest selection-adjustment/DSR method and its unavailable inputs, verify pre-run power/MDE for a stated economically meaningful effect, and keep L3 costs, paired random-anchor controls, one locked held-out read, positive net primary outcome, conservative fill, complete trial ledger, and no MES rescue. Define in the card the *single* decisive contrast, thresholds, uncertainty method and inconclusive rules. Concentration, roll and regime slices are reported diagnostics, not automatic independent vetoes. If a real selectable family is later approved, restore CSCV/PBO with every trial's daily returns and a separately frozen family; this amendment cannot be used to promote that family.
- **Cost of not changing:** A single-rule test can never pass the existing gate, or a bogus PBO value will be reported; building a large variant grid solely to satisfy the metric wastes time and increases selection risk.
- **Status:** accepted for this single-rule track on 2026-10-25; master PLAN.md narrow note applied. The eventual frozen card and power/MDE still require separate review; this is not approval of a result.
- **Jason's decision:** explicitly selected “Approve PROP-011 as proposed” in the 2026-10-25 decision prompt. Also selected drafting Fetna's cash-open 15-minute R2 rule **for review only**, not freezing or testing it. No held-out run authorized.

### PROP-012 - BM25 keyword layer for retrieval (proposed 2026-10-28)
- **Problem:** semantic search (nomic-embed-text) can miss exact terms such as rule IDs, tickers and formula names.
- **Proposed change:** add a BM25 lexical score fused with the existing embedding score inside `retrieval/`, judged by `scripts/retrieval_eval.py` (must beat the current Recall@5). No new agent, no new models.
- **Origin:** an ML4T-based harness proposal (parked locally 2026-10-28; the rest duplicated existing code).
- **Status:** proposed; low priority while strategy work leads.

---

## Accepted changes log

Once Jason accepts a proposal, apply it to `PLAN.md`, then record the applied change here with the date, so the plan's history stays readable.

| Date | Proposal | Applied to | Summary |
|---|---|---|---|
| 2026-09-07 | PROP-001 | `PLAN.md` Phase 4 deliverables | Replaced stale `Snapshots/` with canonical `Source_Snapshots/` path during Gate A factual reconciliation. |
| 2026-09-18 | PROP-002 | `PLAN.md` §5 amendment section | Added the authorized external-report retention intake. Isolated workspace only; no production promotion, no Gate D execution. |
| 2026-09-19 | PROP-003 | `PLAN.md`, `src/quant_brain/discovery/arxiv_search.py`, `agent_reach.py`, `research/executor.py`, `scripts/{gate_readiness,agent_reach_check}.py` | Added the zero-account arXiv lane; made the ≥3-source bar enforceable over distinct upstream works; quarantined sparse results in Failed_Runs. One of three questions became probe-ready; no child run executed. |
| 2026-09-26 | PROP-004 (E2 scope only) | `discovery/{work_identity,candidate_list}.py`, `live_discovery.py`, `research/executor.py`, `harness/handlers.py` (Scout handler only), `scripts/{dispatch_task,gate_readiness}.py` | Added a pre-registered candidate-list lane through the unchanged live path, and DOI-alias collapse in the source minimum. No list registered, no run executed. PROP-005 remains proposed. |
| 2026-09-28 | PROP-007 | PLAN.md §10 (direction note) | Freeze research harness; move to Gate F data, one frozen card, one honest backtest |
| 2026-09-28 | PROP-008 | PLAN.md §6, §10; `ui_terminal_plan.md` | Local Brain Terminal UI: reads by default, allowlisted jobs, tutor with no tools, auth only through subscription CLIs |
| 2026-09-29 | PROP-009 | `plan_change_proposals.md` (status accepted) | FRED rate and regime series under Gate F rules; key only in the git-ignored `.env` |
| 2026-09-29 | PROP-010 | `learning_terminal_plan.md` (status accepted); PLAN.md §10 | Beginner-first learning terminal, free tier first; lighter process for this track; safety rules kept |
| 2026-10-25 | PROP-011 | PLAN.md §10 (narrow futures note) | Single frozen MNQ ORB rule: PBO not applicable, not passed; multi-rule selection still requires CSCV/PBO. Exact card/power and held-out run remain separately gated. |

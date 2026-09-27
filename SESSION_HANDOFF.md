# Quant Agent Brain — Session Handoff

## Gate D checkpoint E2: pre-registered candidate-list lane (2026-09-26). Ready for Drew's review.

This implements the scope PROP-004 authorized for E2. Nothing is committed, and there was no Scout or curator dispatch, network research, list registration, arXiv repair or later-phase work. PROP-005 remains **proposed**. **Phase 6 / Gate D remain incomplete.** `HEAD` is still `7277a76`.

**Change set**

New files:
- `src/quant_brain/discovery/work_identity.py`
- `src/quant_brain/discovery/candidate_list.py`
- `tests/test_work_identity.py`
- `tests/test_candidate_list_lane.py`

Modified files:
- `discovery/live_discovery.py`
- `research/executor.py`
- `harness/handlers.py` (the Scout handler only)
- `scripts/dispatch_task.py`
- `scripts/gate_readiness.py`
- `tests/test_gate_readiness.py`

`dispatcher.py`, `registry.py`, `paths.py` and `acquisition.py` are unchanged.

**How the lane behaves**

- **List file:** `brain/00_Inbox/Scout_Candidates/<RQ>.md`, holding exactly one ```json block with these fields:
  - `research_id`, `selection_rule`, `screening_reference`, `registered_by`, `registered_on`
  - `candidates[]`: 1 to 10 entries, each with `url`, `found_via`, `added_by`, `added_on`

  pydantic `extra="forbid"` applies at both levels, so an entry cannot carry a tier, title, claim or evidence. One work listed twice (for example a DOI and its landing page) is refused at load.
- **Run:**
  - `scripts/dispatch_task.py --type discovery --research-id <RQ> --candidate-list brain/00_Inbox/Scout_Candidates/<RQ>.md`
  - This requires the live backend and an explicit research ID matching the list's own `research_id`. Both are checked before any fetch.
  - The backend keeps `name = "live"`, so the Qwen ladder and validators always run.
  - **Search is not called.** Hits are built from URLs alone, and tiers come from `classify_source`.
- **Offline pre-registration check:**
  - `scripts/gate_readiness.py --research-id <RQ> --candidate-list <path>`
  - It checks that the list loads, matches the question, and names at least 3 distinct works.
  - It says nothing about relevance, access or support. Exit codes: 0 ready, 4 short, 5 invalid.
- **Budget, precisely:** at most 5 **accepted** sources. A thin or boilerplate page is backfilled from the next listed candidate, so fetch attempts can reach the list length (≤10). Pre-fetch `reject` URLs are never fetched.
- **Provenance:** a `discovery_lane` block (path, sha256, count, URLs) is recorded in:
  - the `discovery_started` and `discovery_completed` events
  - the handler detail
  - a `## Discovery Lane` note section, outside the JSON block
  - `InsufficientUpstreamSources.detail`
  - every Failed_Runs receipt, including failures inside `discover()`. It is captured before discovery as an input, not as candidate evidence.

**DOI identity** (`upstream_work_key`)

It uses only a host-anchored table:
- doi.org / dx.doi.org resolver paths
- the arXiv DataCite DOI, mapped to the abs URL
- European Proceedings `/article/10.15405/…`
- Wiley `/doi/(abs|full|pdf|epdf)/10.1111/…`
- SSRN `abstract_id` / `abstract=`, on SSRN hosts only

Publisher rows match the full path with a slash-free suffix. `…/figures`, unlisted publishers, query-string DOIs and `abstract_id` on other hosts stay separate.

The key is used by `distinct_upstream_keys` (the source minimum, which counts fetched sources) and by list validation. **Plan deviation:** search-lane candidate dedupe was left on the normalized URL. Changing it broke `test_duplicates_cannot_buy_a_passing_run`, which pins the existing layering, and the minimum was already protected at the counting layer.

**Verification**

| Check | Result |
|---|---|
| `uv run pytest -q` | **488 passed, 1 skipped** (425 plus 63 new) |
| `tests/test_dispatcher.py` | 13 passed, file unchanged |
| `ruff check .` | clean |
| `ruff check src tests scripts` | clean |
| `git diff --check` | clean |
| `db/brain.sqlite` | `6db65981…f530f9e29`, unchanged |
| `exit-rules-final/external.sqlite` | `4b20094c…7c00`, unchanged |
| `.gitattributes`, `RUN-4e9d910742.md`, five `2026-09-21` snapshots | sha256 OK |
| Questions | all three `queued` with a NULL path; agent_tasks 4, agent_events 58; protected tables 0 |

**Mutation checks** (each applied to a backed-up file and restored byte-for-byte, verified by sha256). All seven were caught:

| # | Mutation | Tests failed |
|---|---|---|
| M1a | drop the European Proceedings row | 5 |
| M1b | drop the SSRN host anchor | 1: `abstract_id` on another host |
| M2 | run search in list mode | 12 |
| M3 | loader ignores extra fields | 6 |
| M4 | lane not captured before discovery | 2 |
| M5 | count listed URLs, not acquisitions | 1 |
| M6 | pass list entries through as hits | 1 |

**Limitations**

- **"Frozen" is procedural.** The sha256 is recorded, but the code does not check git. Before any E3 run, compare the recorded sha256 with the committed blob.
- **Unlisted publisher aliases are not collapsed**, so work identity must be checked by hand before a run.
- Relevance screening and originator independence remain human steps.
- The arXiv 406 is untouched.

**Next, needing separate approval**
- Jason's scope decision on the Malaysian DOI chapter.
- Registering and committing the RQ-6d9c12f4 list.
- E3, the single run.


## Gate D checkpoint E1: seed dossier and proposals (2026-09-26). Stopped for Jason.

This was an approved plan checkpoint. It involved no code change, no Scout or curator run, and no write to the production DB or the intake catalog. **Phase 6 / Gate D remain incomplete.**

**Outputs:**
- `brain/00_Inbox/Gate_D_Seed_Dossier_2026-09-26.md`, holding leads only.
- PROP-004 (pre-registered seed lane plus DOI-alias collapse) and PROP-005 (narrow "source-insufficient" pipeline-acceptance clarification), both **proposed**, in `brain/_system/plan/plan_change_proposals.md`.

**Verified before and after:**
- **425 passed, 1 skipped.** Ruff and `git diff --check` clean.
- `db/brain.sqlite` `6db65981…f530f9e29` is unchanged.
- `exit-rules-final/external.sqlite` `4b20094c…7c00` is unchanged.
- All three questions are `queued` with a NULL raw-note path. agent_tasks is 4 and agent_events is 58. The protected tables are 0.

**New findings:**
1. **The arXiv lane now fails.** Python `urllib` gets **HTTP 406** from `export.arxiv.org` while curl gets 200; the cause is not established. `gate_readiness` now exits 4 with **0 URLs for all three** questions (RQ-6d9c12f4 was at 3).
2. **DOI aliases double-count.** `distinct_upstream_keys` counts a `doi.org` URL and its publisher landing page as 2 works.
3. **sec.gov comment letters classify as `primary` on host alone.**
4. **One catalog DOI primary was fetched, not blocked.** `doi.org/10.15405/epms.2022.10.4` states the RSI(14) 30/70 exit, but on Malaysian equities.

**Pre-run findings:**

| Question | Relevant, accessible | Promotable | Originators | Finding |
|---|---|---|---|---|
| RQ-6d9c12f4 | 4 (5 with the epms DOI) | 2 (3 with the DOI) | 2 (3 with the DOI) | The Scout bar is clearable via a seed lane. Whether the DOI enters is Jason's scope call. |
| RQ-c920baeb | 2, both out of scope | — | — | **source-insufficient.** One is an uncited SEO 10-day time stop; the other is a 9-day cap on A-shares. |
| RQ-80be8cf7 | 2 | 2 | 2 | **source-insufficient.** Nasdaq-measured QQQ spreads of about 1–2 bps (2011–12), and an arXiv paper assuming 18 bps for retail US large-cap equities (2024). |

**Decisions for Jason:**
- Accept or reject PROP-004, or configure Exa instead.
- Include or exclude the epms DOI from the RQ-6d9c12f4 seeds.
- Accept or reject PROP-005.
- Whether to diagnose the arXiv 406 as its own task.
- Next step after those decisions: E2, implementing the seed lane with tests. That needs approval, and no run happens in E2.


## YouTube methodology scout (2026-09-26) — video leads only

Cataloged the first 30 `@itsjjsimon` uploads and all 14 visible `@deltatrendtrading/videos` uploads via yt-dlp; fetched and reviewed English transcripts from 4 JJ Simon and 6 Delta Trend Trading videos. Timestamped transcripts retained outside the repo at `C:/Users/jason/quant-agent-brain-intake/channel-review-2026-09-26/` (video IDs are file names). These are creator claims/teaching, not independent strategy evidence.

- JJ Simon: the sample emphasizes prop-firm evaluation economics and payouts, with useful warnings about selection among many tests, uncounted trials, and small samples (`PMGhHCjYG5c` 03:39–05:40). This supports the existing immutable-trial and benchmark policy; it does **not** substantiate payout figures or a transferable market edge. The break-even/zero-edge account example (`2BtwoTCxcbc`) is a simulation premise, not proof of positive strategy expectancy. Do not copy risk sizing into this no-live-trading project.
- Delta Trend Trading: stronger fit for learning a research workflow. `M3-0LfZMsz4` distinguishes building/falsifying an idea from copying a guru setup; `Zu4sL5u-WyU` defines event sampling as a research start, not a strategy; `ZQUmXK_xapM` shows null results and context-feature experiments; `MCnFrUxZARU` explains net expectation and path dependence. Treat on-video p-values/results as unverified until data, code, split, cost assumptions, and trial family are available. `jGhk-uSrtII` initially describes IID trade bootstrap and later warns of regime dependence; resampling the same trade history does not increase independent information or establish edge.
- No reviewed video supplies three distinct promotable upstream sources documenting the daily ETF RSI exit rule. These videos belong in a methodology/learning lead pool, not the Phase 6 source count or trusted research index. No phase, gate, code, production database, or strategy state was changed.


## Methodology reports reviewed (2026-09-26) — leads, not trusted research

Jason supplied two PDFs, retained byte-for-byte in the vault's `Projects/Quant Agent Brain/Research/External Reports/`:
- `Quant Mind End-to-End - external synthesis.pdf` (11 pages; SHA-256 `0ee8b4878c08eb4089944b1ef7315c613127aa4f0f5d072167064b6f4db3ac6e`): useful hypothesis-first, point-in-time and anti-overfitting orientation; mostly familiar to PLAN.md. Its proposed immediate Alpaca/Tiingo, MLflow, six-station agents, Qlib and external competitions are **not adopted**; they expand scope or jump gates. Precise pricing, subscriber, platform and performance claims are unverified leads, not sources of truth.
- `Closing Three Missing Validation Gaps in the Evidence-First Quant Agent.pdf` (45 pages; SHA-256 `5a3e9ed7d3c3748449501b3350ac43baf16a60358f61e5d2b79c`): stronger candidate methodology for later validation: separate within-family instrument replication from independent economic environments; count signal episodes before exits and evaluate net-outcome power after a strategy freeze; compare feed semantic contracts and signal/trade parity before paper. Its source list provides leads, not independently verified proof; gate cutoffs and formulas need primary-source and data checks before implementation. Neither PDF supplies a third qualifying independent source for `RQ-6d9c12f4` or changes Phase 6 / Gate D.

Retained only as **external methodology leads** in the vault, not imported into the exit-rule claims catalog, RAG/trusted notes, or production database. Do not treat report prose as multiple independent sources. Any added phase/exit gate needs a proposal and Jason's approval; prioritize the current research-source blocker first.


## Resume verification (2026-09-26)

**Completed after Jason selected the original catalog:** appended five exact-quotation claims using the existing Intake API and verified all five offline against pinned snapshots. All five have `quote_match=true`, `full_rule_match=true`, and state `partially_supported` / `review_required`; this is exact passage matching, not validation of a complete strategy. No attributed human scope review was performed. Handoff remains empty. Added 5 claims, 5 evaluations and 10 history rows; no new targets, reports or fetches. All pre-existing catalog rows and non-database intake files (including acceptance.json) were preserved; production DB unchanged. Backup and machine-readable verification are in `C:/Users/jason/quant-agent-brain-intake/exit-rules-review/` as `external-before-remap-2026-09-26.sqlite` and `remap-recorded-verification.json`. The workspace decision is resolved; the next boundary is human scope review and acquiring additional relevant independent evidence through an approved route. Gate D remains incomplete.


- Live local `testing` and remote `refs/heads/testing` both resolve to `7277a76`; the checkpoint is pushed. Earlier "not pushed" statements below are historical.
- Fresh verification: `uv run pytest -q` = **425 passed, 1 skipped**; `uv run ruff check .` and `git diff --check` pass. Production DB SHA-256 before/after: `6db659812411efe084f5168d41c98192b79ca59f9b739d89991e6c3f530f9e29`.
- All three Gate D child questions remain queued with no raw-note path. Strategy cards, backtests, price datasets and reviews are all zero. Phase 6 / Gate D remain incomplete.
- Existing uncommitted changes were documentation only (PLAN.md and SESSION_HANDOFF.md); preserved during this review.
- Next bounded step recommended: append exact-quotation claims and offline verification to the original isolated `exit-rules-final` catalog, preserving existing records. This resolves the copied-workspace path guard without bypassing it. Await Jason's workspace choice before catalog writes; do not attribute a scope review to him without his actual review.
- This step alone cannot satisfy Gate D: the existing packet identifies only two promotable targets (Connors via ChartSchool and Hill). More independent, relevant evidence and an approved ingestion route are still needed. No Scout/curator dispatch, model calls, production research writes, commits or pushes performed in this session.


## Verbatim re-mapping pre-check for RQ-6d9c12f4 (2026-09-22) — stopped at a guard, awaiting decision

The reliability checkpoint is committed as **`7277a76`** (entry below). This is the separate part B:
read-only, offline, no model, no network, no Scout, no curator. **Phase 6 / Gate D remain incomplete.**

- **Pre-check:** the intake verifier's own `normalized`/`source_span` were run on the integrity-checked
  pinned snapshots in `C:\Users\jason\quant-agent-brain-intake\exit-rules-final`. All **5 of 5**
  verbatim exit-rule spans were located, across 5 distinct targets:
  - ChartSchool (Connors, 5-day SMA exit);
  - Arthur Hill (RSI(5) above 70);
  - Connors Research (4-period RSI above 55);
  - NAAIM/Pagonidis (hold while RSI(3) ≤ 40);
  - Bulkowski (relaying Connors & Alvarez, seven-day high).
- **Only 2 are promotable tier (both StockCharts), and only 1 is independent of Connors.** Under the
  unchanged tier policy this material cannot meet the ≥3-source bar.
- **Not recorded, by design.** Recording was to happen in a byte-identical copy
  (`…\exit-rules-review`). But the catalog stores absolute snapshot paths inside `exit-rules-final`, and
  `safe_target` refuses paths outside the workspace root. The guard was not bypassed, and the recorded
  workspace was verified unchanged (24 files, sha256).
- **Packet:** `…\exit-rules-review\REVIEW-PACKET.md`; raw results in `remap-precheck.json`.
- **Jason's decision:**
  1. append the claims to `exit-rules-final` and verify offline;
  2. use a fresh workspace and one refetch; or
  3. stop here.

  Then comes his attributed `review --state supported_in_scope`. A third promotable, independent source
  is needed before any `RQ-6d9c12f4` Scout run could pass. A "reviewed-leads" Scout lane remains a
  possible governance proposal, not authorized.

## Reliability checkpoint committed (2026-09-22) — local on `testing`, not pushed

The discovery-recovery hardening and the reliability closeout (both described below) were independently
reviewed and are now **one local commit on `testing`**, directly after `df63698`. **Not pushed**
(`origin/testing` is still `3c02397`). No Scout run, retry, curator or research. **Phase 6 / Gate D remain
incomplete.**

- **Two wording fixes at commit time, no behaviour change:**
  - the held-question receipt now gives **two literal, runnable** release commands
    (`clear_raw_note_path=True` if the note was removed, `False` if it was kept) instead of a template;
  - a failed dispatcher finalization is reported as `task_row=unconfirmed (finalization update failed;
    state not verified)` instead of assuming the row is still `running`.

  The tests assert both.
- **Verified before committing:**
  - the related files (recovery, dispatcher-failure, dispatcher, discovery handler, provenance,
    upstream minimum): **76 passed**;
  - full suite **425 passed, 1 skipped**;
  - `ruff check .` and `ruff check src tests scripts` clean; `git diff --check` clean;
  - `db/brain.sqlite`, `.gitattributes`, and every `Failed_Runs/` and `2026-09-21` snapshot file
    sha256-identical.
- **Committed paths (7):** `research/executor.py`, `research/intake.py`, `harness/dispatcher.py`,
  `tests/test_fail_closed_recovery.py`, `tests/test_dispatch_failure_recording.py`, `PLAN.md`,
  `SESSION_HANDOFF.md`.
- **Limitations are unchanged:** see the closeout entry below.

**Research blocker, re-diagnosed (read-only; details in `PLAN.md`):** for `RQ-6d9c12f4` the bottleneck is
**claim-to-source mapping**, not discovery.
- The retained external reports paraphrased their claims.
- The intake verifier (by design) accepts only a claim that *equals* its verbatim quotation.
- So 4 located quotations, plus 2 exit rules present verbatim in pinned snapshots, never reached
  review.
- Tier policy (unchanged) makes only the 2 StockCharts targets promotable, fewer than the ≥3 bar.

**Next (approved):** an offline re-mapping of those verbatim spans in a *copy* of the intake workspace,
producing a review packet for Jason's attributed scope review. It creates no raw note, no Gate D
progress, and no promotion.

## Reliability closeout (2026-09-22) — historical: the pre-commit description

**425 passed, 1 skipped** (413 + 12 new); `ruff check .` and `ruff check src tests scripts` clean;
`git diff --check` clean. `db/brain.sqlite` (`6db65981…f530f9e29`), `.gitattributes` and every
historical `Failed_Runs/` and `Source_Snapshots/2026-09-21/` file are sha256-identical before and after.
On top of `df63698` together with the recovery hardening below; nothing staged, committed or pushed. No
Scout run, retry, curator or research. **Phase 6 / Gate D remain incomplete; source relevance is
unchanged.**

**1. Incomplete recovery no longer looks retryable, and a real control backs that up.**
- Inspection showed that **nothing reads a receipt's `retryable:` line**. The retry signal actually used
  is `research_questions.status`:
  - executor queue selection takes `researching`, then `queued`;
  - `claim_next_research_task` takes `queued`, then overwrites the note at its fixed path;
  - explicit `--research-id` dispatch took any status.
- So when raw-note recovery **fails**, the question is now held at a new status **`needs_review`**
  (added to `intake.VALID_STATUSES`), using the existing `update_research_status`, whose `COALESCE`
  keeps `raw_note_path` pointing at the leftover file.
- No selector picks `needs_review` up, and `execute_discovery_task` refuses it on explicit dispatch
  **before the task binds**, so fail-closed can't undo the hold.
- The receipt says `retryable: false` and **"Manual inspection required"**, naming the leftover path,
  what to check, and the exact release one-liner (`reset_research_for_retry(...)`).
- A preserved (`untouched-preexisting`) or `restored` pre-existing note counts as **successful**
  recovery: `queued`, `retryable: true`.
- The `recovery` block is now `raw_note` / `question` (`queued` | `needs_review` | `update-failed`) /
  `complete` / `secondary_failures`. If the hold or reset update itself fails, the receipt says
  "Recovery incomplete" and claims neither state.

**2. The dispatcher preserves the original error**
(`harness/dispatcher.py`, failure branches only).
- Both `except` branches now call `_record_dispatch_failure`, which independently attempts:
  1. the first event (`handler_failed` or `path_violation`);
  2. `dispatch_failed`;
  3. `_finish_task_row(..., "failed")`.
- Each goes through a local `_secondary` helper (the same contract as the executor's `_attempt`; kept
  local so the harness doesn't import a research module).
- Secondary failures are added as notes on the handler's exception, stating `task_row=failed` or
  `task_row=NOT finalized (still 'running')`, never a finalization that didn't happen.
- The bare `raise` re-raises the same object with its traceback; the notes appear in the CLI's traceback.
- `Exception` only is caught, so `KeyboardInterrupt`/`SystemExit` propagate. The success path, the
  pre-handler writes and the handler contracts are unchanged.

**Tests (12 new; mutation-checked).**
- `tests/test_dispatch_failure_recording.py` (8):
  - each event failing; finalization failing (the row really stays `running`, and the note says so);
  - everything failing together; a handler `PathViolation` whose own event fails;
  - `KeyboardInterrupt` during finalization; a clean failure with no notes;
  - a successful dispatch unchanged.
- `tests/test_fail_closed_recovery.py` (+4):
  - explicit dispatch of a held question refused with nothing mutated;
  - queue selection skips a held question;
  - a failed hold reported, not claimed;
  - end to end, the same Qwen exception carrying both executor and dispatcher notes.
- The two cleanup-failure tests now expect the hold, and the pre-existing-note tests assert
  `complete: true` / `retryable: true`.
- Mutation checks:
  - un-guarding finalization fails 2 dispatcher tests;
  - resetting after a failed cleanup fails 3 hold tests.
- The committed tests, including `tests/test_dispatcher.py`, pass unchanged.

**Limitations (precise).**
- The hold blocks automatic selection and Scout dispatch. It does **not** stop direct DB edits, or a
  manual `research_scout_runner.py prepare`, which claims only `queued` but would overwrite the fixed
  note path if the question were released without inspection.
- Release is a documented manual one-liner, not a CLI command.
- Recovery and finalization are attempted, not guaranteed. The success-path dispatcher writes and the
  pre-handler task-row and `dispatch_started` writes are still unguarded, but there's no original error
  to mask at those points.
- A scaffold whose creation failed mid-way is left in place and not held, because ownership can't be
  proven.
- Snapshot frontmatter still has no `run_id`.

**Recommended next step toward research acceptance (not authorized):** relevance, not reliability, is the
blocker (zero `RSI`/`ETF` mentions in the five retrieved works). The smallest step is read-only: add a
deterministic topical-relevance count to `scripts/gate_readiness.py` and use it to evaluate one
alternative lane or query for `RQ-6d9c12f4`, with no model and no Scout dispatch. Propose a single,
separately authorized Scout run only if a candidate set clears both the ≥3-source bar and the relevance
check.

## Fail-closed recovery hardened (2026-09-22, later) — historical; its dispatcher limitation is resolved above

**413 passed, 1 skipped** (397 + 16 new); `ruff check .` and `ruff check src tests scripts` clean; `git diff
--check` clean. `db/brain.sqlite` (`6db65981…f530f9e29`), `.gitattributes`, and every file under
`Failed_Runs/` and `Source_Snapshots/2026-09-21/` are sha256-identical before and after. On top of
`df63698`; nothing staged, committed or pushed. No Scout run, retry, curator or research. **Phase 6 /
Gate D remain incomplete; the source-relevance blocker is untouched.**

**Defects fixed, all in `src/quant_brain/research/executor.py`.** Each one could skip recovery and
replace the original research error with a diagnostic one:
1. The `discovery_failed` event ran *before* `_fail_closed_discovery`, unguarded, so a DB error there
   skipped *all* recovery. (Found during planning; not in the brief.)
2. The receipt write caught only `OSError`, so a `PathViolation` escaped.
3. The `failed_run_written` event shared the receipt's `try`: a DB error escaped, and an `OSError` nulled
   the path of a receipt that *had* been written.
4. Scaffold cleanup caught only `OSError`, its fallback event was unguarded, and the unlink/restore
   bypassed `resolve_write`.
5. `reset_research_for_retry` was unguarded.
6. The receipt always claimed the question "was returned to `queued`".

**Fix.**
- A private `_attempt()` runs each step and returns `(ok, value)`. Outcomes are read from the flag, so a
  successful `None` return can't read as failure. It absorbs `Exception` only, so
  `KeyboardInterrupt`/`SystemExit` propagate.
- `_fail_closed_discovery` now attempts, independently and in order:
  1. the `discovery_failed` event;
  2. raw-note recovery;
  3. the reset;
  4. the receipt, *after* recovery so it states the outcome, with a `recovery` block. `retryable: false`
     and "Recovery incomplete" appear when the reset failed;
  5. the `failed_run_written` event.
- Each failed step is added as a note on the original exception (`add_note`). That channel depends on
  neither the DB nor the filesystem. The executor's bare `raise` re-raises the same object with its
  original traceback.

**Ownership corrected (behaviour change).**
- Before: a pre-existing note at `Raw_Research/{research_id}.md` that the run never modified was
  **deleted** on an early failure. A pre-existing note that *was* restored lost its pointer, so a retry
  would recreate, and overwrite, it at the same path.
- Now the run mutates only what it provably owns or changed. A run-created scaffold is removed; a
  modified pre-existing note is restored byte for byte; an untouched pre-existing note is left alone.
- Every mutation passes `resolve_write` first: a `PathViolation` **refuses** recovery and is reported,
  never bypassed.
- `reset_research_for_retry` gained a keyword-only `clear_raw_note_path` (default `True`, so other callers
  are unchanged). The pointer is cleared only when no note remains at it. The curator only accepts
  `raw_saved`/`curated`, so a `queued` question that keeps its pointer can't be curated.

**Tests: `tests/test_fail_closed_recovery.py` (16).**
- Coverage:
  - receipt `PathViolation` (real enforcement) and receipt `OSError` (real `FileExistsError`);
  - each event failing with `PathViolation`/`OSError`/`sqlite3.OperationalError`, and all of them together;
  - cleanup refused by the real resolver after a normal scaffold and Qwen failure;
  - cleanup `PermissionError`; a reset DB failure;
  - `KeyboardInterrupt` propagation; a clean failure;
  - both pre-existing-note cases.
- Every case spies on the real handler and asserts the **same exception object** and the original
  traceback frame. Cases also assert task, question and scaffold state.
- Mutation-checked: all 16 fail against `HEAD` code (some only via the new `recovery` field), and
  un-guarding just the receipt step fails the 3 receipt tests.
- Existing tests pass unchanged.

**Remaining limitations.**
- Recovery is *attempted*, not guaranteed: a failed filesystem or DB step is reported, not overcome.
- The dispatcher (`harness/dispatcher.py`) still emits `handler_failed`/`dispatch_failed` and finalizes
  `agent_tasks` unguarded, so a broken DB there can still mask the original *after* discovery
  re-raises. That is harness-wide and a candidate follow-up.
- If `create_raw_research_note` fails mid-way, its scaffold is left in place, because ownership can't be
  proven.
- The manual `prepare_next_research_run` still overwrites `Raw_Research/{research_id}.md` whatever the
  pointer says. That behaviour predates this change and this change doesn't cause it.
- Snapshot frontmatter still has no `run_id`.

**Next decision is Jason's:** review this unstaged change set. A dispatcher-level guard is a
recommended small follow-up; it matters only when the DB is already failing, and in that case the
receipt still records the original error. The source-relevance blocker still decides whether a Scout
retry can succeed.

## Checkpoint committed (2026-09-22) — provenance repair and historical evidence (historical)

Two local commits on `testing`, **not pushed** (`origin/testing` is still `3c02397`). No Scout run, retry,
curator or research was executed. **Phase 6 / Gate D remain incomplete.**

- **`54df8cf`, evidence:** `RUN-4e9d910742.md` plus the five `Source_Snapshots/2026-09-21/` files, committed
  unchanged, and a new `.gitattributes` marking exactly those six paths `-text` so `core.autocrlf=true`
  cannot normalise them. Original, staged and committed sha256 were verified identical for all six (CRLF
  and trailing whitespace preserved). The link to `RUN-4e9d910742` stays **probable, not established**.
- **The commit containing this entry:** the provenance repair (`live_discovery.py`, `executor.py`), its
  tests (`test_failed_run_provenance.py`, `test_upstream_minimum.py`), and this file plus `PLAN.md`. Code
  and test bytes are sha256-identical to the state verified below (397 passed, 1 skipped, Ruff clean), so
  that verification was reused rather than re-run.
- **Next build task, required before any further production Scout attempt:** harden
  `_fail_closed_discovery`:
  - treat receipt-write and event failures (`PathViolation`, `OSError`, any `Exception`) as secondary;
  - always run raw-note cleanup and `reset_research_for_retry`;
  - re-raise the **original** exception, recording the handler failure without masking it;
  - add regression tests injecting `PathViolation`/`OSError` into the receipt and event writes. Each asserts
    the original exception propagates, the question is back in `queued`, no scaffold remains, and the
    evidence gates are unchanged.

  Optional and separate: stamp `run_id`/`task_id` into new snapshot frontmatter.

## Finalization verification of the provenance repair (2026-09-22) — historical: the pre-commit state

**Verdict: no blocker to committing the provenance repair.** Verification and status updates only; nothing
staged, committed or pushed; no Scout run, retry, curator or research. Phase 6 / Gate D remain
**incomplete**. Branch `testing` at `3c02397` (= `origin/testing`).

- **397 passed, 1 skipped**; `ruff check .` and `ruff check src tests scripts` both clean; `git diff --check`
  clean; untracked `tests/test_failed_run_provenance.py` and `RUN-4e9d910742.md` whitespace-clean.
- **Change-set integrity, checked by hashes rather than `git status`:** the DB, all 12 files under
  `Failed_Runs/` and `Source_Snapshots/2026-09-21/`, the tracked `git diff`, and every modified or untracked
  change-set file were sha256-hashed before verification and matched afterwards. `db/brain.sqlite` =
  `6db659812411efe084f5168d41c98192b79ca59f9b739d89991e6c3f530f9e29`.
- **Scope review:** the code diff touches only `live_discovery.py` and `executor.py`; no change to source
  minimums, the 5-source cap, validators, tiers, prompts or the model ladder. The receipt and all 5 snapshots
  were read in full: public arXiv abstract pages only.
- **Snapshot integrity (intact, not authorship):** for all 5, `content_hash` recomputes exactly from the
  LF-normalised body *including* its final newline (on disk the files are CRLF because `write_text` runs on
  Windows); filename prefixes and `url_hash` also match. This proves integrity, not which run wrote them;
  the link to `RUN-4e9d910742` stays **probable**.
- **Separate follow-up, required before the next production Scout run** (new build task, needs approval):
  make `_fail_closed_discovery` catch non-`OSError` failures from the receipt write and its event, always run
  cleanup and the reset to `queued`, and re-raise the *original* exception, with `PathViolation` and
  `OSError` injection tests. Optional: stamp `run_id`/`task_id` into new snapshot frontmatter.
- **Proposed commit scope (later, separately approved):**
  - **A, the fix:** both source files, both test files, `PLAN.md`, `SESSION_HANDOFF.md`.
  - **B, historical evidence as-is:** `RUN-4e9d910742.md` and the 5 snapshots. No backfill; the commit
    message calls the lineage "probable". Precedent: `46728a7`.
- **Commit-stage cautions:**
  - There is no `.gitattributes` and `core.autocrlf=true`, so stored blobs will be LF. After staging, compare
    the sha256 of the `git cat-file blob :<path>` output with the on-disk sha256 and decide explicitly on
    normalisation. `content_hash` is defined over the LF body, so it stays verifiable either way.
  - The snapshots contain trailing whitespace that is part of the captured content and covered by the hash:
    never whitespace-fix them. There are no pre-commit hooks.

## Failure-receipt provenance defect fixed (2026-09-20, later)

**397 passed, 1 skipped (re-verified 2026-09-22 after the review follow-up; 396 at the
original fix); Ruff clean on `.` and on `src tests scripts`; `git diff --check` clean.**
The failed-run receipt and five `2026-09-21` snapshots were hash-checked before and after
the follow-up and are unchanged. Production
`db/brain.sqlite` byte-identical across the whole session at sha256
`6db659812411efe084f5168d41c98192b79ca59f9b739d89991e6c3f530f9e29` (this is the
**post-run** hash; the older `43fa24b0…` is the pre-run baseline and is now historical —
the database legitimately changed when `RUN-4e9d910742` wrote its audit rows, which must
not be discarded). Everything is **unstaged**; nothing committed, pushed or merged.
**No Scout child run, no curator, no other research question was executed.** Phase 6
remains **incomplete**.

**Root cause — two defects sharing one gap.**

1. **Candidate evidence was attached to an exception class, not to the run.**
   `_fail_closed_discovery` built the receipt's `Detail` from
   `{"task_id", "created_scaffold", **getattr(error, "detail", {})}`. Only
   `InsufficientUpstreamSources` defines `.detail`; `QwenValidationError` carries
   `.attempts` and no `.detail`, so the spread contributed nothing and, whenever a receipt
   *was* written for a post-fetch failure (Qwen validation, write_note, a path violation
   raised by the run's own writes), it named no source and no snapshot.
2. **`snapshot_path` / `snapshot_sha256` were read but never written.** `executor.py`
   read both off each source dict, but `_source_from_fetch` only ever interpolated the
   path into an `evidence` string — it never set the keys. So **even the sparse-source
   path** recorded `null` for both. `tests/test_upstream_minimum.py` asserted only that
   the key was *present*, which `None` satisfies; that is why a green suite carried this.

**The fix (smallest robust change, 2 source files).**

- `src/quant_brain/discovery/live_discovery.py` — `_source_from_fetch` takes
  `snapshot_sha256` and sets both `snapshot_path` and `snapshot_sha256` as real keys. The
  hash is computed at the call site from the same `content` `save_source_snapshot` hashes,
  so it is identical by construction and the filename's 12-char prefix stays a cross-check.
- `src/quant_brain/research/executor.py` — new shared `candidate_evidence()` helper (one
  definition, used by both failure paths, so they cannot describe candidates differently);
  provenance captured **once at the discover stage** into `discovered_provenance` and
  passed to `_fail_closed_discovery` as `run_provenance`, merged **beneath**
  `error.detail` so `InsufficientUpstreamSources` keeps precedence.

**Why capture at the discover stage:** a *successful* model call rebinds
`sources = list(model_result.output["sources"])`, so reading `sources` at failure time
would describe a later `write_note` failure with model-shaped values instead of what
discovery actually fetched. Capturing early pins the classifier tier and the canonical
fetched URL regardless of which later stage fails. This is covered by its own test.

**`QwenValidationError` was deliberately left untouched.** Giving it a `detail` would
require `qwen_call` — which knows nothing about snapshots — to carry per-source
provenance, inverting a boundary the codebase maintains. The executor-side keyword covers
the *contents* of every receipt the fail-closed path writes, whatever the exception type.

**How future failures retain lineage — receipt contents, not receipt creation.** This fix
improves what a receipt says **when the receipt is successfully written**; it does not
change whether one is written. For a discovery failure after the discover stage, a written
receipt now contains `run_id`, `task_id`, `research_id`, `stage`, `error_type`,
`accepted_candidates` (url / title / tier / snapshot_path / snapshot_sha256),
`snapshot_paths`, `distinct_upstream_count`, `required_upstream_count`,
`rejected_candidates` and `search_query_expression` — enough to reconstruct the run without
directory dates or manual inference (verified by building the receipt the real run
*should* have written, in an isolated scratch project). For a failure inside discovery,
before a `DiscoverResult` exists, the receipt carries `run_id`/`task_id`/`research_id`/
`stage`/`error_type` and the error text, and **no** candidate or snapshot fields (absent,
not empty) — covered by its own test.

**Receipt creation is still not guaranteed (unchanged, pre-existing).**
`_fail_closed_discovery` catches only `OSError` around the receipt write, and the receipt
is written only once a task has loaded. So: (i) an `OSError` writing the receipt leaves no
receipt (cleanup and reset still run); (ii) a `PathViolation` from `resolve_write` on the
`Failed_Runs` path — or any other non-`OSError` from the write or its event — escapes the
handler, skipping raw-note cleanup and the `queued` reset, and replaces the original
exception (which survives only as `__context__`); (iii) a failure before the task loads
(e.g. an unknown `research_id`) writes no receipt by design. None of this was fixed here.

**Regression coverage — `tests/test_failed_run_provenance.py` (6 new tests):** the reported
Qwen-validation defect; the recorded hash verified against the filename prefix and the
snapshot's own frontmatter; fail-closed containment unchanged; a later-stage failure
keeping discovery-side values rather than model-shaped ones; an early discovery failure
(valid task, real live backend raising `LiveDiscoveryError` before any `DiscoverResult`)
that spies on the real `_fail_closed_discovery` to prove it runs once at stage `discover`,
propagates the original exception object, and writes a receipt with run/task/research/
stage/error but no candidate or snapshot fields; and an unknown `research_id`, which
writes no receipt because no task ever loads.
`tests/test_upstream_minimum.py` was strengthened from key-presence to non-null values.
**Mutation-checked:** temporarily removing the two keys fails 4 of these tests, so they
genuinely detect the defect rather than merely passing alongside it.

**Review follow-up (2026-09-22).** An independent review found two issues, both now
resolved: (1) the original early-failure test used an unknown `research_id`, so it failed
before a task loaded and never reached `_fail_closed_discovery` or the provenance
carrier — it was renamed to say what it actually pins, and the valid-task test above was
added (mutation-checked: seeding `discovered_provenance` with an empty
`accepted_candidates` fails it); (2) this file and `PLAN.md` implied every failure now
writes a complete receipt — corrected above to distinguish receipt *contents* from
receipt *creation*. No production code changed in the follow-up.

**Nothing weakened.** No change to prompts, the model ladder, validators, source tiers,
`MIN_UPSTREAM_SOURCES`, the 5-source cap, curator controls, snapshot-before-model ordering,
or the cleanup sequence. The sparse path's **contract** is preserved (same keys, same
semantics, same behavior); its **contents** necessarily change, because two fields that
were always `null` now hold real values — it is not byte-identical, and claiming so would
be wrong.

**The existing receipt was NOT backfilled, and that is deliberate.** An earlier assessment
called the attribution "deterministically provable". That was an overclaim. The evidence is
strong but circumstantial: `TASK-a679b61436` is the only `discovery` task ever recorded;
all five `captured_at` values (00:57:54–00:58:03 UTC) fall strictly inside the run's event
span (00:57:30–01:00:18 UTC); and every `content_hash` recomputes exactly from its snapshot
body. **None of that proves authorship** — content hashes prove *integrity*, not which
process wrote the file. An identical snapshot could come from a standalone script or an
unrecorded invocation; the files carry no `run_id` and no event references a path. The
brief permits backfill only when deterministically proven, so
`brain/00_Inbox/Failed_Runs/RUN-4e9d910742.md` is **unchanged**. The association is
recorded here as **probable**, with that limitation stated. The tiers reported for those
five URLs are **re-derived** by running the current `classify_source` now — not recovered
runtime records.

**Remaining limitations.** (a) The five existing snapshots stay without machine-readable
lineage; only *future* runs get it. (b) The fix records provenance in the receipt, not in
`agent_events` — a reader still needs the receipt file. (c) Snapshot frontmatter still
carries no `run_id`; linking a loose snapshot back to a run remains inferential. (d) The
unsuitable-relevance blocker for `RQ-6d9c12f4` is untouched and unresolved. (e) Receipt
*creation* is not guaranteed — see "Receipt creation is still not guaranteed" above.

**Next decision is Jason's:** review this unstaged change set; then choose whether to widen
the lane set toward sources that document RSI exit rules, stamp `run_id` into snapshot
frontmatter as a follow-up, or accept the relevance gap as the finding. Do **not** lower
`MIN_UPSTREAM_SOURCES` or relax extractive support.

## First Scout child run executed — research acceptance FAILED, fail-closed safeguards verified (2026-09-20)

**Verdict: Scout research acceptance failed; fail-closed safeguards verified.** The first
Research Scout child run ever executed under PROP-003 ran end to end for `RQ-6d9c12f4`
only, and stopped at the Qwen validation gate. **This is not Gate D or Phase 6 progress on
the research question** — it is the first evidence that the production path's safety
machinery works on live material.

**Precisely what was and was not written.** Nothing was promoted. No validated raw
research note and no curator recommendation were produced. But the run was not
write-free: it wrote durable task and event audit rows (`agent_tasks` +1,
`agent_events` +9), a failed-run receipt, and five source snapshots. An earlier draft of
this section said "nothing durable was written", which was wrong.

> **Correction (2026-09-20, later).** This section originally stated that the five
> snapshots' provenance "survives in `agent_events`". **It does not.** All nine event
> payloads were re-inspected: they carry `S1`–`S5` opaque labels, model/prompt/response
> hashes and validator reasons, and **no source URL, no snapshot path and no content
> hash**. The snapshot files likewise carry no `run_id` or `task_id`. The original failure
> path preserved **no explicit run-to-snapshot lineage**; the snapshot *content* remains on
> disk, but nothing machine-readable ties those files to this run. That defect has since
> been fixed in code — see the 2026-09-20 provenance-fix section above this one.

**Run:** `RUN-4e9d910742` / `TASK-a679b61436`, branch `testing` at `3c02397`, 2026-09-20
19:57:30–20:00:18 local (168s). Exit 1 with traceback, by design.

```bash
uv run python scripts/dispatch_task.py --type discovery --research-id RQ-6d9c12f4
```

**Pre-run baseline (all verified):** 391 passed / 1 skipped; Ruff clean on `.` and on
`src tests scripts`; tree clean; `origin/testing` == local. `agent_reach_check.py` exit 0
(`exa_search` off, `github` warn/usable, `arxiv` usable, `web`/Jina ok).
`gate_readiness.py --research-id RQ-6d9c12f4` exit **0** with **3** candidate URLs. The
dry run was verified genuinely inert: sha256, schema hash, all 40 schema objects and every
row count byte-identical before and after.

**What the Scout actually found.** The live path retrieved **5 distinct arXiv works** —
more than the probe's 3, because the probe passes `limit=min_sources=3` while the live run
uses the agent's `max_sources: 5`. All five classify `primary` via the unmodified
structural `arxiv-abs` signal. All five were fetched through Jina and snapshotted before
any model call:

| Work | Title |
|---|---|
| `arxiv.org/abs/1411.5062` | Optimal Mean Reversion Trading with Transaction Costs and Stop-Loss Exit |
| `arxiv.org/abs/2309.16008` | Optimal Entry and Exit with Signature in Statistical Arbitrage |
| `arxiv.org/abs/1601.04210` | Speculative Futures Trading under Mean Reversion |
| `arxiv.org/abs/1707.03498` | Mean Reversion Trading with Sequential Deadlines and Transaction Costs |
| `arxiv.org/abs/0911.1921` | Diagnostics of Rational Expectation Financial Bubbles… |

The ≥3-source bar was **cleared** (5 distinct works, re-derived independently with
`distinct_upstream_keys`, not trusted from the printed count). The run failed later, at
extraction.

**Why it failed — the validators were right.** The full bounded ladder ran and all three
attempts failed deterministic validation:

| Attempt | Model | Duration | Validator reasons |
|---|---|---|---|
| 1 | `qwen3:14b` | 51.8s | invented `research_id: R1`; omitted all 5 supplied sources; cited `<missing>` sources |
| 2 (repair) | `qwen3:14b` | 14.3s | still omitted all 5; still `<missing>` citations |
| 3 (escalation) | `qwen3.8:27b` | 69.4s | used S5, but `quote:S5: exact evidence is absent from snapshot`; `ungrounded-promotion:S5: main_claim asserts a strategy/performance claim that is not an exact passage of the snapshot` |

**This was verified as a true positive, not validator over-strictness.** The snapshots
contain **zero** standalone occurrences of `RSI` and **zero** of `ETF`. `RQ-6d9c12f4` asks
for source-supported exit rules pairing with daily ETF RSI-oversold entries; arXiv returned
continuous-time optimal-stopping theory on Ornstein-Uhlenbeck processes. The 27B's
ungrounded main_claim was papering over exactly that gap, and the Gate B extractive-support
rule blocked it.

**Attributing the failure precisely** (an earlier draft said "not a model defect and not a
lane fault", which was too generous on both counts):

- **The decisive research blocker was unsuitable source relevance.** Even a perfect
  extraction could not have produced ETF RSI exit rules from these five papers.
- **The models also produced genuinely invalid outputs** — an invented `research_id`
  (`R1`), all five supplied sources omitted, citations to `<missing>` sources, and finally
  an evidence quotation absent from the snapshot. Those are real model failures, separate
  from the relevance gap.
- **The validators and the fail-closed runtime handled those outputs correctly.** Every
  invalid output was caught and none reached a durable note.
- **The arXiv lane operated as designed.** It searched, returned real `primary`-tier
  works, and fetched them. Its *topical coverage* was unsuitable for this particular
  question — a property of what arXiv indexes, not a malfunction.

**Fail-closed behavior verified against evidence, not assumed:**
- Event trail complete and correct for the model-validation path: `dispatch_started →
  discovery_started → qwen_attempt ×3 → discovery_failed → failed_run_written →
  handler_failed → dispatch_failed` (9 events). No `discovery_candidates_rejected` —
  nothing was rejected pre-fetch.
- Per-attempt audit intact: model, duration, prompt hash, response hash, validator verdict
  and reasons recorded for all three attempts.
- `agent_tasks` row finalized `failed` with the error text; `output_path` NULL.
- Raw-note scaffold **removed** — no `Raw_Research/RQ-6d9c12f4.md` exists.
- `RQ-6d9c12f4` reset to `queued` with `raw_note_path` NULL. `RQ-c920baeb` and
  `RQ-80be8cf7` untouched and still `queued`.
- **No curator recommendation was produced or acted on.** No curator was dispatched.

**Protected tables unchanged** (before → after): `strategy_cards` 0→0, `backtests` 0→0,
`price_datasets` 0→0, `reviews` 0→0, `research_findings` 7→7, `notes` 23→23, `sources` 7→7,
`chunks` 260→260, `embeddings` 260→260, `research_questions` 7→7. No `external_*` tables.
Only `agent_tasks` 3→4 and `agent_events` 49→58 changed, as a dispatch must.

**Post-run verification:** 391 passed / 1 skipped; Ruff clean on both invocations.

**Defect found — the Failed_Runs receipt is thin on this path.** The receipt
`brain/00_Inbox/Failed_Runs/RUN-4e9d910742.md` records id, research_id, `stage:
qwen_extract`, the error string and a retry command — but its `Detail` JSON contains only
`task_id` and `created_scaffold`. It records **no source URLs, tiers, snapshot paths or
snapshot hashes**, because `_fail_closed_discovery` populated that block from
`getattr(error, "detail", {})` and `QwenValidationError` carries no `detail` attribute —
only `InsufficientUpstreamSources` does. Consequence: the five snapshots on disk are
**not referenced by the receipt or by any event**, so a reader cannot machine-verify what
was fetched. **This has since been fixed in code — see the provenance-fix section above.**

**Unstaged artifacts left for review (nothing staged, committed or pushed):**
- `brain/00_Inbox/Failed_Runs/RUN-4e9d910742.md`
- `brain/00_Inbox/Source_Snapshots/2026-09-21/` — 5 files whose **content** remains on
  disk, each self-describing with url/title/captured_at/content_hash. Their association
  with `RUN-4e9d910742` is **probable, not established**: no artifact records the linkage
  (see the attribution limitation in the provenance-fix section).

**Date skew, not an inconsistency:** the run executed on **2026-09-20 local time**
(19:57–20:00), while the snapshot directory is named **`2026-09-21`** because snapshot
paths are derived from UTC (`snapshot_relative_path` uses `datetime.now(UTC)`). The
`agent_events` timestamps are UTC too, which is why they read `00:57–01:00`.

**Limitations.** (a) One run of one question; Phase 6's exit gate requires all three child
runs and remains **incomplete**. (b) A passing extraction was never demonstrated, so the
success path of the production Scout is still unproven end to end. (c) The question-to-
literature relevance gap is unresolved and is not fixable by retrying the same lane.

**Next decision is Jason's.** The options, none of which were taken here: (1) accept the
relevance gap as the finding and widen the lane set toward documentation/practitioner
sources that actually discuss RSI exit rules; (2) authorize a receipt-completeness fix so
`QwenValidationError` carries candidate evidence into `Failed_Runs`; (3) retain sources
manually through the external intake and verify their upstream works; (4) re-run the same
question unchanged, which on this evidence would be expected to fail the same way. Do
**not** lower `MIN_UPSTREAM_SOURCES` or relax the extractive-support rule — the bar was
cleared; the grounding was not.

## Gate D partially unblocked — arXiv lane added, no child run (2026-09-19)

**Gate D remains NOT executed.** One of three child questions is now probe-ready; the other two are honestly still blocked. PROP-003 was committed at `cddd3d84d3849e445c2d227f824bb5b9206c5c85` and pushed to `origin/testing`, followed by the documentation commit `30630a0cb8d4559372ca6430812ceb78cd20fd91`. `origin/testing` was fetched and verified at `30630a0`, matching local `HEAD`. `main` remains untouched at `51979f6`; nothing was merged and no branch was created. Post-change verification on the committed tree: **391 passed, 1 skipped**, Ruff clean on `.` and on `src tests scripts`, working tree clean, and `db/brain.sqlite` unchanged at sha256 `43fa24b0c7c7e92d08760404774cb872d5b4530080d8a7ac6a677bafed3069bb`; the production invariants below remain unchanged.

**Starting state, verified live at `51979f6`:** `gate_readiness.py` exited **4** with **0 candidate URLs** for all three children. Only `search_exa` and `search_github` could turn a question into URLs (`agent_reach.py`, `SEARCH_CHANNELS = ("exa_search",)`). Exa is `off` by Jason's decision; GitHub is authenticated and working but searches *code repositories* — `gh search repos "RSI exit rules backtest"` returns `[]`. The plan's "web search" was never implemented as search: `fetch_web(self, url)` takes one already-known URL and has no query parameter. RSS/YouTube have no search code at all. `SEARCH_LANES` was decorative — `operational_lanes()` was never called from `src/`.

**What changed (PROP-003, approved before implementation).**
1. **`src/quant_brain/discovery/arxiv_search.py`** — an independent zero-account lane over arXiv's free Atom API, with its own hardened transport: fixed HTTPS host, explicit timeout and User-Agent, bounded read, DOCTYPE/entity rejection, redirects refused outright, strict arXiv-host validation on every identifier, and canonical `https://arxiv.org/abs/<id>` output. A valid empty feed returns `[]`; malformed or oversized responses raise. It is **not** gated on the Agent Reach `web`/Jina channel — conflating the two would misreport *why* discovery failed.
2. **One deterministic query transformation** (`build_arxiv_query`) applied identically to every question, recorded in the run and in any receipt. **No per-question tuning.** A three-phrase conjunction returned 0 for all three questions; two phrases is the measured rule.
3. **The ≥3-source bar is now enforced in the pipeline.** It previously lived only in `gate_readiness.py` (a read-only probe) and Phase 6 prose — `executor.py` checked only `if not sources`, i.e. ≥1. It is now counted over **distinct normalized upstream works**, not `len(sources)`, with one shared `MIN_UPSTREAM_SOURCES` constant imported by the probe so the two cannot drift.
4. **Sparse results are quarantined, never promoted.** Below the minimum the run fails closed **before** any raw note is written, and the existing `_write_failed_run_note` path records canonical URLs, tiers, snapshot paths/hashes, actual/required counts, the generated query and follow-up guidance — with **no `raw_saved` note and no curator recommendation**.

**Verified results.** **391 passed, 1 skipped**; Ruff clean on `.` and on `src tests scripts`.

| Question | unique URLs | `gate_readiness` exit |
|---|---|---|
| RQ-6d9c12f4 exit rules | 3 | **0 — ready** |
| RQ-c920baeb max holding period | 1 | 4 — still blocked |
| RQ-80be8cf7 costs/slippage | 1 | 4 — still blocked |

RQ-6d9c12f4's three candidates are distinct `primary`-tier works (`arxiv.org/abs/1411.5062`, `/2309.16008`, `/1601.04210`) from the generated expression `all:"mean reversion" AND all:"exit"`. **No query was tuned to produce this.** The two blocked questions are a finding about reachable literature, not a lane fault — arXiv indexes academic preprints, and "maximum holding-period caps" and practitioner cost conventions are largely documented elsewhere.

**Independent review: APPROVED**, after finding two real defects in the first implementation, both fixed and regression-tested:
- **P2 — `/pdf/` and `/abs/` of one paper counted as separate works**, so three links to a single paper satisfied the floor of 3. `canonical_abs_url` now reduces both renderings (and a `.pdf` extension) to one identity.
- **P2 — a bare trailing `v` split one work in two** (`v\d+$` required a digit). Now `v\d*$`.
- P3s also fixed: an arXiv transport failure no longer reads as "the literature is empty" (the reason is retained and reported), and the generated query is now recorded even when a caller injects its own `search_fn`. Redirects are refused outright rather than checked at the final hop, since `geturl()` cannot see a chain that leaves the host and returns.

**Production invariants unchanged:** `strategy_cards`/`backtests`/`price_datasets`/`reviews` all **0**; no `external_*` tables; all three RQs still `queued` with `raw_note_path NULL`; `db/brain.sqlite` byte-identical after every readiness probe.

**Known limitations.** (a) arXiv is academic-only, so documentation and practitioner questions may still find nothing — that is the honest reason two questions remain blocked. (b) The lane is a *search* addition only; caps, tiers, validators, the curator threshold and snapshot-before-model are untouched. (c) A run reaching exactly 3 sources still has to pass every downstream gate; probe-ready is not evidence.

**Next decision is Jason's:** whether to authorize a single Research Scout child run for `RQ-6d9c12f4` only. That is a separate authorization and was deliberately not taken here.

## External intake merged to `main` (2026-09-19)

The independently approved external-research intake and its documentation correction were fast-forwarded to `main` at `75b51c9` and pushed. `main` and `testing` are being kept synchronized; Gate D remains blocked and was not executed. The next authorized activity requires a new bounded Gate D brief and prerequisite check, not a strategy or backtest.

## P1 quotation defect corrected and re-reviewed — committed to `testing` (2026-09-19)

The substring-matching blocker is fixed, independently re-reviewed and **APPROVED**, and the intake feature is committed on `testing`. **350 passed, 1 skipped**; Ruff clean on `.` and on `src tests scripts`.

**What the bug was.** `normalized()` collapsed whitespace but applied no token boundaries, so `quote in normalized(body)` was a raw substring test. `Exit when RSI > 5` matched source text `Exit when RSI > 50 or after 10 trading days.` Reproduced end-to-end: `quote_match`/`full_rule_match` true, `approve_scope` accepted, and the curator handoff carried `evidence: "Exit when RSI > 5"` — a threshold the source never states. Not automatic promotion (an attributed reviewer must approve scope), but it defeated the exact-quotation safeguard, whose whole promise is that evidence is the verbatim source span. Truncation at *either* edge did it, not only the reported prefix case.

**Why it mattered in plain terms.** Exiting at RSI > 50 is an ordinary mean-reversion exit; exiting at RSI > 5 would exit on nearly every bar — a different strategy. The one number defining the rule could be silently wrong in material handed to the curator while still passing an "exact quotation" check.

**The correction.** A boundary-safe `source_span()` helper in `external_verification.py`, used by all three matching sites: verification, `approve_scope` and `handoff`. A span must begin and end on a token boundary; a severed word or number is refused. Clean partial quotation stays legitimate (`Exit when RSI > 50` ends on a boundary and still matches). Text matching stays separate from full-rule and contextual assessment — `full_rule_match` remains its own `claim == quote` check, and reviewer scope judgement is unchanged.

**Stale cache closed.** `verify_claim` returns a cached `evaluations` row *before* matching runs, and `UNIQUE(claim_id,fetch_id)` prevents a corrected row replacing it, so a catalog verified under the old rule keeps `quote_match: true` permanently. Fixing the matcher alone was therefore insufficient: `approve_scope` and `handoff` now **re-derive** the check from the pinned snapshot instead of trusting the stored flag. Cached rows stay immutable (append-only history preserved, no schema change). A stale flag can still *display* as matched; it cannot approve or promote. `verify --force --allow-network` refreshes recorded values.

**Two further defects were found in the fix itself by re-review, and corrected.** (1) The first boundary rule was asymmetric — it guarded a quote ending in `.`/`,` before a digit but left the mirror case open, so `Threshold is 1` matched `1,250` (a 1250× misstatement) and `Win rate 0` matched `0.55`. Tellingly, `Threshold is 1,` was rejected while the *more* misleading `Threshold is 1` passed. Now symmetric over `.,:/%-` plus typographic separators, severing only when digits sit on both sides. (2) The character class was ASCII-only, letting the original defect back in via fullwidth (`５０`→`５`) or Arabic-Indic digits; now `str.isalnum()`, so the alnum test and `str.isdigit()` agree across scripts. The em dash is deliberately **not** a joiner: a dash census over the 18 real snapshots found en dash binding numeric ranges 25 times and em dash 0 times, while including it falsely rejected `It rose 20` from `It rose 20— then fell.`

**Verification.** 350 passed/1 skipped; Ruff clean. Recomputing all 18 evaluations in the real demo catalog under the corrected matcher gives **identical verdicts** — 4 quote matches, 0 full-rule matches, zero changed — so `acceptance.json` counts are unchanged and no legitimate quotation was penalized. Handoff on an isolated copy returns `[]`. All mutation-capable work used a scratchpad copy; `C:/Users/jason/quant-agent-brain-intake/exit-rules-final/external.sqlite` is byte-identical (sha256 `20ebc695…`). Production untouched: `strategy_cards`/`backtests`/`price_datasets`/`reviews` all 0, no `external_*` tables in `db/brain.sqlite`, `RQ-6d9c12f4` still `queued` with `raw_note_path NULL`, `gate_readiness.py --research-id RQ-6d9c12f4` still exits **4** with `brain.sqlite` byte-identical after the run.

**Known limitations.** (a) An em-dash-bound numeric range truncates undetected — a documented trade-off with 0 observed instances in the corpus. (b) `source_span` is a boundary check only: clipping a complete, meaning-bearing token (`Exit when RSI > 50` out of `...50 unless volume is below average`) matches by design; the safeguard there is `full_rule_match` plus the attributed reviewer's scope judgement, not the matcher. (c) Review attribution is a name, not authentication. **Gate D is not advanced and was not executed.**

## Verified closeout / limits

- Only `main` and `testing` exist. The intake feature and documentation correction were **merged to `main` and pushed** at `75b51c9` after independent re-review and approval.
- Final verification: **350 passed, 1 skipped**, Ruff clean. (The 321/1 figure below predates the P1 correction and its regression tests.)
- Canonical demo: `C:/Users/jason/quant-agent-brain-intake/exit-rules-final/acceptance.json`. All three PDFs extracted; 18 claims/citation leads, 17 distinct targets (not independent works). Counts of fetch outcomes below are per claim, not network calls. Final catalog reuses hash-checked snapshots from the earlier live run with original timestamps and reuse provenance. Both reimport and offline replay verified idempotent.
- 47 protected production files, question rows and tracked entity counts unchanged. No trusted promotion, Gate D, strategy or backtest executed.
- Automatic parsing is conservative: ChatGPT's unstructured sections remain citation leads requiring manual claim-to-source mapping. Four quote matches do not constitute four supported full exit rules. Handoff is empty; no evidence threshold was relaxed.
- Review role is attributed, not authenticated: this local CLI cannot establish that a reviewer is human. Source matching preserves operators but does not prove context or profitability. Do not call this production-ready before an independent review.
- Workflow and small learning note: `brain/_system/external_intake_workflow.md`.


> **External research intake implemented locally 2026-09-18 (branch `testing`, not merged).** A bounded retention lane for manually-collected external reports. **321 passed, 1 skipped**; Ruff clean. **Gate D was NOT executed and is NOT advanced.** `RQ-6d9c12f4` remains `queued` with `raw_note_path NULL`; `strategy_cards`/`backtests`/`price_datasets`/`reviews` all remain 0; `db/brain.sqlite` has no `external_*` tables; `scripts/gate_readiness.py --research-id RQ-6d9c12f4` still exits **4**.
>
> **What it does.** `scripts/external_intake.py` retains original PDFs, native `pypdf` text, per-report citations, deduplicated source targets and an append-only per-claim review history in an **isolated workspace database outside the repository and vault** (the workspace guard refuses any path inside either). Retention is not trust: a claim enters as `unreviewed_lead`, a deterministic verifier can only move it to `partially_supported`/`unresolved`/`blocked`, and **only an attributed reviewer scope review can set `supported_in_scope`** — which is the sole state the curator handoff will offer. The handoff builds its payload from the exact verified source span, not the report's transcription, and still has to pass the existing unmodified `promotion_block_reason`.
>
> **Real run over Jason's three reports:** 3 reports, 18 claims, **17 distinct targets** (ChartSchool is cited by 2 reports and counted once — repeated citation is not corroboration). Live verification: 13 fetched, 1 access-blocked, 3 content-rejected, 1 no-URL. **4 quotations located, 0 full-rule matches, so the curator handoff is correctly empty.** Two DOI/SSRN sources sit behind access walls and are parked with reasons, never circumvented. Re-importing all three is a no-op; re-verifying without `--allow-network` replays from cached snapshots in <1s.
>
> **Reproduce:**
> ```
> uv run python scripts/external_intake.py --workspace C:/tmp/ext_demo import "<pdf>" --provider <name> --research-id RQ-6d9c12f4
> uv run python scripts/external_intake.py --workspace C:/tmp/ext_demo verify --allow-network --limit 20
> uv run python scripts/external_intake.py --workspace C:/tmp/ext_demo leads
> uv run python scripts/external_intake.py --workspace C:/tmp/ext_demo handoff
> ```
>
> Governance: **PROP-002** in `brain/_system/plan/plan_change_proposals.md` (accepted, authorized before implementation) plus the §5 amendment in `PLAN.md`. Still needing separate approval: OCR/further extraction deps, relaxing the ≥3-source bar, and any production promotion.
>
> **Gate D attempted 2026-09-17 — BLOCKED, no child question executed.** Prerequisites were checked before any run. `RQ-6d9c12f4`, `RQ-c920baeb`, `RQ-80be8cf7` remain `queued` with no raw note; `strategy_cards`/`backtests`/`price_datasets`/`reviews` all remain 0. **284 passed, 1 skipped**; Ruff clean. Work is on `testing`, **not merged to `main`**.
>
> **Three code defects found and fixed.** (1) `default_runner` decoded subprocess output with the locale codec (`cp1252`) while `agent-reach doctor --json` emits UTF-8 — the `UnicodeDecodeError` fired on subprocess's reader thread, nulled `stdout`, and surfaced as a misleading `TypeError`. Every live discovery call was broken on this machine. (2) The adapter looked for channels `"search"`/`"exa"`; the real doctor key is `exa_search`, so the Exa lane could never be selected. The recorded fixture repeated the same invented names — which is why a green suite carried this through a whole gate. (3) `plan_queries` sent the full 440-character question to `gh search`, which rejects long queries as malformed, misreporting a query error as an empty result.
>
> **The blocker is not a defect and was not fixed:** `exa_search` reports `status: "off"` — mcporter installed, Exa not configured, no config and no `EXA_*` env vars. That is Jason's decision; project code must never call `agent-reach`/`mcporter configure`.
>
> **Say the blocker precisely.** It is *not* "no usable lane". `github` is `warn`, which the code correctly treats as usable, so discovery would run **GitHub-only** — the sweep Gate C exists to prevent. The blocker is that the only lane able to answer these questions is `off`, GitHub returns **0 results for all three children**, and Phase 6 requires **≥3 upstream sources per raw note**.
>
> **Reproduce:** `uv run python scripts/gate_readiness.py --research-id RQ-6d9c12f4` → exit **4**. Read-only: no fetch, no snapshot, no model, and `db/brain.sqlite` is byte-identical afterwards. The general `agent_reach_check.py` exits **0**, correctly — GitHub genuinely is usable, and a lane is not unhealthy merely because it suits a question poorly. **Do not mistake that 0 for Gate D readiness.**
>
> **Gate C verified 2026-09-16.** Bounded source acquisition now discriminates by credibility before spending a fetch or a model call. `discovery/source_quality.py` makes the written Tier A/B/C/D policy executable (structural host/path signals + allowlists + a commercial-intent reject detector that runs first); `discovery/acquisition.py` adds normalize → dedupe → classify → rank → budget plus a 600-char/120-word content floor. The central unlock: live discovery previously hardcoded `source_quality="discovery-only"` while the curator only promotes `primary`/`practitioner`, so the live path could never promote anything it found. Tiers are now assigned discovery-side, the only correct placement given the validators' protected-field guard. **269 passed, 1 skipped**; Ruff clean on both invocations. PR #3 was merged first (`2a876f7`). The three child questions remain **queued** — Gate C ran none of them.
>
> Acceptance demonstration: `uv run python scripts/acquisition_report.py` — zero network, finds 3 primary + 1 practitioner, rejects promotional material pre-fetch and a cookie banner post-fetch/pre-model, collapses a cross-channel duplicate, exits non-zero on any failed check.
>
> **Gate D is next and requires Jason's explicit authorization.**
>
> **Gate B verified 2026-09-11.** The production live Research Scout passes fetched snapshots through `quant_brain.llm.qwen_call`: qwen3:14b at temperature 0/schema mode, deterministic validation, exactly one 14B repair, qwen3.8:27b escalation, then structured fail closed. Every attempt records model, duration, prompt/response SHA-256 hashes, and validator verdict/reasons in `agent_events`. Durable promotion requires fully extractive main claims and strategy rules; late write failures restore/delete notes consistently; dispatcher validation failures finalize tasks as failed. Hermetic and adversarial tests pass (**201 passed, 1 skipped**), with full-tree/scoped Ruff clean. Phase 6 remains pending; Gate C is next.
>
> **Gate A verified 2026-09-07.** Desktop `main` was safely fast-forwarded from `f053341` to merged PR #1 commit `feaa84e86db5b435cf12a21d65e7e924cd116bbb`, then the pre-existing tracked and untracked work was reapplied. The exact backup directory is `C:\Users\jason\quant-agent-brain-gate-a-backup-20260907-171959`; it contains `tracked-worktree.patch`, `tracked-index.patch`, `untracked.tar.gz`, `untracked-list.txt`, `head-before.txt`, `status-before.z`, and related inventory files. The backup branch and retained stash also preserve the pre-integration state.
>
> The reviewed PR implementation is the production Scout path: registry/dispatcher → `quant_brain.discovery` → recommendation only. Pre-existing untracked `src/quant_brain/research/live_*.py` and dashboard files remain preserved as experimental local work; they are not a competing accepted architecture.
>
> `RQ-66078766` remains an **experimental audit receipt**, including raw research, rejected curator review, source snapshots, failed-run material, and decision log. The real child queue remains untouched: `RQ-6d9c12f4`, `RQ-c920baeb`, and `RQ-80be8cf7`. Do not execute them until the later roadmap gate is explicitly approved.
>
> Gate A verification: `uv sync --extra dev` succeeded; full pytest passed (`149 passed, 1 skipped`); Ruff passed with immutable failed-run audit artifacts explicitly excluded in `pyproject.toml` (maintained `src`, `tests`, and `scripts` remain lint-clean); discovery registry and child dry-run resolved to `research_scout`; Agent Reach health was inspectable, with web/RSS/Bilibili healthy and optional-channel warnings/off states. No research, strategy card, backtest, paper trade, remote push, or remote merge was performed.
>
> **Read `PLAN.md` first.** It remains the master architecture source of truth. Use `.hermes/plans/2026-09-07_171423-research-to-paper-trading-roadmap.md` for the gated execution sequence, and do not silently rewrite master phases.

Use this file to resume work in a new Hermes session without reloading the full conversation.

## Project Path

`C:\Users\jason\OneDrive\Desktop\quant-agent-brain`

## Current Goal

Build a budget-first, local-first agentic quant research/backtesting second-brain system that showcases AI/ML skills without overengineering or creating an agent for every tiny task.

Core idea:

```text
research structure + RAG structure + controlled work packets
```

## User Preferences For This Project

- Move slowly, one verified step at a time.
- Avoid overengineering.
- Do not delegate an agent for every small thing.
- Prefer local/free tools first.
- Use paid/cloud models only for escalation/review later.
- Build like a serious quant research workflow: evidence first, backtests second, review before any paper trading.
- No live trading.

## What Has Been Built

### 1. Project foundation

- `pyproject.toml`
- `README.md`
- `AGENTS.md`
- `.gitignore`
- `.env.example`
- `src/quant_brain/`
- `tests/`

Python uses `uv`.

Latest verified test count:

```text
396 passed
1 skipped
```

(Was 391/1 before the 2026-09-20 provenance fix added 5 regression tests.)

### 2. SQLite database

Database path:

```text
db/brain.sqlite
```

Schema/init code:

```text
src/quant_brain/db/schema.sql
src/quant_brain/db/init_db.py
```

Important tables:

```text
notes
sources
chunks
embeddings
research_questions
research_findings
strategy_cards
price_datasets
backtests
metrics
reviews
agent_tasks
retrieval_log
```

### 3. Market data foundation — historical claim, not current capability

Earlier handoffs claimed market-data downloader/registry modules and downloaded SPY/QQQ/IWM data. Those modules are not present in the reconciled source tree, and the current database has **`price_datasets = 0`**. Do not infer that usable price files or registrations exist. Roadmap **Gate F** owns restoring reproducible files, provider/date/calendar/adjustment metadata, checksums, and SQLite registrations before any backtest.

### 4. Research intake system

Files:

```text
src/quant_brain/research/intake.py
scripts/research_intake.py
brain/_system/research_intake_workflow.md
```

Creates research questions and briefs.

Existing research task:

```text
RQ-4ddd4ef4
Question: Find useful sources for ETF mean reversion strategies and summarize only methods that can be tested with daily SPY QQQ IWM data
Status: curated
```

### 5. Research Scout runner/executor

Files:

```text
src/quant_brain/research/scout_runner.py
scripts/research_scout_runner.py
src/quant_brain/research/executor.py
scripts/research_executor.py
agents/research_scout.md
```

Output raw research note:

```text
brain/00_Inbox/Raw_Research/RQ-4ddd4ef4.md
```

The first executor is intentionally conservative and deterministic, not a web crawler yet.

### 6. Curator promotion/executor

Files:

```text
src/quant_brain/curation/promotion.py
scripts/curator_promotion.py
src/quant_brain/curation/executor.py
scripts/curator_executor.py
agents/knowledge_curator.md
```

Curated `RQ-4ddd4ef4` and promoted 5 source notes:

```text
brain/01_Sources/web/SRC-df1769724d-relative-strength-index-rsi-investopedia-overview.md
brain/01_Sources/docs/SRC-2830f8cd41-quantconnect-glossary-look-ahead-bias.md
brain/01_Sources/docs/SRC-7691c731ac-quantconnect-glossary-survivorship-bias.md
brain/01_Sources/docs/SRC-26d92ac325-backtesting-py-documentation.md
brain/01_Sources/docs/SRC-022c5bed68-vectorbt-documentation.md
```

Curator review:

```text
brain/00_Inbox/Curator_Reviews/RQ-4ddd4ef4-curated.md
```

### 7. Markdown indexer

Files:

```text
src/quant_brain/indexing/markdown_indexer.py
scripts/index_markdown.py
brain/_system/markdown_indexer_workflow.md
```

Indexes Markdown notes into:

```text
notes
chunks
```

Current indexed count at last run:

```text
23 Markdown files
260 chunks
```

### 8. Embedding indexer

Files:

```text
src/quant_brain/indexing/embeddings.py
scripts/embed_chunks.py
brain/_system/embedding_indexer_workflow.md
```

Uses real local semantic embeddings through Ollama:

```text
nomic-embed-text
768 dimensions
```

The deterministic `local-hash-embedding-v1` backend remains available only as an offline/test fallback.

Current embedding count at last run:

```text
260 embeddings
0 pending chunks
```

Later scaling options:

```text
Ollama mxbai-embed-large
sentence-transformers/all-MiniLM-L6-v2
LanceDB or Chroma
```

### 9. Retrieval context builder

Files:

```text
src/quant_brain/retrieval/context_builder.py
scripts/build_context.py
brain/_system/retrieval_context_builder_workflow.md
```

Builds an agent-ready evidence packet:

```text
query
source path
heading
chunk id
score
chunk text
rules to cite evidence and avoid guessing
```

### 10. Agent work packet builder

Files:

```text
src/quant_brain/agents/work_packet.py
scripts/build_work_packet.py
brain/_system/agent_work_packet_builder_workflow.md
```

Creates work packets with:

```text
agent role
specific task
retrieved context
allowed read paths
allowed write paths
output contract
guardrails
```

Latest sample packet:

```text
brain/00_Inbox/Work_Packets/WP-3818c6a760-knowledge_curator.md
```

It asked the Knowledge Curator to review whether lookahead bias should update the validation checklist.

### 11. Deterministic Work Packet Executor

Files:

```text
src/quant_brain/agents/executor.py
scripts/execute_work_packet.py
tests/test_work_packet_executor.py
brain/_system/work_packet_executor_workflow.md
```

The first executor is intentionally narrow and deterministic. It:

```text
parses one bounded packet
→ verifies retrieved evidence
→ enforces project-relative allowed write paths
→ writes a cited Markdown result
→ validates path + heading citations
→ updates agent_tasks running/completed/failed state
```

Unsupported tasks fail closed instead of receiving a fabricated generic answer. No local or cloud model is called yet.

Verified real execution:

```text
Packet: WP-3818c6a760
Status: completed
Output: brain/00_Inbox/Curator_Reviews/WP-3818c6a760-result.md
Citations validated: 1
```

The Markdown indexer was also hardened for repeated identical heading/text sections inside one note. Duplicate occurrences now receive distinct chunk IDs instead of raising a SQLite uniqueness error.

### 12. Canonical Pre-Backtest Validation Checklist

File:

```text
brain/_system/pre_backtest_validation_checklist.md
```

The completed work-packet recommendation was reviewed and promoted into a short system checklist. Version 1 contains one evidence-backed gate only:

```text
confirm all signal inputs were available at decision time
→ close-based signals execute no earlier than the next bar unless timing proves otherwise
→ failing configurations stop before performance is reported
```

The checklist cites the curated QuantConnect lookahead-bias source. It intentionally does not add speculative validation rules yet.

### 13. First Strategy Door

File:

```text
brain/02_Strategy_Doors/DOOR-etf-mean-reversion.md
```

The door maps the daily SPY/QQQ/IWM ETF mean-reversion family without creating a strategy card. It currently identifies RSI oversold rebound as the only candidate with enough support for another focused research pass.

### 14. Focused RSI Definition Research

Research task:

```text
RQ-17a4103d
Status: curated
```

New curated sources:

```text
brain/01_Sources/docs/SRC-1ea110cb46-stockcharts-chartschool-relative-strength-index-rsi.md
brain/01_Sources/docs/SRC-89c682a686-ta-lib-documentation-relative-strength-index-rsi.md
```

This pass captured Wilder's formula and bounded the entry-condition research space to:

```text
RSI(14) below 30 at the close
RSI(2) below 20 at the close
next-bar entry for either candidate
```

It did not find enough evidence to approve an exit rule or maximum holding period, so no strategy card or backtest was created.

A follow-up task was originally queued, then used only by the preserved experimental
live-research work described below. It is not a production acceptance receipt:

```text
RQ-dd7da469
Question: Find source-supported exit conditions, maximum holding periods, timing/regime risks, and fixed cost assumptions for the bounded RSI candidates.
Current artifact status: rejected (experimental history; not accepted)
```

### 15. Agent Reach Live-Research Connection

Canonical repository:

```text
https://github.com/Panniantong/Agent-Reach
```

Verified local connection:

```text
Version: 1.5.0
Clone: C:/Users/jason/Projects/Agent-Reach-review
Executable: C:/Users/jason/.agent-reach-venv/Scripts/agent-reach.exe
Obsidian skill: C:/Users/jason/OneDrive/Desktop/memory_vault/Agents/skills/agent-reach/SKILL.md
```

Agent Reach is now named in `AGENTS.md`, the Research Scout role, and generated Research Scout prompts. It is used as a discovery router for web pages, YouTube transcripts, GitHub, RSS, and social leads. Durable notes cite upstream sources rather than Agent Reach itself.

### 16. Cross-Asset Quant Research Universe and Quality Gate

Files:

```text
brain/80_Summaries/quant-research-universe.md
brain/_system/research_source_quality_policy.md
brain/_system/citations/quant-universe-ledger.json
```

The grounded scan used official institutional research, trading-firm pages, practitioner interviews, and YouTube transcripts from AQR, Man Group/Man AHL, Two Sigma, HRT, Jane Street, Wintermute, BlackRock, Aspect Capital, and J.P. Morgan.

The project is explicitly open to:

```text
equities and ETFs
futures / rates / FX / commodities
options and volatility
crypto and digital assets
factor/style premia
systematic macro and trend following
statistical arbitrage / relative value / mean reversion
market making and liquidity
alternative data / machine learning
portfolio construction and risk allocation
```

This is a research universe, not an approval list. The curator now promotes only `primary` or `practitioner` source-quality items; `discovery-only` material can create leads but cannot independently enter durable source notes. The policy rejects untraceable returns, screenshots without rules/data/costs, copied summaries, hidden assumptions, and invented citations.

### 17. Local Qwen Research Evaluation

Files:

```text
src/quant_brain/research/model_eval.py
scripts/evaluate_research_model.py
tests/test_research_model_eval.py
brain/00_Inbox/Model_Evaluations/qwen-research-evaluation.md
brain/00_Inbox/Model_Evaluations/qwen3-14b-research-eval-v4.json
brain/00_Inbox/Model_Evaluations/qwen3.8-27b-research-eval-v2.json
brain/_system/local_qwen_research_policy.md
```

Models and hardware:

```text
qwen3:14b       9.3 GB
qwen3.8:27b    17 GB
GPU: NVIDIA GeForce RTX 5070, 12 GB VRAM
```

Final bounded evaluation results:

```text
qwen3:14b      3/3 passed, 17.740 seconds total, 2 cases repaired
qwen3.8:27b   3/3 passed, 123.972 seconds total, 0 cases repaired
```

The cases tested missing-evidence honesty, slop rejection, and cross-asset source-grounded mapping. A stronger validator caught a direct contradiction in an early 14B answer; one bounded repair corrected it. Therefore 14B is approved only as the default evidence-processing worker behind schema, source-ID, validator, and one-repair gates. The slower 27B model is the escalation/reviewer.

### 18. Experimental Local History — Not Production

The following files and run records are preserved because they are useful audit history.
They were pre-existing untracked local work when Gate A was reconciled. They do **not**
replace, extend, or prove acceptance of the registry/dispatcher architecture in `PLAN.md`.

#### Experimental live-research prototype

Files:

```text
src/quant_brain/research/live_discovery.py
src/quant_brain/research/live_worker.py
src/quant_brain/research/live_executor.py
scripts/live_research_executor.py
brain/_system/live_research_executor_workflow.md
```

The prototype attempted this bounded flow:

```text
Agent Reach health check
→ upstream web search
→ deterministic dedupe/ranking
→ Jina source snapshots + hashes
→ bounded Qwen 14B extraction
→ exact source/URL/quote validation
→ one repair
→ Qwen 27B escalation
→ raw research note
→ curator gate
→ ordered SQLite events
```

Experimental rejected run (not an acceptance run):

```text
Research: RQ-dd7da469
Run: RUN-rsi-exit-live-v5
Sources fetched: 3
Qwen 14B: two exact-quote validation failures
Qwen 27B: passed validation
Curator: rejected all 3 discovery-only sources
```

The rejection is retained as quality-gate evidence only. It did not accept the Scout,
promote sources, resolve the RSI evidence gaps, or authorize another stage.

#### Experimental operations dashboard

Files:

```text
src/quant_brain/ops/events.py
src/quant_brain/ops/dashboard.py
scripts/serve_agent_dashboard.py
ui/agent_dashboard.html
brain/_system/agent_operations_dashboard_workflow.md
brain/07_Decision_Log/DEC-agent-operations-dashboard.md
```

Historical prototype launch command:

```bash
uv run python scripts/serve_agent_dashboard.py
```

Local URL:

```text
http://127.0.0.1:8765
```

This dashboard is preserved experimental UI. It is not the production interface, not a
Gate A deliverable, and not part of the canonical execution path.

## Canonical Current Architecture

`PLAN.md` is authoritative. Gate A recognizes only this production Scout path:

```text
agent registry + typed capability
→ dispatcher selects research_scout
→ quant_brain.discovery performs the bounded discovery task
→ validated output
→ recommendation only
→ harness/human decides whether any later task is authorized
```

The `src/quant_brain/research/live_*.py` modules, experimental dashboard, and their
workflows are outside that path. Do not package, promote, or describe them as current
production. As of 2026-09-16 they live on `preserve/live-research-and-dashboard-20260916`
and are no longer in the working tree — being on a branch does not make them accepted.

## Merged Checkpoint (2026-09-15)

Gate B was merged to `main` as `fb3ecc3` (PR #2). Local `main` is synchronized with it by
fast-forward; the merge introduced no upstream edits, so the accepted Gate A/B code is
byte-identical to the reviewed checkpoint. Recovery tag: `pre-gatec-reconcile-20260915`.

Verified after reconciliation: 210 passed / 1 skipped, Ruff clean on both invocations,
child RQs queued, `RQ-66078766` rejected, and `strategy_cards` / `backtests` /
`price_datasets` / `reviews` all zero. (That 210 included 13 experimental tests — see
the test-baseline note below.)

### Deliberately uncommitted work — resolved 2026-09-16

The working tree is now clean. Everything previously held back has been classified and
routed. Decision note:
[brain/07_Decision_Log/DEC-2026-09-16-phase-3-indexing-checkpoint.md](brain/07_Decision_Log/DEC-2026-09-16-phase-3-indexing-checkpoint.md).

- **Phase 3 semantic-RAG edits** — reviewed on their own merits and **accepted** on
  `phase-3/indexing-and-retrieval-eval` (`b236175`), PR open and **awaiting Jason's approval;
  not merged**. Excludes `Source_Snapshots` from the index, removes a retrieval fixture that
  was *unreachable* (its target lives in the excluded `_system/`, so it could never be
  retrieved), and makes a dimension mismatch raise instead of returning an empty list.
  Re-verified: Recall@1 0.71, Recall@5 1.00, MRR 0.790 across 7 now-reachable fixtures.
- **Gate C-adjacent scaffolding** — `src/quant_brain/research/live_{discovery,executor,worker}.py`,
  `src/quant_brain/ops/dashboard.py`, `ui/`, `scripts/{live_research_executor,serve_agent_dashboard,gate_b_live_smoke}.py`
  and their 4 test files. **Preserved** on `preserve/live-research-and-dashboard-20260916`
  (`7a7209e`), pushed. Audit history only — never reviewed in PR #2, not the accepted
  architecture, not to be merged.
- `.hermes/` and `src/quant_agent_brain.egg-info/` are now gitignored; the egg-info was
  untracked with `git rm --cached` (files remain on disk). It is regenerated by every
  editable install and produced diff noise unrelated to any real change.

Promoting any preserved work into production requires its own reviewed change, not a
carry-over from this reconciliation.

### Test baseline — read this before comparing numbers

The **210 passed** figure recorded for the Gate B merge included 13 tests from the
then-untracked experimental files. The tracked-only baseline at that commit was
**197 passed, 1 skipped**. With the Phase 3 branch's `tests/test_retrieval_eval.py` (2 tests)
the current tracked baseline is **199 passed, 1 skipped**. The experimental tests now live on
the preserve branch and no longer inflate a run on `main`.

### Known issue — `retrieval_eval.py --compare` is broken

It compares the semantic backend against the `local-hash-embedding-v1` baseline, but the hash
vectors are absent from `db/brain.sqlite` (only `nomic-embed-text@768`), despite the Phase 3
design note saying to keep them for this purpose — most likely lost to the documented
re-index-drops-embeddings behavior. **Pre-existing, not caused by the Phase 3 branch**; it
previously failed *silently* as recall 0.00 and now raises. Fixing it requires re-embedding
every chunk under the hash model, which writes to the database — deliberately not done. The
single-model run that gates Phase 3 is unaffected.

## Gate Status and Resume Rule

Gate A reconciliation, Gate B / master-plan Phase 5, and Gate C are complete. **Gate D was
authorized and attempted on 2026-09-17, and is blocked on an unconfigured search lane — not
on authorization.** No child question was executed; all three remain `queued`.

**Re-attempting Gate D requires a usable search lane that can answer documentation and
academic questions.** That is Jason's decision: Exa is a third-party service, and he has
said to enable it only if it is genuinely free with no API key. Project code must never run
`agent-reach`/`mcporter configure`. Before assuming the blocker still stands, run
`uv run python scripts/gate_readiness.py --research-id RQ-6d9c12f4` — exit 4 means still
blocked, exit 0 means the lanes can now reach the minimum.

When a lane is available, Gate D runs the three child research questions one at a time, in
order: `RQ-6d9c12f4` (exit rules), `RQ-c920baeb` (maximum holding periods), `RQ-80be8cf7`
(commission/slippage). Each needs its own dispatch, snapshot set, validated raw note, event
trail, and a **separately dispatched** curator verdict, with tests run before the next child
starts. Zero promotions is an acceptable outcome.

Nothing here authorizes a strategy card, market-data download, backtest, or paper trading.
Follow the explicit gated roadmap and do not infer a production step from the experimental
run history. Until Gate D is authorized, preserve `RQ-6d9c12f4`, `RQ-c920baeb`, and
`RQ-80be8cf7` in `queued` without executing them.

### Acquisition lane status (Gate C)

| Lane | Status | Notes |
|---|---|---|
| Exa via mcporter | declared operational, **currently off** | Primary search channel. `exa_search` reports `status: off` (Exa not configured) as of 2026-09-17 — this is the Gate D blocker |
| GitHub via `gh` | operational | Top-up only when search is short of the cap |
| arXiv `/abs/` | **operational since 2026-09-19** (PROP-003) | Now a real search lane over the free public Atom API — zero account, no key, own hardened transport, not routed through Agent Reach. Academic preprints only. Still no PDF parser; `/pdf/` links are canonicalized to `/abs/`. (Was: fixture-only rewrite of hits already found.) |
| YouTube, RSS | deferred | Declared so doctor output maps cleanly; never dispatched |
| Reddit, X, Facebook, Instagram, XiaoHongShu, LinkedIn | never | Login-backed; appear in no lane |

## Commands To Verify State

```bash
cd C:/Users/jason/OneDrive/Desktop/quant-agent-brain
uv run pytest -q
uv run ruff check . --no-cache
uv run ruff check src tests scripts
uv run python -m quant_brain.harness.registry --task-type discovery --json
uv run python scripts/dispatch_task.py --type discovery --research-id RQ-6d9c12f4 --dry-run

# Gate C acceptance demonstration (offline, no database writes)
uv run python scripts/acquisition_report.py

# Which lanes are usable right now? (exit 0 = at least one; 3 = none)
uv run python scripts/agent_reach_check.py

# Can those lanes answer a specific question? (exit 0 = ready; 4 = not)
uv run python scripts/gate_readiness.py --research-id RQ-6d9c12f4
```

## Important Design Rule

Do not overengineer. This is not yet a fully autonomous AI quant firm. Build reliable primitives first:

```text
queue → evidence → curation → retrieval → bounded work packets → review
```

Only add more automation after the loop is verified.

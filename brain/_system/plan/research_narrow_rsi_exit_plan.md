---
id: PLAN-research-narrow-rsi-exit
type: research_execution_plan
status: completed_wave1_blocked
owner: jason
created: 2026-09-07
related_research: RQ-dd7da469
related_door: DOOR-etf-mean-reversion
supersedes: none
read_first: true
---

# Research Plan — Narrow RSI Exit / Hold / Cost Pass

> **Status:** draft for Jason review. Do **not** execute until Jason approves.
>
> **Goal:** Unblock the ETF mean-reversion door with *accurate, promotable* evidence for exits, max holding period, and fixed costs — without skipping quality gates, inventing rules, or creating a strategy card.
>
> **Style:** ML-pipeline discipline. Narrow the dataset → quality gate → durable artifacts → no silent promotion. Few steps. Test after every step. Stop on fail.

## Context (verified 2026-09-07)

| Item | State |
|---|---|
| Repo | `C:\Users\jason\OneDrive\Desktop\quant-agent-brain` |
| Authoritative plan | `PLAN.md` (harness phases). This file is a **research execution plan**, not a rewrite of `PLAN.md`. |
| Door | `brain/02_Strategy_Doors/DOOR-etf-mean-reversion.md` |
| Blocking RQ | `RQ-dd7da469` — last live run `RUN-rsi-exit-live-v5` fetched 3 discovery-only sources; curator **rejected all**. Correct fail-closed. |
| Locked entry candidates | A: Wilder RSI(14) < 30 at close → next-bar entry. B: RSI(2) < 20 at close → next-bar entry. |
| Still missing | Source-backed exit; max holding period; fixed cost/slippage assumptions for SPY/QQQ/IWM. |
| Non-goals for this plan | Strategy card, backtest, paper/live trading, Phase 4 adapter rewrite, relaxing curator, optimizing parameters. |

## Principles (do not violate)

1. Evidence before rules. Rules before card. Card before backtest.
2. Fail closed. Validator/curator reject → nothing durable promoted; keep the audit receipt.
3. Cite upstream sources, never Agent Reach.
4. Primary / practitioner only for promotion. Discovery-only may create leads, not door updates.
5. Cap: ≤5 sources fetched per acquisition pass. No retry loops to “get a better answer.”
6. Local Qwen only unless Jason explicitly authorizes cloud.
7. One step at a time. After each step: run the **Test** block. Pass → continue. Fail → stop and report.

## Artifact map (where things must land)

| Stage | Write location | Also recorded in |
|---|---|---|
| Narrowed briefs | `brain/00_Inbox/Research_Briefs/` | `research_questions` (SQLite) |
| Source snapshots | `brain/00_Inbox/Source_Snapshots/` (or `Snapshots/` if that is the live path) | hash + captured_at |
| Raw research | `brain/00_Inbox/Raw_Research/` | `agent_events` |
| Curator verdict | `brain/00_Inbox/Curator_Reviews/` | `agent_tasks` / events |
| Promoted sources only | `brain/01_Sources/{docs,web,...}/` | notes + re-index + embed |
| Door update (Step 4 only) | `brain/02_Strategy_Doors/DOOR-etf-mean-reversion.md` | decision note if needed |
| Failed runs | `brain/00_Inbox/Failed_Runs/` | events |
| Never write here during this plan | `brain/03_Strategy_Cards/`, `04_Backtest_Reports/`, `06_Paper_Trading/` | — |

---

## Step 0 — Baseline freeze (read-only)

**Purpose:** Know exactly what “before” looks like so tests are meaningful.

**Do**
1. Note git / file mtimes are optional; required is a DB + folder snapshot.
2. Record counts: `research_questions` rows for RSI-related IDs, notes, chunks, embeddings, pending embeddings.
3. Confirm `RQ-dd7da469` raw note and curator rejection still exist.
4. Confirm door still says: entries bounded; exit/hold/cost unresolved; no card.

**Do not**
- Fetch anything.
- Edit sources or the door.
- Re-index (re-index resets embeddings — dangerous mid-flight).

### Test 0 (must pass before Step 1)

```bash
cd C:\Users\jason\OneDrive\Desktop\quant-agent-brain
uv run pytest -q
```

Manual checks:
- [ ] `brain/00_Inbox/Raw_Research/RQ-dd7da469.md` exists; scout decision = rejected / sources discovery-only.
- [ ] `DOOR-etf-mean-reversion.md` still `status: research_map` and lists missing exit/hold/cost.
- [ ] Pytest green (or only pre-documented failures — if suite red, **stop** and fix baseline first).
- [ ] Write down: notes / chunks / embeddings / pending counts (append to a short receipt at bottom of this file under “Run log”).

**Exit gate:** Suite usable + RQ/door state documented.  
**On fail:** Stop. Do not narrow briefs on a broken baseline.

---

## Step 1 — Narrow the research ask (docs + DB only)

**Purpose:** Split the fuzzy “find exits/holds/costs” blob into three tiny, testable questions so discovery cannot wander into SEO strategy spam.

**Do**
Create **three** research briefs (Markdown + intake into SQLite if intake CLI is the project norm):

| New ID (assign via intake) | One-line question | Allowed answer shape | Out of scope |
|---|---|---|---|
| RQ-A (exit) | What source-supported **exit** rules pair with daily ETF RSI oversold *entries* (candidates A/B), without optimizing? | At most **two** exit candidates, each with exact rule text + upstream citation + instrument/timeframe assumptions | Entries, backtests, “best RSI settings,” discretionary tips |
| RQ-B (hold) | What source-supported **maximum holding periods** (hard caps, not averages) are stated for short-horizon ETF / equity mean-reversion or RSI-style swings? | At most **two** max-hold candidates, each fixed (e.g. “exit by close of day N”) + citation | Average hold times sold as max; intraday scalps; crypto-only rules |
| RQ-C (cost) | What **fixed** transaction-cost / slippage assumptions are defensible for liquid US equity ETFs (SPY/QQQ/IWM) in daily backtests? | One small table: commission + slippage (bps or $/share) + citation tier; mark `assumption` vs `measured` | Broker promo claims; options/futures costs; optimizing costs to fit returns |

Also write one parent brief that points at A/B/C and freezes:

```text
Universe: SPY, QQQ, IWM
Timeframe: daily bars
Entries locked: RSI(14)<30 or RSI(2)<20 at close; fill next bar
This pass: exits, max hold, costs only
Promotion bar: primary or practitioner only
Cap: ≤5 sources total across A/B/C for the first acquisition wave
No strategy card in this plan
```

Link the old `RQ-dd7da469` as **superseded-for-scoping** (keep file; do not delete — it is the audit receipt). Prefer status note in its frontmatter or a one-line pointer in the parent brief: “prior live run rejected; replaced by RQ-A/B/C for narrower acquisition.”

**Do not**
- Call Agent Reach / Jina / Qwen.
- Promote or demote existing `01_Sources` notes.
- Edit the door yet.

### Test 1

- [ ] Three brief files exist under `brain/00_Inbox/Research_Briefs/` with clear IDs and the tables above reflected in the question text.
- [ ] Parent brief exists and freezes universe / entries / caps.
- [ ] `RQ-dd7da469` still on disk (not deleted).
- [ ] Each brief’s “out of scope” section is present (prevents scope creep in Step 3).
- [ ] If intake CLI used: `research_questions` shows A/B/C as `queued` (or equivalent), not `curated`.
- [ ] Re-run: `uv run pytest -q` still green (docs-only change should not break code).

**Exit gate:** Jason can read the three questions and agree they are narrow enough.  
**On fail:** Fix briefs only; do not start Step 2 with fuzzy questions.

**Human checkpoint:** Jason reviews briefs. Proceed to Step 2 only after OK.

---

## Step 2 — System / save-path check (read-only + tiny fixes only if broken)

**Purpose:** Prove the “ML-style” save pipeline is intact before any new research writes.

**Do**
1. Trace one past successful path (e.g. `RQ-4ddd4ef4` or `RQ-17a4103d`): raw → curator review → `01_Sources` → indexed chunks → embeddings.
2. Trace the failed path (`RQ-dd7da469` / `RUN-rsi-exit-live-v5`): raw saved, curator rejected, **nothing** promoted that should not have been.
3. Confirm write rules in `AGENTS.md` match folders on disk.
4. Check embedding hygiene: pending chunk count; if pending > 0, note it — **do not** blind `index_markdown.py index` (drops embeddings). Prefer `embed_chunks.py embed` only for pending, if Step 2 finds a real pending backlog.
5. Confirm ops events for the rejected run are queryable (`quant_brain.ops.events` tail/summary) so future passes leave the same audit trail.
6. List any `01_Sources` notes whose own text still says “verify before citation” (known hygiene debt). **Do not** mass-demote here — log them for a later Phase-7-style pass.

**Do not**
- Run live discovery.
- Rewrite `PLAN.md`.
- Build a new dashboard or adapter.

### Test 2

```bash
uv run pytest -q
uv run python -m quant_brain.harness.registry
# optional if events CLI works for the known run:
uv run python -m quant_brain.ops.events summary --run-id RUN-rsi-exit-live-v5
```

Manual checks:
- [ ] Happy-path artifacts exist for at least one curated RQ (raw + curator review + ≥1 `01_Sources` file).
- [ ] Rejected RQ did **not** add new durable strategy rules to the door.
- [ ] Registry loads `research_scout` + `knowledge_curator` without error.
- [ ] Pending embeddings known (0 or explicitly listed). If you embed pending: pending returns to 0; spot-check retrieval still returns cited chunks.
- [ ] Short “hygiene debt” list written into this plan’s Run log (the verify-before-cite sources).

**Exit gate:** Save/index/event path understood and safe to write into.  
**On fail:** Fix only the broken primitive (event import, pending embeds, path mismatch). Re-test Step 2. Do not acquire sources on a leaky save path.

**Human checkpoint:** Optional. Auto-continue if all boxes pass; stop if any red.

---

## Step 3 — One bounded accurate acquisition pass

**Purpose:** Get *better* evidence for RQ-A/B/C, not more noise. Accuracy > volume.

### 3a — Channel policy (before any fetch)

Allowed for this pass (in priority order):
1. **Primary docs / references:** StockCharts ChartSchool, TA-Lib docs, peer-reviewed or SSRN/arXiv papers with explicit rules, exchange/ETF issuer methodology docs if relevant to costs.
2. **Practitioner with checkable rules:** named quant blogs / books excerpts / verified transcripts that state exact exit or hold rules and data frequency.
3. **Institutional research** that states cost assumptions or holding conventions for liquid equities/ETFs.

Disallowed for promotion (may note as lead only):
- SEO “RSI strategy 2026” pages, affiliate swing tips, undated screenshots, copied summaries without upstream, social posts without primary evidence.

Hard caps:
- ≤5 upstream fetches total for this wave (across A/B/C).
- ≤1 Qwen repair; then escalate 27B once; then fail closed.
- Wall-clock: one run session; no overnight scrape loops.

### 3b — Execution order

1. `agent-reach doctor --json` (health only).
2. Search/fetch per channel policy; snapshot every fetch (hash + captured_at) into inbox snapshots.
3. Bound extraction with schema validators (exact quotes / source IDs). Fail closed on invented rules.
4. Write **one** raw research note per RQ (A, B, C) or one combined raw note with clear sections — prefer **one note per RQ** for cleaner curator gates.
5. Run curator. Promote only `primary` / `practitioner`. Reject the rest with reasons.
6. If anything promoted: index **only new files** if the tooling allows; else follow project workflow carefully (`embed` after any full re-index). Spot-check retrieval for the new source IDs.

**Do not**
- Create or edit a strategy card.
- Change entry candidates.
- Raise the 5-source cap.
- Treat averages (“typically 3–7 days”) as a max hold unless the source states a hard cap.

### Test 3

For each of RQ-A / RQ-B / RQ-C:
- [ ] Raw note exists with run_id, source list, and evidence quotes tied to URLs.
- [ ] Every fetched URL has a snapshot file with hash + captured_at.
- [ ] Curator review exists with explicit promote/reject per source.
- [ ] **No** discovery-only item appears under `brain/01_Sources/`.
- [ ] Promoted notes include: exact rule text (or cost table), tier, citation, and “applies to daily ETF?” honesty.
- [ ] `uv run pytest -q` still green.
- [ ] Events for the new run_id reconstruct: discover → extract → validate → curator verdict.
- [ ] If zero promotions: that is a **valid pass** of the quality system. Record “no promotable evidence” and **skip Step 4**. Plan next wave (different channels), do not loosen the gate.

**Exit gate:** Either (promoted ≥1 useful source for exit **and/or** hold **and/or** cost) OR (clean zero-promote with audit).  
**On fail (pipeline error, not quality reject):** write `Failed_Runs/` note, stop, do not partial-promote.

**Human checkpoint:** Jason skims curator reviews before Step 4.

---

## Step 4 — Update the door only (no card)

**Purpose:** Reflect *only* what Step 3 promoted. Keep the door a research map, not a strategy.

**Do (only if Step 3 promoted relevant evidence)**
1. Update `DOOR-etf-mean-reversion.md`:
   - Add exit candidate(s) with `source_ids`.
   - Add max-hold candidate(s) with `source_ids`.
   - Add cost assumption table with `source_ids` and `assumption` vs `measured` labels.
   - Keep readiness decision honest: still no card unless exit **and** max hold **and** costs are all source-supported enough for Jason’s bar.
2. Add a short decision log note under `brain/07_Decision_Log/` describing what changed and what is still missing.
3. Re-index/embed if the door should be retrievable (door lives outside `_system/`, so normal index path applies).

**Do not**
- Freeze a strategy card.
- Run a backtest.
- “Fill gaps” with unverified assumptions marked as facts.

### Test 4

- [ ] Door frontmatter `source_ids` includes only real promoted SRC ids.
- [ ] Every new rule line in the door cites a path + heading (or SRC id) that exists on disk.
- [ ] Readiness section updated; if any of exit/hold/cost still missing, door still says **not ready for card**.
- [ ] Decision log note exists.
- [ ] Retrieval spot-check: query for the new exit/hold/cost returns the new source chunks, not the rejected SEO pages.
- [ ] `uv run pytest -q` green.
- [ ] Confirm `brain/03_Strategy_Cards/` still empty / untouched.

**Exit gate:** Door matches evidence; card still gated.  
**On fail:** Revert door edit; leave decision log explaining the revert.

**Human checkpoint:** Jason approves door wording. End of this plan.

---

## Done looks like

**Success path:** Narrow RQs saved → system check green → ≤5 high-quality fetches → curator promotes something useful → door updated with citations → still no card/backtest.

**Also success:** Same pipeline, zero promotions, clear “still blocked” note. Quality held.

**Failure:** Anything promoted without primary/practitioner tier; door updated from discovery-only blogs; card/backtest created; embeddings wiped accidentally; `RQ-dd7da469` audit deleted.

## Explicitly deferred (not in this plan)

- Phase 4 clean `discovery/agent_reach.py` adapter
- Phase 5 packaged `qwen_call` + validator module polish
- Phase 7 mass re-verify of the five soft sources
- Second market door (trend / futures)
- Dashboard UX work

## Run log (fill during execution)

| Step | Date | Result (pass/fail) | Notes |
|---|---|---|---|
| 0 Baseline | 2026-09-07 | **pass** | notes=23; chunks=260; embeddings=260; pending=0; pytest=109 passed, 1 skipped; RQ-dd7da469 raw+rejected on disk; door=research_map missing exit/hold/cost; no 03_Strategy_Cards |
| 1 Narrow briefs | 2026-09-07 | **pass** | RQ-A=RQ-6d9c12f4 (exit); RQ-B=RQ-c920baeb (hold); RQ-C=RQ-80be8cf7 (cost); parent=BRIEF-parent-rsi-exit-hold-cost; RQ-dd7da469 marked superseded-for-scoping; pytest 109/1 |
| 2 System check | 2026-09-07 | **pass** | registry ok; events for RUN-rsi-exit-live-v5 reconstruct (15 events); happy path RQ-17a4103d/4ddd4ef4 intact; rejected path clean (door not polluted); pending embeds=0; hygiene debt: SRC-df1769724d Investopedia verify-before-cite; note registry writes Snapshots/ but folder is Source_Snapshots/; pytest 109/1 |
| 3 Acquisition | 2026-09-07 | **pass (quality zero-promote)** | run_id=RUN-seeded-primary-v1; RQ-66078766; seeds=5 attempted (StockCharts 422; 4 snapshotted); Qwen failed quotes → Failed_Runs; manual exact-quote raw note; curator rejected 4/4 (mvp_testable=false); promoted=0; pytest 109/1 |
| 4 Door update | 2026-09-07 | **skipped** | zero promotions — door untouched; no strategy card |

---

## Approval

- [ ] Jason approves this plan as written
- [ ] Jason requests edits before any step runs
- [ ] Start at Step 0 only after approval

**Recommendation when approved:** execute Step 0 → Test 0 → stop and show Jason the baseline receipt before Step 1.





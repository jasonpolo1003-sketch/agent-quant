---
id: PHASE-06
type: plan_phase
phase: 6
title: Research Scout as the first registered agent
status: pending
created: 2026-08-28
acceptance_task: RQ-dd7da469
---

# Phase 6 — Research Scout as the first registered agent

Parent plan: [../../../PLAN.md](../../../PLAN.md)

## Why this phase exists

Everything so far built the harness and its parts:

| Phase | Gave us |
|---|---|
| 0 | Observability (`ops.events`) |
| 1 | Agents that **declare** capabilities and permissions |
| 2 | A **dispatcher** that routes tasks and enforces boundaries |
| 3 | Honest **retrieval** (semantic embeddings) |
| 4 | Live **discovery** (Agent Reach adapter) |
| 5 | Validated **extraction** (Qwen + validators) |

Phase 6 is the first time a *real* agent runs inside that harness. It replaces the `STARTER_SOURCES` stub with an implementation that actually reaches the internet and reads what it finds.

**The critical constraint:** this phase must change **no harness code**. It registers a new handler for the `discovery` task type and swaps the implementation behind it. If Phase 6 forces edits to `dispatcher.py`, `registry.py`, or `paths.py`, then Phase 2 was designed wrong and the right response is a plan change proposal — not a workaround.

That is precisely why Jason scoped v1 to a single agent: to find that out cheaply, with one worker, before Extractor / Curator / Reviewer are built on top of a bad foundation.

## Entry gate

Phases 0-5 complete. All tests green. Ollama running with `qwen3:14b` + `qwen3.8:27b`. Agent Reach doctor healthy for zero-config channels.

## Exit gate — the acceptance test

Dispatch a `discovery` task for the already-queued research question:

```
RQ-dd7da469
Question: Find source-supported exit conditions, maximum holding periods,
          timing/regime risks, and fixed cost assumptions for the bounded
          RSI candidates.
```

Success requires all of:
1. Raw research note citing **≥3 upstream sources** (never Agent Reach itself).
2. All Phase 5 validators pass (one repair and/or 27B escalation permitted).
3. Complete event trail; `summarize_run` reconstructs the run without reading files.
4. Curator accepts the note and promotes **≥1 Tier A/B source**.
5. **Zero harness-code changes** required to make this work.

### On outcome (5) vs research outcome

If 1-3 and 5 pass but the curator finds the evidence insufficient, **the phase still succeeded**. The honest result "the sources we reached do not support an exit rule" is a valid research finding — the previous pass (RQ-17a4103d) correctly refused to approve an exit rule on thin evidence, and that refusal is the quality gate working as designed.

Do not lower the bar to manufacture a pass. Record what was actually found.

## What gets built

### Handler, not orchestrator

The scout handler is registered against the `discovery` task type:

```python
register_handler("discovery", "research_scout", run_discovery)
```

`run_discovery(task, spec, ctx)` composes existing pieces — it should contain very little logic of its own:

```
1. health check        -> discovery.agent_reach.check_health()
2. plan queries        -> 3-5 bounded queries from the research question
3. discover candidates -> Exa / GitHub / web search; dedup; cap at spec.extras["max_sources"] (5)
4. fetch + snapshot    -> agent_reach.fetch_web(); hash; register in `sources`
5. extract per source  -> llm.qwen_call() with ONE source per call + a stable source_id
6. validate            -> Phase 5 gates; one repair; escalate 27B; else fail closed
7. write raw note      -> brain/00_Inbox/Raw_Research/{research_id}.md
8. return HandlerResult(recommendation="curation")
```

Step 8 matters: the handler **recommends** curation. It does not run the curator. The harness decides (PLAN.md §2).

### Design notes worth pinning

- **Query planning:** keep deterministic if possible (template + method_family + question keywords). If an LLM is used, 14B with a tight schema, capped at 5 queries. Never an open-ended loop.
- **One source per extraction call.** Bounded context keeps 14B honest, makes the source-ID gate trivially checkable, and stops one bad source from poisoning the whole extraction.
- **Note format is already specified.** Reuse the JSON contract from `build_scout_prompt` in [scout_runner.py](../../../src/quant_brain/research/scout_runner.py) — the curator already parses it. Do not invent a second format.
- **Snapshot before extraction.** Provenance must survive URL rot; the curator may need to check a quote months later.

### Retiring the stub

Keep `STARTER_SOURCES` reachable behind a flag (`--stub`) for offline testing and CI, but the default `discovery` handler becomes the live implementation. Do not delete the stub — it is how the dispatcher tests stay hermetic.

### Fail-closed

Any irrecoverable failure:
- Diagnostic note → `brain/00_Inbox/Failed_Runs/{run_id}.md` with stage reached, validator reasons, models used, candidate URLs, event trail.
- Research question returns to `queued` (**not** `failed`), with the failed run id recorded, so it is retryable after a fix.
- **Never** write to `brain/01_Sources/` or any curated shelf.
- Never leave a partial raw note that looks complete.

### Run report

Every run — pass or fail — writes a short report: run_id, task, channels used, sources fetched, models used, repairs, escalations, wall time, validator verdicts. This is what Jason reads to decide whether to trust the run.

## Budget guardrails

- ≤5 sources per run (from the agent's own `max_sources` declaration).
- ≤1 repair per extraction (enforced in Phase 5).
- ≤1 escalation to 27B per extraction.
- Whole-run wall clock cap (suggest 15 min) → abort, fail closed.
- Zero paid API calls.

## Testing

- **Unit:** each step with stubbed dependencies (fake adapter, fake `qwen_call`).
- **Integration (offline):** full handler with recorded Agent Reach + Ollama fixtures — proves wiring with no network or GPU.
- **Harness regression:** the Phase 2 dispatcher tests must still pass **unchanged**. That is the proof the harness held.
- **Acceptance (manual, live):** the real RQ-dd7da469 run. Not in CI.

## Files to create/modify

| Path | Action |
|---|---|
| `src/quant_brain/research/discovery_handler.py` | create — the handler |
| `src/quant_brain/research/executor.py` | modify — keep stub behind `--stub` |
| `agents/research_scout.md` | modify — confirm `handles`/paths/`max_sources` match reality |
| `scripts/dispatch_task.py` | modify — support the live discovery path |
| `tests/test_discovery_handler.py` | create |
| `tests/fixtures/live_run/` | create — recorded end-to-end fixtures |
| `brain/_system/research_scout_agent_workflow.md` | create |
| `brain/00_Inbox/Failed_Runs/` | create dir |

## Verification

```bash
cd C:/Users/jason/OneDrive/Desktop/quant-agent-brain
uv run pytest tests/test_discovery_handler.py -v
uv run pytest tests/test_dispatcher.py -v          # MUST pass unchanged
uv run pytest -q

# live acceptance
uv run python scripts/dispatch_task.py --type discovery --research-id RQ-dd7da469 --dry-run
uv run python scripts/dispatch_task.py --type discovery --research-id RQ-dd7da469
uv run python -m quant_brain.ops.events tail --run-id <printed>
uv run python scripts/dispatch_task.py --type curation --research-id RQ-dd7da469
```

Then **read the raw note and run report by hand.** First live run deserves human eyes on every citation.

## Definition of done

- [ ] `discovery` handler registered; live implementation is the default
- [ ] Stub retained behind `--stub` for hermetic tests
- [ ] Hard caps enforced from the agent's own declaration
- [ ] Fail-closed writes to `Failed_Runs/`, never touches curated shelves
- [ ] Run report written every run
- [ ] Offline integration test passes
- [ ] **Phase 2 dispatcher tests pass unchanged** — the harness held
- [ ] Live acceptance run on RQ-dd7da469 completed and reviewed by Jason
- [ ] Curator outcome recorded honestly (promotion **or** insufficient-evidence finding)
- [ ] Strategy Door updated **only if** evidence genuinely resolved the gaps
- [ ] `PLAN.md` §10 checkpoint updated

## Do not

- Do not create a strategy card or run a backtest here. That is Phase 8, and it needs Jason's explicit approval.
- Do not add Extractor / Curator / Reviewer agents in this phase. Prove the harness with one.
- Do not raise the 5-source cap for "better coverage." Depth over breadth.
- Do not let the handler dispatch the curator itself.
- Do not edit harness code to make this handler fit. If it does not fit, file a plan change proposal.
- Do not treat a clean pipeline run as evidence the *strategy* is good. It is evidence the *pipeline* works.

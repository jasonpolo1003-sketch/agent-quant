---
id: PLAN-UI-TERMINAL
type: phase_plan
status: accepted
owner: jason
created: 2026-09-28
depends_on: PROP-008 (accepted 2026-09-28)
---

# Brain Terminal — local UI plan

Parent: [../../../PLAN.md](../../../PLAN.md) · Proposal: PROP-008 in [plan_change_proposals.md](plan_change_proposals.md)

> **Status: accepted 2026-09-28.** Claude builds it on branch `ui-terminal`.
> The scheduler is always-on through Windows Task Scheduler. Claude CLI is the only backend for now.

## 1. What it is (one paragraph)

A **local, Bloomberg-style terminal** at `http://127.0.0.1:8765`. It lets Jason
*see* what the harness and his coding agents (Codex, Claude Code) are doing,
browse the market data and backtest results, and learn how the system works.
It is a **window onto the brain, not a new agent**. It reads by default. Its
only actions are a small allowlist of scheduled or run-now jobs and a
NotebookLM-style tutor. Model calls go through the **official CLIs, already
logged in to Jason's subscriptions** (`claude -p`, `codex exec`). The terminal
never handles or stores tokens.

Origin: brainstorm with Jason, 2026-09-28. He builds in Codex and "can't
really see anything when things happen". He wants it to feel like a Bloomberg
terminal. His core jobs are the market and backtest lab, learning, and seeing
tasks, runs, skills and schedules in one place.

## 2. Decisions from the brainstorm

| Topic | Jason's answer | Consequence |
|---|---|---|
| Core jobs | Market + backtest lab, Learning, "see everything in one spot" | Observability first, lab second, tutor third |
| Live data | Live **brain state** | Server-sent events over `agent_events`, git and agent sessions. No market feed, no quotes |
| Agent panel | Tasks, runs, skills in one spot, plus scheduled tasks | Tasks/Runs/Skills/Schedules screens. A job allowlist, not a free agent |
| Skills | All three: harness agents, Claude Code skills, Codex skills | One catalogue with three sources |
| Schedules | Data refresh, health checks, agent prompts, research runs | All four job kinds. **Research runs stay disabled while PROP-007's freeze holds** |
| Learning | Concept library, explain-this-result, decision journal; "like NotebookLM, a teacher, not a crazy agent"; "understand what's happening and how to rebuild this" | Source-grounded tutor with no tools, citations required |
| Stack | Local web app | FastAPI + static frontend, served from this repo via `uv` |

## 3. Screens (function-key navigation, dense dark theme)

A command bar sits on every screen, e.g. `SPY <GO>`, `RUN-871299ea31 <GO>` or
`learn look-ahead bias <GO>`.

| Key | Screen | Shows | Reads |
|---|---|---|---|
| F1 | **HOME** | Gate/phase timeline (A–F, PROP-007 steps), test baseline, counts, "next bounded step" from PLAN §10, event ticker | `PLAN.md` §10, `brain.sqlite` counts, last health-check result |
| F2 | **RUNS** | Live event stream; one lane per agent; run inspector (receipts, diagnostics, snapshots); **external agent feed**: Codex and Claude Code sessions in this repo (prompts, files touched, commands, commits) | `agent_events`, `agent_tasks`, `brain/00_Inbox/Failed_Runs/`, `~/.codex/sessions/`, `~/.claude/projects/<this repo>/`, `git log` |
| F3 | **TASKS** | Harness task queue, schedules, job history, run-now buttons (with confirmation), next-fire times | `agent_tasks`, terminal DB (§6) |
| F4 | **SKILLS** | One catalogue: harness agents (handles, model, read/write paths, recent runs), Claude Code skills, Codex skills | `agents/*.md`, `~/.claude/skills/*/SKILL.md`, `.claude/skills/`, `~/.codex/skills/` |
| F5 | **MARKETS** | Dataset list with provenance badges (accepted/invalid, sha256, basis, warnings); candlestick + volume; SPY/QQQ/IWM compare; drawdown; data-freshness age | `price_datasets`, `data/manifests/`, loader for accepted datasets only |
| F6 | **LAB** | Strategy card (frozen hash); **full trial ledger, never just the best run**; equity vs buy-and-hold vs random-entry band; in-sample/held-out shading; deflated Sharpe; review verdict banner | Whatever PROP-007 step 5 writes. Empty until then |
| F7 | **LEARN** | NotebookLM-style tutor, concept library, decision journal | See §5 |
| F8 | **SETTINGS** | Backend status (Claude CLI, Codex CLI, Ollama), sign-in instructions, scheduler on/off | CLI probes |

"Explain" buttons on RUNS and LAB open LEARN with that run's ledger or
diagnostics preselected as sources.

## 4. Subscription CLIs (the auth question)

- **Claude:** `claude -p "<prompt>" --output-format stream-json`, using the
  login Claude Code already holds. Installed now (2.1.63).
- **Codex:** `codex exec --sandbox read-only "<prompt>"`, after
  `npm i -g @openai/codex` and `codex login` (ChatGPT sign-in). **Not on PATH
  yet.** The Codex app's data exists in `~/.codex`.
- **Local:** Ollama/Qwen stays available as a zero-cost option.
- **Why the CLIs:** calling the official CLIs keeps usage within each vendor's
  own client and terms. Extracting OAuth tokens to call the APIs directly is
  **out of scope**: it is fragile and breaks the terms. This is personal
  local use only, never exposed to other users.
- **Adapter:** one `ModelBackend` interface (`ask(prompt, sources, mode) ->
  stream`), with Claude, Codex and Ollama implementations. This follows the
  model-agnostic direction; see the memory note on the model backend.
- **Tutor restrictions:** tutor calls run with no tools (Claude:
  `--allowedTools ""`, or a Read-only allowlist scoped to the selected files;
  Codex: `--sandbox read-only`). The tutor receives the selected source text
  and cannot browse, edit or dispatch.
- **Not a harness change:** this does **not** change the harness's extraction
  model policy (§9). Moving Scout extraction to a subscription CLI remains a
  separate proposal.

## 5. LEARN, the NotebookLM-style tutor

- **Layout:** sources on the left (checkboxes), chat in the centre, the saved
  notebook on the right.
- **Sources:** `brain/01_Sources/`, decision log, PROPs, `PLAN.md`, phase
  docs, `SESSION_HANDOFF.md`, selected code files, a run's receipts, a
  backtest's ledger. Large selections go through the existing retrieval
  module (nomic-embed chunks).
- **Persona:** a teacher. It explains plainly, cites `[source:line]` for every
  claim, says "the sources don't say" instead of guessing, and offers "how
  would I rebuild this?" walk-throughs of the code.
- **Concept library:** saved answers become study notes in
  `terminal/learning/`, with `type: study_note` and
  `trusted: false`. They are **never indexed into RAG** as evidence.
- **Decision journal:** a timeline of PROP-001…, DEC-* and handoff entries,
  read as a story ("what we tried, what broke, what we decided").

> **Correction (build, 2026-09-28):** the indexer indexes every `brain/**`
> note except `_system` and `Source_Snapshots`. So the terminal writes study
> notes and scheduled outputs under a repo-root `terminal/` folder
> (`learning/`, `scheduled/`, `logs/`), never under `brain/`. That keeps them
> out of RAG by construction.

## 6. Scheduler

- **Where definitions live:** a separate UI database, `db/terminal.sqlite`,
  with `schedules`, `job_runs` and `ui_settings` tables, so the terminal
  never alters `brain.sqlite`'s schema or hash. `brain.sqlite` is opened
  **read-only** (`file:...?mode=ro`).
- **Job allowlist**, with no arbitrary shell:

  | Kind | Runs | Writes |
  |---|---|---|
  | `health_check` | `uv run pytest -q`, `scripts/verify_receipts.py`, `scripts/verify_market_data.py` | Result into `job_runs` only |
  | `data_refresh` | `scripts/fetch_market_data.py` then verify | New immutable datasets (Gate F rules unchanged) |
  | `agent_prompt` | A saved prompt via `claude -p` / `codex exec` in read-only mode | Output into `terminal/scheduled/`, never promoted |
  | `research_run` | Dispatcher `discovery` task | **Disabled while PROP-007's freeze holds** |

- **Caps:** a timeout, max runs per day and one concurrent job per kind.
  Every run records `agent_events` through the existing `ops.events` API.
  The UI's only write into `brain.sqlite` goes through that API.
- **When jobs run (decided: always-on):** each enabled schedule is
  registered as a Windows Task Scheduler task named `QuantBrain\<job id>`
  (`schtasks /Create`). The task runs `scripts/run_terminal_job.py <job id>`,
  so jobs fire even when the terminal is closed. The terminal DB is the
  source of truth: editing or disabling a schedule re-registers or deletes its
  task, and the SCHEDULES screen flags any drift between the DB and
  Task Scheduler.

## 7. Stack

- **Backend:** FastAPI + uvicorn, SSE for live updates. New dependencies:
  `fastapi`, `uvicorn`. The server binds to **127.0.0.1 only**.
- **Frontend:** static HTML/JS, no build step. Chart libraries are vendored
  into `ui/static/vendor/` so it works offline: TradingView
  `lightweight-charts` (Apache-2.0) for price, `uPlot` (MIT) for equity and
  drawdown.
- **Layout:** `src/quant_brain/ui/` (server, readers, backends, scheduler),
  `ui/static/`, `scripts/serve_terminal.py`, `tests/test_ui_*.py`.
- **Reuse:** salvage what helps from `preserve/live-research-and-dashboard-20260916`
  (event lanes, inspector) through a reviewed change, not a merge.

## 8. No cross-over with the Codex builder

- **Terminal-owned paths:** the terminal owns only its own paths (§7),
  `db/terminal.sqlite`, `terminal/scheduled/` and
  `terminal/learning/`.
- **Never touched:** it never edits `src/quant_brain/{data,harness,research,discovery,curation,llm}`,
  `db/schema.sql`, `brain/03`–`07`, or `data/`.
- **LAB contract:** LAB **adapts to** whatever PROP-007 step 5 writes. It
  does not define the backtest schema. One request goes to the builder:
  persist each trial's daily equity series (e.g. Parquet next to the report)
  so LAB can chart it without recomputing.

## 9. Build order (one verified slice at a time)

| Slice | Delivers | Exit check |
|---|---|---|
| U0 | PROP-008 accepted; server skeleton; HOME; read-only DB access | Tests green; `brain.sqlite` hash unchanged after a session |
| U1 | RUNS: SSE event stream, agent lanes, git + Codex/Claude session feed | Live event appears within ~2 s of `record_event` |
| U2 | MARKETS: dataset list, provenance, charts | Only accepted datasets chart; invalid ones are shown flagged |
| U3 | LEARN: backend adapter (Claude first), tutor, decision journal, concept library | Answers cite sources; tutor process has no write/tool access |
| U4 | TASKS + scheduler: health_check first, then data_refresh, agent_prompt | Caps enforced; every run evented; research_run refuses while frozen |
| U5 | SKILLS catalogue | All three sources listed with provenance |
| U6 | LAB | After PROP-007 step 5 lands; renders the full ledger |

## 9a. Build status (2026-09-28, branch `ui-terminal`)

- **Built in one pass:** U0–U6, all eight screens. Everything lives in its own
  worktree (`../quant-agent-brain-ui`) so the builder working on `testing` in
  the main checkout is never switched or blocked.
- **Run it:**
  `uv run python scripts/serve_terminal.py --root ../quant-agent-brain --open`.
  After merge, drop `--root`.
- **Verified:**
  - 44 terminal tests: read-only hash check, host/origin guards, source
    allowlist, caps, freeze refusal, Task Scheduler argument building and drift.
  - Full suite: 693 passed, 1 skipped. Ruff is clean.
- **Live checks:**
  - Every screen was driven in Chrome with no console errors.
  - A tutor answer through the real `claude -p` cited `[PLAN.md:208-219]`,
    and the citation opened the highlighted lines.
  - A real `schtasks` register → query → delete round trip passed.
- **Known finding (not in terminal code):** `market_data.verify_datasets`
  raises on a corrupt Parquet file instead of reporting `invalid`. The terminal
  contains it (it shows `unverified` or `invalid`), but the Gate F owner should
  fix it.
- **Not yet exercised against the live brain:** job runs. A run appends
  `agent_events` rows to `brain.sqlite`, so the first one is deferred until the
  builder's backtest step no longer depends on a fixed DB hash.

## 10. Deliberately out of scope

- Live or real-time market feeds, quotes or brokers.
- Any trading button.
- Multi-user or remote access.
- A general agent that edits code from the UI.
- Arbitrary shell from the UI.
- Token extraction.
- Cloud hosting.

## 11. Bigger ideas for later (not now)

- **Run replay:** step through a run's events, prompts and validator verdicts.
- **Trial comparison:** side by side, with a multiple-testing penalty shown
  inline.
- **Windows notifications** when a job or a Codex session finishes.
- **"Rebuild this" guided tours:** the tutor walks the code path for one
  feature file by file.

## 12. Decisions (2026-09-28)

1. **Scheduler:** always-on through Windows Task Scheduler.
2. **Codex CLI:** not now. Claude is the only backend, and the Codex slot
   stays in the adapter.
3. **Builder:** Claude builds the whole terminal. Codex is not involved.
4. **Timing:** start now, slice by slice, on branch `ui-terminal`.

# Agent Reach Adapter Workflow

## Purpose

Production Research Scout discovery uses Agent Reach as a **router + doctor**, then calls the named upstream tools directly. This project does not wrap Agent Reach's routing, invent a scraper, or require injecting a Python `search_fn` on the CLI.

Pytest never opens the network. Tests inject a subprocess `runner` and a `fetch_impl`.

## What is wired

| Step | Tool | How |
|---|---|---|
| Health | `agent-reach doctor --json` | Routes Exa/GitHub only. An unhealthy doctor disables those lanes but does not gate independent arXiv search. |
| Search (preferred) | Exa via `mcporter call exa.web_search_exa` | Zero-config search channel. |
| Search (fallback) | `gh search repos` | Used when Exa is empty or the search channel is unusable. |
| Fetch | Jina Reader (`https://r.jina.ai/URL`) | Web channel. Snapshots cite the **upstream** URL, never Agent Reach. |

Login-backed social channels (reddit, twitter, facebook, instagram, xiaohongshu, linkedin) stay off.

Forbidden Agent Reach subcommands: `install`, `uninstall`, `configure`. The adapter never reads `~/.agent-reach/config.yaml`.

## Locate the executable

Resolved in this order:

1. `AGENT_REACH_EXE`
2. `agent-reach` on `PATH`
3. Jason's default Windows venv: `C:\Users\jason\.agent-reach-venv\Scripts\agent-reach.exe` (only if that path exists)

## Run a real dispatcher Scout command (no Python injection)

```bash
# 1. Check routed-lane health and see which independent lanes remain usable.
#    Exit 0 = at least one lane usable, 2 = doctor unusable with no independent
#    lane, 3 = doctor answered but none are usable.
uv run python scripts/agent_reach_check.py

# 1b. A usable lane is not the same as a lane that can answer YOUR question.
#     Exit 0 = the lanes can reach the Phase 6 minimum, 4 = they cannot.
uv run python scripts/gate_readiness.py --research-id RQ-xxxxxxxx

# 2. Queue a research question if you do not already have one.
uv run python scripts/research_intake.py add "What published papers cover overnight reversal?" --family mean_reversion

# 3. Explain routing without executing.
uv run python scripts/dispatch_task.py --type discovery --research-id RQ-xxxxxxxx --dry-run

# 4. Run live discovery. Default backend is live; do not pass --stub.
uv run python scripts/dispatch_task.py --type discovery --research-id RQ-xxxxxxxx
```

The live handler constructs `LiveDiscoveryBackend(allow_network=True)` with **no** `search_fn` / `fetch_fn`. Search and fetch go through `AgentReachAdapter`.

Offline / CI stub (seeded catalog, not live search):

```bash
uv run python scripts/dispatch_task.py --type discovery --research-id RQ-xxxxxxxx --stub
```

Pytest sets `QUANT_BRAIN_DISCOVERY=seeded` so the suite makes zero network calls.

## Fail closed

An unhealthy/missing Agent Reach doctor disables Exa and GitHub, but independent
arXiv discovery is still attempted. If every available search lane returns no
URLs, or a fetch fails:

- the research question returns to `queued` with `raw_note_path` cleared
- incomplete raw-note scaffolds are deleted
- `brain/00_Inbox/Failed_Runs/{run_id}.md` is written (`retryable: true`)
- scout events `discovery_started`, `discovery_failed`, and `failed_run_written` are recorded

Re-run the same dispatch command after fixing the failed routed lane, arXiv, or network.

## Snapshots

Fetched pages land at:

```text
brain/00_Inbox/Source_Snapshots/YYYY-MM-DD/{content_hash[:12]}-{url_hash[:8]}.md
```

Identical body text from two URLs keeps two files so both identities stay auditable.

## Caps

`max_sources = min(agent extras max_sources, task payload max_sources)`. Callers may narrow the agent cap (default 5). They may not widen it.

## Files

```text
src/quant_brain/discovery/agent_reach.py
src/quant_brain/discovery/live_discovery.py
scripts/agent_reach_check.py
scripts/dispatch_task.py
tests/test_agent_reach_adapter.py
tests/fixtures/agent_reach_doctor_live.json      # verbatim capture; do not edit
tests/fixtures/agent_reach_doctor_healthy.json   # explicitly synthetic
tests/fixtures/README_agent_reach_doctor.md      # why there are two
tests/fixtures/agent_reach_search.json
tests/fixtures/jina_web_page.md
```

## Fixtures: two files, deliberately

`agent_reach_doctor_live.json` is a **verbatim** capture of real `doctor --json`
output. `exa_search` really is `"off"` in it, and its non-ASCII names are literal
UTF-8 — an escaped file would be pure ASCII and would decode cleanly under cp1252,
defeating the test that pins the encoding fix.

`agent_reach_doctor_healthy.json` is **synthetic**, with `exa_search` forced to
`"ok"` so dispatch tests exercise dispatch.

Do not merge them, and do not edit the live capture to make a test pass. A single
file blending observed and edited state, while still called a recording, is exactly
what let the `search`/`exa` channel-name defect survive an entire gate.

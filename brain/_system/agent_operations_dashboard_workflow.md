# Agent Operations Dashboard

## Purpose

Show the research harness operating in real time so the human operator can move between agent lanes, inspect evidence handoffs, understand failures, and ask Hermes to continue or inspect a run.

## Architecture

```text
agents / scripts
→ append ordered events to SQLite agent_events
→ local stdlib HTTP server
→ dashboard polls once per second
→ agent lanes + event timeline + task inspector
```

No cloud observability service is required.

## Start

```bash
uv run python scripts/serve_agent_dashboard.py --host 127.0.0.1 --port 8765
```

Open:

```text
http://127.0.0.1:8765
```

## UI

- **Agent lanes:** orchestrator, Research Scout, Qwen 14B, Qwen 27B, curator, strategy generator, backtest agent, and risk reviewer.
- **Live event trail:** ordered health checks, candidates, snapshots, handoffs, validation failures, escalations, and reviews.
- **Inspector:** task status, question, selected agent state, and recent handoffs.
- **Hermes controls:** when opened inside Hermes, `Inspect agent` and `Continue run` send a scoped prompt back to the assistant.

## API

```text
GET /api/health
GET /api/runs?limit=25
GET /api/run?run_id=RUN-...
```

The server binds to localhost by default. Do not expose it publicly without authentication and a separate security review.

## Verified Run

`RUN-rsi-exit-live-v5` displays:

```text
orchestrator       completed
research_scout     completed
qwen3:14b          failed validation and escalated
qwen3.8:27b        completed validation
knowledge_curator  completed with rejected verdict
```

A failed model lane is not hidden. The UI shows the failure and the successful escalation so the operator can understand what happened.

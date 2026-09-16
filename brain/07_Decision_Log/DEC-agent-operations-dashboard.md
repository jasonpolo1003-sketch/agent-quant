---
id: DEC-agent-operations-dashboard
type: decision
title: Use a Lightweight Local Agent Operations Dashboard First
status: accepted
---

# Decision — Lightweight Local Agent Operations Dashboard

## Decision

Use an append-only SQLite event stream and a small local Python/HTML dashboard before adopting a larger orchestration-observability platform.

## Why

- The project already uses SQLite as its structured system of record.
- The user needs agent lanes, handoffs, evidence, failures, escalation, and task state—not production-scale tracing infrastructure yet.
- The dashboard must remain local, budget-first, and compatible with Ollama.
- Every event should be inspectable without depending on a cloud service.
- Hermes-native buttons can turn visual inspection into a scoped follow-up instruction.

## Current Implementation

```text
agent_events table
→ record_event()
→ localhost dashboard API
→ agent lanes / event timeline / inspector
```

## Deferred Options

LangGraph Studio, Langfuse, Arize Phoenix, or OpenTelemetry-based tracing may become useful after the workflow graph, run volume, or evaluation needs outgrow the local dashboard. They are not required to prove the first research-to-backtest loop.

## Revisit When

- runs involve concurrent branches rather than one bounded pipeline;
- traces need token/cost/span analytics across many sessions;
- multiple users need remote access;
- manual event instrumentation becomes a maintenance burden;
- the project adopts LangGraph or another formal orchestration runtime.

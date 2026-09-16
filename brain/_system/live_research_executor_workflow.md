# Live Research Executor Workflow

## Purpose

Replace the hard-coded starter-source executor with a bounded live path that discovers sources through Agent Reach/upstream tools, snapshots evidence, processes it with local Qwen, validates the output, and hands it to the curator.

## Flow

```text
research question
→ Agent Reach doctor
→ bounded Yahoo/OpenCLI discovery
→ deterministic dedupe + source-quality ranking
→ Jina source snapshots with SHA-256 hashes
→ Qwen 14B evidence extraction
→ deterministic source/URL/quote validation
→ one Qwen 14B repair
→ Qwen 27B escalation if needed
→ raw research note
→ curator promotion/rejection
→ SQLite agent event trail
```

## Command

```bash
uv run python scripts/live_research_executor.py \
  --research-id RQ-xxxx \
  --run-id RUN-description \
  --max-candidates 10 \
  --max-sources 3
```

The source and context caps are intentional. More links do not automatically produce better research.

## Quality Gates

- URLs come from the discovery tool, never from Qwen.
- Snapshot content and hashes are written before model processing.
- Qwen must preserve protected source IDs, titles, URLs, and quality labels.
- Evidence quotes must appear in the corresponding snapshot.
- Discovery-only sources cannot independently support strategy rules.
- A failed 14B answer gets one repair; unresolved failures escalate to 27B or fail closed.
- Source snapshots remain raw inbox evidence and are excluded from the durable embedding index.

## Acceptance Run

```text
Research task: RQ-dd7da469
Run: RUN-rsi-exit-live-v5
Sources fetched: 3
Qwen 14B: two validation failures
Qwen 27B: passed deterministic validation
Curator verdict: rejected
```

The rejection is a successful quality-control result: all discovered pages were discovery-only and did not establish a fixed RSI(14) exit, maximum holding period, or transaction-cost assumption.

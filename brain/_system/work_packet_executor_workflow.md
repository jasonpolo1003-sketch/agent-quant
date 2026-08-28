# Work Packet Executor Workflow

## Purpose

Execute one bounded agent work packet without launching an autonomous model agent.

The first executor is deliberately narrow and deterministic. It currently supports the lookahead-bias validation-checklist packet and refuses unsupported tasks instead of inventing an answer.

## Command

```bash
uv run python scripts/execute_work_packet.py brain/00_Inbox/Work_Packets/<packet-file>.md
```

Optional paths:

```bash
uv run python scripts/execute_work_packet.py <packet-file> --project-root <project-root> --db <sqlite-path>
```

## What It Does

1. Parses the packet ID, agent role, task, output contract, retrieved evidence, and allowed write paths.
2. Confirms the packet has retrieved evidence with source paths and headings.
3. Sets the matching `agent_tasks` row to `running`.
4. Resolves the first allowed write path inside the project boundary.
5. Produces a deterministic Markdown result for the supported checklist task.
6. Validates that the result cites a retrieved source path and heading.
7. Writes `<packet-id>-result.md` under the allowed write path.
8. Sets `agent_tasks.status` to `completed` and records `output_path`.
9. On an execution error, sets the task to `failed` and records the error.

## Safety Boundaries

- Project-relative output paths only; `..` escapes are rejected.
- No local or cloud model is called.
- Unsupported task types fail closed.
- No backtest, strategy card, paper trade, or live trade is created.
- A result cannot complete unless it contains at least one retrieved path-and-heading citation pair.

## Current Limitation

`deterministic-v1` is a tracer-bullet executor, not a general reasoning agent. Add reviewed task templates one at a time, or later introduce an explicitly configured local-model executor behind the same path, citation, and database gates.

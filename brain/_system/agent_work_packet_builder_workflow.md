# Agent Work Packet Builder Workflow

The work packet builder creates a bounded assignment for a single agent.

## Why This Exists

Agents should not receive vague prompts like:

```text
go improve the research brain
```

They should receive:

```text
role
specific task
retrieved context
allowed read paths
allowed write paths
output contract
```

## Flow

```text
task
  -> load agent role file
  -> retrieve relevant RAG context
  -> combine role + task + context + file boundaries
  -> save packet to brain/00_Inbox/Work_Packets/
  -> record agent_tasks row
```

## Command

```bash
uv run python scripts/build_work_packet.py knowledge_curator "Review whether lookahead bias source should update the validation checklist" --query "lookahead bias future data" --log-retrieval
```

## Important Rule

This does not spawn more agents by itself. It prepares clean work for one agent at a time. That keeps the system disciplined and closer to a real research workflow.

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from quant_brain.config import PROJECT_ROOT
from quant_brain.db.init_db import DEFAULT_DB_PATH, connect, init_database
from quant_brain.harness.registry import RegistryError, has_declaration, load_agent_spec
from quant_brain.indexing.embeddings import DEFAULT_MODEL as _EMBED_DEFAULT_MODEL
from quant_brain.retrieval.context_builder import build_retrieval_context


# Fallback only for agent files that carry no registry frontmatter yet. A declared
# agent's own allowed paths always win -- the agent states its boundary, the
# harness enforces it. See PLAN.md section 2.
DEFAULT_READ_PATHS = [
    "AGENTS.md",
    "agents/",
    "brain/00_Inbox/",
    "brain/01_Sources/",
    "brain/02_Strategy_Doors/",
]
DEFAULT_WRITE_PATHS = ["brain/00_Inbox/"]
_DEFAULT_OUTPUT_CONTRACT = "Return a concise Markdown result and update only allowed files."


def _is_within(candidate: str, allowed: str) -> bool:
    """Report whether a declared path is inside an allowed declared path."""
    candidate = candidate.strip().replace("\\", "/").lstrip("./").rstrip("/")
    allowed = allowed.strip().replace("\\", "/").lstrip("./").rstrip("/")
    if candidate == allowed:
        return True
    return candidate.startswith(f"{allowed}/")


def _resolve_paths(
    requested: list[str] | None,
    declared: tuple[str, ...] | None,
    fallback: list[str],
    agent_role: str,
    field_name: str,
) -> list[str]:
    """Pick the effective path list, refusing to widen an agent's declaration.

    Narrowing is allowed: a caller may restrict an agent further for one task.
    Widening is a bug -- it would let a careless caller hand an agent reach it
    never asked for.
    """
    if declared is None:
        return list(requested) if requested is not None else list(fallback)
    if requested is None:
        return list(declared)

    widened = [
        path for path in requested if not any(_is_within(path, allow) for allow in declared)
    ]
    if widened:
        raise RegistryError(
            f"{agent_role}: {field_name} {widened} exceed the agent's declared paths "
            f"{list(declared)}; narrowing is allowed, widening is not"
        )
    return list(requested)


@dataclass
class AgentWorkPacket:
    packet_id: str
    agent_role: str
    task: str
    role_instructions: str
    retrieved_context: str
    allowed_read_paths: list[str] = field(default_factory=list)
    allowed_write_paths: list[str] = field(default_factory=list)
    output_contract: str = "Return a concise Markdown result and update only allowed files."
    retrieval_query_id: str | None = None
    retrieval_query: str | None = None


def load_agent_role(project_root: str | Path, agent_role: str) -> dict[str, str]:
    """Load an agent role instruction file from agents/<role>.md."""
    root = Path(project_root)
    path = root / "agents" / f"{agent_role}.md"
    if not path.exists():
        raise FileNotFoundError(f"agent role file not found: {path}")
    return {
        "agent_role": agent_role,
        "path": path.relative_to(root).as_posix(),
        "instructions": path.read_text(encoding="utf-8"),
    }


def _markdown_list(items: list[str]) -> str:
    return "\n".join(f"- `{item}`" for item in items) if items else "- None"


def format_work_packet_markdown(packet: AgentWorkPacket) -> str:
    """Format a work packet that can be handed to a human or model agent."""
    return f"""---
id: {packet.packet_id}
type: agent_work_packet
agent_role: {packet.agent_role}
status: ready
retrieval_query_id: {packet.retrieval_query_id or ''}
---

# Agent Work Packet — {packet.packet_id}

## Agent Role

{packet.agent_role}

## Task

{packet.task}

## Role Instructions

{packet.role_instructions.strip()}

## Retrieved Context

{packet.retrieved_context.strip()}

## Allowed Read Paths

{_markdown_list(packet.allowed_read_paths)}

## Allowed Write Paths

{_markdown_list(packet.allowed_write_paths)}

## Output Contract

{packet.output_contract}

## Guardrails

- Do not edit outside allowed write paths.
- Cite source file paths/headings from retrieved context.
- If context is weak, say what is missing instead of guessing.
- Do not create strategy cards unless this packet explicitly asks for that.
- Do not run backtests unless this packet explicitly asks for that.
- Do not paper trade or live trade.
"""


def build_work_packet(
    project_root: str | Path = PROJECT_ROOT,
    db_path: str | Path = DEFAULT_DB_PATH,
    agent_role: str = "research_scout",
    task: str = "",
    retrieval_query: str | None = None,
    allowed_read_paths: list[str] | None = None,
    allowed_write_paths: list[str] | None = None,
    output_contract: str = _DEFAULT_OUTPUT_CONTRACT,
    context_limit: int = 5,
    model: str = _EMBED_DEFAULT_MODEL,
    dimensions: int | None = None,
    log_retrieval: bool = False,
) -> AgentWorkPacket:
    """Combine role instructions, task, retrieved context, and file boundaries."""
    if not task.strip():
        raise ValueError("task cannot be empty")
    packet_id = f"WP-{uuid4().hex[:10]}"
    role = load_agent_role(project_root, agent_role)

    # Registry-declared paths win when the agent declares them; undeclared agent
    # files keep the legacy caller-supplied behavior so migration can be gradual.
    spec = load_agent_spec(project_root, agent_role) if has_declaration(project_root, agent_role) else None
    read_paths = _resolve_paths(
        allowed_read_paths,
        spec.allowed_read_paths if spec else None,
        DEFAULT_READ_PATHS,
        agent_role,
        "allowed_read_paths",
    )
    write_paths = _resolve_paths(
        allowed_write_paths,
        spec.allowed_write_paths if spec else None,
        DEFAULT_WRITE_PATHS,
        agent_role,
        "allowed_write_paths",
    )
    if spec is not None and output_contract == _DEFAULT_OUTPUT_CONTRACT:
        output_contract = spec.output_contract

    query = retrieval_query or task
    context_packet = build_retrieval_context(
        db_path=db_path,
        query=query,
        limit=context_limit,
        model=model,
        dimensions=dimensions,
        agent_id=agent_role,
        task_id=packet_id,
        log=log_retrieval,
    )
    return AgentWorkPacket(
        packet_id=packet_id,
        agent_role=agent_role,
        task=task,
        role_instructions=role["instructions"],
        retrieved_context=context_packet["markdown"],
        allowed_read_paths=read_paths,
        allowed_write_paths=write_paths,
        output_contract=output_contract,
        retrieval_query_id=context_packet.get("query_id"),
        retrieval_query=query,
    )


def save_work_packet(
    project_root: str | Path,
    db_path: str | Path,
    packet: AgentWorkPacket,
) -> str:
    """Write packet Markdown and record an agent_tasks row."""
    root = Path(project_root)
    out_dir = root / "brain" / "00_Inbox" / "Work_Packets"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{packet.packet_id}-{packet.agent_role}.md"
    path.write_text(format_work_packet_markdown(packet), encoding="utf-8")

    init_database(db_path)
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO agent_tasks (task_id, agent_role, status, input_path)
            VALUES (?, ?, 'ready', ?)
            ON CONFLICT(task_id) DO UPDATE SET
                agent_role = excluded.agent_role,
                status = excluded.status,
                input_path = excluded.input_path
            """,
            (packet.packet_id, packet.agent_role, str(path)),
        )
        conn.commit()
    return str(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build agent work packets with retrieved context.")
    parser.add_argument("agent_role")
    parser.add_argument("task")
    parser.add_argument("--query", default=None)
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--project-root", default=str(PROJECT_ROOT))
    parser.add_argument("--read", nargs="*", default=None)
    parser.add_argument("--write", nargs="*", default=None)
    parser.add_argument("--contract", default=_DEFAULT_OUTPUT_CONTRACT)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--model", default=_EMBED_DEFAULT_MODEL)
    parser.add_argument("--dimensions", type=int, default=None)
    parser.add_argument("--log-retrieval", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    packet = build_work_packet(
        project_root=args.project_root,
        db_path=args.db,
        agent_role=args.agent_role,
        task=args.task,
        retrieval_query=args.query,
        allowed_read_paths=args.read,
        allowed_write_paths=args.write,
        output_contract=args.contract,
        context_limit=args.limit,
        model=args.model,
        dimensions=args.dimensions,
        log_retrieval=args.log_retrieval,
    )
    path = save_work_packet(args.project_root, args.db, packet)
    result = {"packet_id": packet.packet_id, "path": path, "retrieval_query_id": packet.retrieval_query_id}
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(path)


if __name__ == "__main__":
    main()

from __future__ import annotations

import os
from typing import Any

from quant_brain.harness.dispatcher import (
    HandlerResult,
    Task,
    WorkPacketContext,
    register_handler,
)
from quant_brain.harness.registry import AgentSpec


def _relative_output(context: WorkPacketContext, path: str) -> str:
    """Express a handler output as a project-relative POSIX path.

    Legacy executors record absolute paths in the database. Those may point at
    a different project root than the one being dispatched against, so rebase
    onto this run's root before enforcement rather than trusting the stored
    string.
    """
    from pathlib import Path

    root = context.project_root.resolve()
    candidate = Path(str(path).replace("\\", "/"))
    if candidate.is_absolute():
        try:
            candidate = candidate.resolve().relative_to(root)
        except ValueError:
            # Stored under a different root: keep the tail below `brain/`.
            parts = candidate.parts
            if "brain" in parts:
                candidate = Path(*parts[parts.index("brain") :])
            else:
                candidate = Path(candidate.name)
    resolved = context.resolve_write(candidate)
    return resolved.relative_to(root).as_posix()


def _discovery_backend_name(task: Task) -> str:
    payload_name = task.payload.get("backend") or task.payload.get("discovery_backend")
    if payload_name:
        return str(payload_name)
    return os.environ.get("QUANT_BRAIN_DISCOVERY") or "live"


def run_discovery(task: Task, agent: AgentSpec, context: WorkPacketContext) -> HandlerResult:
    """Research Scout discovery handler.

    Live Agent Reach / Jina discovery is the production backend. The seeded
    starter catalog is a test double selected with ``backend=seeded`` or
    ``QUANT_BRAIN_DISCOVERY=seeded``. This handler never runs the curator; it
    returns ``recommendation="curation"`` so the harness decides what is next.
    """
    from quant_brain.discovery.live_discovery import get_discovery_backend
    from quant_brain.research.executor import execute_discovery_task

    backend_name = _discovery_backend_name(task)
    allow_network = backend_name == "live" and task.payload.get("allow_network", True)
    backend_kwargs: dict[str, Any] = {}
    if backend_name in {"live", "agent-reach", "jina"}:
        backend_kwargs["allow_network"] = bool(allow_network)
        if task.payload.get("search_fn") is not None:
            backend_kwargs["search_fn"] = task.payload["search_fn"]
        if task.payload.get("fetch_fn") is not None:
            backend_kwargs["fetch_fn"] = task.payload["fetch_fn"]
    backend = get_discovery_backend(backend_name, **backend_kwargs)

    research_id = task.payload.get("research_id")
    max_sources = int(agent.extras.get("max_sources") or task.payload.get("max_sources") or 5)
    result: dict[str, Any] = execute_discovery_task(
        project_root=context.project_root,
        db_path=context.db_path,
        research_id=research_id,
        backend=backend,
        resolve_write=context.resolve_write,
        max_sources=max_sources,
    )

    outputs = [_relative_output(context, result["raw_note_path"])]
    outputs.extend(_relative_output(context, path) for path in result.get("snapshots") or [])
    return HandlerResult(
        status="completed",
        outputs=tuple(outputs),
        recommendation="curation",
        detail={
            "research_id": result["research_id"],
            "sources_count": result.get("sources_count"),
            "backend": result.get("backend"),
            "snapshots": list(result.get("snapshots") or []),
        },
    )


def run_curation(task: Task, agent: AgentSpec, context: WorkPacketContext) -> HandlerResult:
    """Curation handler backed by the existing deterministic curator executor."""
    from quant_brain.curation.executor import execute_curator_task

    research_id = task.payload.get("research_id")
    result = execute_curator_task(
        project_root=context.project_root,
        db_path=context.db_path,
        research_id=research_id,
    )

    outputs = [_relative_output(context, result.curator_note_path)]
    outputs.extend(_relative_output(context, path) for path in result.promoted_paths)

    return HandlerResult(
        status="completed",
        outputs=tuple(outputs),
        recommendation=None,
        detail={
            "research_id": result.research_id,
            "curator_status": result.status,
            "promoted_sources_count": result.promoted_sources_count,
            "skipped_sources_count": result.skipped_sources_count,
        },
    )


def register_default_handlers() -> None:
    """Bind the shipped handlers to their registered task types."""
    register_handler("discovery", "research_scout", run_discovery)
    register_handler("curation", "knowledge_curator", run_curation)

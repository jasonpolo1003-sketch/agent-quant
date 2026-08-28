from __future__ import annotations

from pathlib import Path
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


def run_discovery(task: Task, agent: AgentSpec, context: WorkPacketContext) -> HandlerResult:
    """Discovery handler.

    Currently backed by the deterministic starter-source executor. Phase 6
    replaces the implementation behind this same registration with live Agent
    Reach discovery plus Qwen extraction -- the dispatcher must not change.
    """
    from quant_brain.research.executor import execute_research_task

    research_id = task.payload.get("research_id")
    result: dict[str, Any] = execute_research_task(
        project_root=context.project_root,
        db_path=context.db_path,
        research_id=research_id,
    )

    output = _relative_output(context, result["raw_note_path"])
    return HandlerResult(
        status="completed",
        outputs=(output,),
        recommendation="curation",
        detail={
            "research_id": result["research_id"],
            "sources_count": result.get("sources_count"),
            "implementation": "deterministic-starter-sources",
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
    """Bind the shipped deterministic handlers to their task types."""
    register_handler("discovery", "research_scout", run_discovery)
    register_handler("curation", "knowledge_curator", run_curation)

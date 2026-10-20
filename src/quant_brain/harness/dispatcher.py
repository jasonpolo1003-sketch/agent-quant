from __future__ import annotations

import time
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

from quant_brain.config import PROJECT_ROOT
from quant_brain.db.init_db import DEFAULT_DB_PATH, connect
from quant_brain.harness.migrations import apply_migrations
from quant_brain.harness.paths import PathViolation, resolve_write_target
from quant_brain.harness.registry import AgentSpec, agents_for_task_type, load_registry
from quant_brain.ops.events import record_event


class DispatchError(Exception):
    """Base class for routing failures."""


class NoCapableAgent(DispatchError):
    def __init__(self, task_type: str, known: list[str]) -> None:
        self.task_type = task_type
        self.known = known
        super().__init__(
            f"no enabled agent handles task type {task_type!r}; registry contains {known}"
        )


class AmbiguousDispatch(DispatchError):
    def __init__(self, task_type: str, candidates: list[str]) -> None:
        self.task_type = task_type
        self.candidates = candidates
        super().__init__(
            f"task type {task_type!r} is claimed by multiple enabled agents {candidates}; "
            "ambiguity is a design decision for a human, not a routing heuristic"
        )


class NoHandlerRegistered(DispatchError):
    def __init__(self, task_type: str, agent_name: str) -> None:
        super().__init__(
            f"no handler registered for task type {task_type!r} on agent {agent_name!r}"
        )


class ReentrantDispatch(DispatchError):
    """Raised when a handler tries to dispatch another agent.

    Agents complete one bounded task and return a recommendation; the harness
    decides what runs next. Allowing agents to spawn agents makes runs
    irreproducible and costs unbounded. See PLAN.md section 2.
    """


@dataclass(frozen=True)
class Task:
    task_id: str
    task_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    run_id: str = ""

    def with_defaults(self) -> Task:
        return self if self.run_id else Task(
            task_id=self.task_id,
            task_type=self.task_type,
            payload=self.payload,
            run_id=f"RUN-{uuid4().hex[:10]}",
        )


@dataclass(frozen=True)
class WorkPacketContext:
    project_root: Path
    db_path: str
    run_id: str
    allowed_read_paths: tuple[str, ...]
    allowed_write_paths: tuple[str, ...]

    def resolve_write(self, target: str | Path) -> Path:
        """Resolve a write target against this agent's declared paths."""
        return resolve_write_target(self.project_root, target, self.allowed_write_paths)


@dataclass(frozen=True)
class HandlerResult:
    status: str
    outputs: tuple[str, ...] = ()
    recommendation: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DispatchResult:
    run_id: str
    task_id: str
    task_type: str
    agent: str
    status: str
    outputs: tuple[str, ...]
    recommendation: str | None
    duration_seconds: float
    detail: dict[str, Any] = field(default_factory=dict)


HandlerFn = Callable[[Task, AgentSpec, WorkPacketContext], HandlerResult]

_HANDLERS: dict[tuple[str, str], HandlerFn] = {}
_IN_DISPATCH = False


def register_handler(task_type: str, agent_name: str, fn: HandlerFn) -> None:
    """Bind a callable to one (task type, agent) pair."""
    _HANDLERS[(task_type, agent_name)] = fn


def unregister_handler(task_type: str, agent_name: str) -> None:
    _HANDLERS.pop((task_type, agent_name), None)


def registered_handlers() -> list[tuple[str, str]]:
    return sorted(_HANDLERS)


@contextmanager
def _dispatch_guard():
    """Block re-entrant dispatch so an agent cannot spawn another agent."""
    global _IN_DISPATCH
    if _IN_DISPATCH:
        raise ReentrantDispatch(
            "a handler attempted to dispatch another agent; the harness controls "
            "sequencing -- return a recommendation instead"
        )
    _IN_DISPATCH = True
    try:
        yield
    finally:
        _IN_DISPATCH = False


def select_agent(
    task_type: str,
    registry: dict[str, AgentSpec],
) -> AgentSpec:
    """Return the one enabled agent that handles this task type.

    Zero or many candidates is an error, never a heuristic pick: silent
    selection makes a run impossible to reproduce.
    """
    candidates = agents_for_task_type(registry, task_type)
    if not candidates:
        raise NoCapableAgent(task_type, sorted(registry))
    if len(candidates) > 1:
        raise AmbiguousDispatch(task_type, [spec.name for spec in candidates])
    return candidates[0]


def _record_task_row(db_path: str | Path, task: Task, agent: AgentSpec) -> None:
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO agent_tasks (task_id, agent_role, status, model, task_type, run_id)
            VALUES (?, ?, 'running', ?, ?, ?)
            ON CONFLICT(task_id) DO UPDATE SET
                agent_role = excluded.agent_role,
                status = 'running',
                model = excluded.model,
                task_type = excluded.task_type,
                run_id = excluded.run_id,
                started_at = CURRENT_TIMESTAMP,
                completed_at = NULL,
                error = NULL
            """,
            (task.task_id, agent.name, agent.model, task.task_type, task.run_id),
        )
        conn.commit()


def _finish_task_row(
    db_path: str | Path,
    task_id: str,
    status: str,
    output_path: str | None,
    error: str | None,
) -> None:
    with connect(db_path) as conn:
        conn.execute(
            """
            UPDATE agent_tasks
            SET status = ?, output_path = ?, error = ?, completed_at = CURRENT_TIMESTAMP
            WHERE task_id = ?
            """,
            (status, output_path, error, task_id),
        )
        conn.commit()


def _secondary(
    failures: list[dict[str, str]], step: str, fn: Callable[..., Any], *args: Any, **kwargs: Any
) -> tuple[bool, Any]:
    """Run one failure-recording step; absorb and record an ordinary failure.

    Same contract as the research executor's ``_attempt``, kept local so the
    harness does not import from a research module. ``Exception`` only:
    KeyboardInterrupt and SystemExit must propagate.
    """
    try:
        return True, fn(*args, **kwargs)
    except Exception as exc:
        failures.append({"step": step, "error_type": type(exc).__name__, "error": str(exc)})
        return False, None


def _record_dispatch_failure(
    exc: BaseException,
    db_path: str | Path,
    task_id: str,
    emit: Callable[..., None],
    *,
    first_event: tuple[str, str, str, dict[str, Any], str],
    duration: float,
) -> None:
    """Record a handler failure without ever replacing it.

    Each write is attempted independently, so a failing event cannot stop the
    task row from being finalized. What could not be recorded is attached to
    ``exc`` itself -- the one channel that survives a broken database -- and the
    note states the task row's real state rather than assuming it.
    """
    failures: list[dict[str, str]] = []
    _secondary(failures, f"{first_event[0]}_event", emit, *first_event)
    _secondary(
        failures,
        "dispatch_failed_event",
        emit,
        "dispatch_failed",
        "failed",
        str(exc),
        {"error": type(exc).__name__, "duration_seconds": duration},
        "dispatch",
    )
    finalized, _ = _secondary(
        failures, "finalize_task", _finish_task_row, db_path, task_id, "failed", None, str(exc)
    )
    row = "failed" if finalized else "unconfirmed (finalization update failed; state not verified)"
    for failure in failures:
        exc.add_note(
            f"dispatch {failure['step']} failed "
            f"({failure['error_type']}: {failure['error']}); task_row={row}"
        )


def dispatch(
    task: Task,
    *,
    project_root: str | Path = PROJECT_ROOT,
    db_path: str | Path = DEFAULT_DB_PATH,
    registry: dict[str, AgentSpec] | None = None,
    dry_run: bool = False,
) -> DispatchResult:
    """Route one typed task to the agent qualified to run it."""
    root = Path(project_root)
    apply_migrations(db_path)
    task = task.with_defaults()
    registry = registry if registry is not None else load_registry(root)
    agent = select_agent(task.task_type, registry)

    context = WorkPacketContext(
        project_root=root,
        db_path=str(db_path),
        run_id=task.run_id,
        allowed_read_paths=agent.allowed_read_paths,
        allowed_write_paths=agent.allowed_write_paths,
    )

    if dry_run:
        # Explain the routing decision without executing: this is most of the
        # debugging value of a harness.
        return DispatchResult(
            run_id=task.run_id,
            task_id=task.task_id,
            task_type=task.task_type,
            agent=agent.name,
            status="dry_run",
            outputs=(),
            recommendation=None,
            duration_seconds=0.0,
            detail={
                "model": agent.model,
                "allowed_read_paths": list(agent.allowed_read_paths),
                "allowed_write_paths": list(agent.allowed_write_paths),
                "output_contract": agent.output_contract,
                "handler_registered": (task.task_type, agent.name) in _HANDLERS,
            },
        )

    handler = _HANDLERS.get((task.task_type, agent.name))
    if handler is None:
        raise NoHandlerRegistered(task.task_type, agent.name)

    def emit(event_type: str, status: str, message: str, payload: dict[str, Any], stage: str) -> None:
        record_event(
            db_path,
            run_id=task.run_id,
            task_id=task.task_id,
            agent_role=agent.name,
            stage=stage,
            status=status,
            event_type=event_type,
            message=message,
            payload=payload,
        )

    _record_task_row(db_path, task, agent)
    emit(
        "dispatch_started",
        "running",
        f"Routing {task.task_type} to {agent.name}",
        {
            "task_type": task.task_type,
            "model": agent.model,
            "read_path_count": len(agent.allowed_read_paths),
            "write_path_count": len(agent.allowed_write_paths),
        },
        "dispatch",
    )

    started = time.monotonic()
    try:
        with _dispatch_guard():
            result = handler(task, agent, context)
            # Validated inside the guarded block so a rejected claim finalizes
            # through the same fail-closed path as a handler exception. A
            # handler must not claim outputs it was never allowed to write.
            for output in result.outputs:
                resolve_write_target(root, output, agent.allowed_write_paths)
    except PathViolation as exc:
        duration = time.monotonic() - started
        _record_dispatch_failure(
            exc,
            db_path,
            task.task_id,
            emit,
            first_event=(
                "path_violation",
                "failed",
                "Handler attempted a write outside its declared paths",
                {"target": exc.target, "allowed": list(exc.allowed)},
                "dispatch",
            ),
            duration=duration,
        )
        raise
    except Exception as exc:
        duration = time.monotonic() - started
        _record_dispatch_failure(
            exc,
            db_path,
            task.task_id,
            emit,
            first_event=(
                "handler_failed",
                "failed",
                str(exc),
                {"error": type(exc).__name__},
                task.task_type,
            ),
            duration=duration,
        )
        raise

    duration = time.monotonic() - started

    emit(
        "handler_completed",
        result.status,
        f"{agent.name} finished {task.task_type}",
        {
            "outputs": list(result.outputs),
            "recommendation": result.recommendation,
            "duration_seconds": duration,
        },
        task.task_type,
    )
    status = "completed" if result.status == "completed" else result.status
    emit(
        "dispatch_completed" if status == "completed" else "dispatch_failed",
        status,
        f"Dispatch {status} for {task.task_id}",
        {"duration_seconds": duration},
        "dispatch",
    )
    _finish_task_row(
        db_path,
        task.task_id,
        status,
        result.outputs[0] if result.outputs else None,
        None if status == "completed" else result.detail.get("error"),
    )

    return DispatchResult(
        run_id=task.run_id,
        task_id=task.task_id,
        task_type=task.task_type,
        agent=agent.name,
        status=status,
        outputs=result.outputs,
        recommendation=result.recommendation,
        duration_seconds=duration,
        detail=result.detail,
    )

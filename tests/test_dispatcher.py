import pytest

from quant_brain.db.init_db import connect, init_database
from quant_brain.harness.dispatcher import (
    AmbiguousDispatch,
    HandlerResult,
    NoCapableAgent,
    NoHandlerRegistered,
    ReentrantDispatch,
    Task,
    dispatch,
    register_handler,
    select_agent,
    unregister_handler,
)
from quant_brain.harness.migrations import apply_migrations
from quant_brain.harness.paths import PathViolation
from quant_brain.harness.registry import load_registry
from quant_brain.ops.events import list_events, summarize_run

AGENT_TEMPLATE = """---
name: {name}
handles: [{handles}]
model: {model}
enabled: {enabled}
allowed_read_paths:
  - brain/01_Sources/
allowed_write_paths:
  - brain/00_Inbox/Raw_Research/
output_contract: raw_research_note_v1
---

# {name}

Role prose.
"""


def write_agent(root, name, handles="discovery", model="null", enabled="true"):
    agents_dir = root / "agents"
    agents_dir.mkdir(exist_ok=True)
    (agents_dir / f"{name}.md").write_text(
        AGENT_TEMPLATE.format(name=name, handles=handles, model=model, enabled=enabled),
        encoding="utf-8",
    )


@pytest.fixture
def project(tmp_path):
    db_path = tmp_path / "brain.sqlite"
    init_database(db_path)
    apply_migrations(db_path)
    write_agent(tmp_path, "research_scout")
    (tmp_path / "brain" / "00_Inbox" / "Raw_Research").mkdir(parents=True)
    return tmp_path, db_path


@pytest.fixture(autouse=True)
def clean_handlers():
    yield
    unregister_handler("discovery", "research_scout")
    unregister_handler("discovery", "other_scout")
    unregister_handler("curation", "knowledge_curator")


def test_select_agent_routes_to_the_single_capable_agent(project):
    root, _ = project
    registry = load_registry(root)

    assert select_agent("discovery", registry).name == "research_scout"


def test_no_capable_agent_raises_loudly(project):
    root, _ = project
    registry = load_registry(root)

    with pytest.raises(NoCapableAgent) as exc:
        select_agent("extraction", registry)

    assert "extraction" in str(exc.value)
    assert "research_scout" in str(exc.value)


def test_ambiguous_dispatch_raises_instead_of_picking(project):
    root, _ = project
    write_agent(root, "other_scout", handles="discovery")
    registry = load_registry(root)

    with pytest.raises(AmbiguousDispatch) as exc:
        select_agent("discovery", registry)

    assert "other_scout" in str(exc.value)
    assert "research_scout" in str(exc.value)


def test_disabled_agent_is_not_a_candidate(project):
    root, _ = project
    write_agent(root, "research_scout", enabled="false")
    registry = load_registry(root)

    with pytest.raises(NoCapableAgent):
        select_agent("discovery", registry)


def test_missing_handler_raises(project):
    root, db_path = project

    with pytest.raises(NoHandlerRegistered):
        dispatch(
            Task(task_id="T-1", task_type="discovery"),
            project_root=root,
            db_path=db_path,
        )


def test_dispatch_runs_handler_and_records_events(project):
    root, db_path = project
    seen = {}

    def handler(task, agent, context):
        seen["agent"] = agent.name
        seen["writes"] = agent.allowed_write_paths
        target = context.resolve_write("brain/00_Inbox/Raw_Research/out.md")
        target.write_text("result", encoding="utf-8")
        return HandlerResult(
            status="completed",
            outputs=("brain/00_Inbox/Raw_Research/out.md",),
            recommendation="curation",
        )

    register_handler("discovery", "research_scout", handler)
    result = dispatch(
        Task(task_id="T-2", task_type="discovery", payload={"research_id": "RQ-1"}),
        project_root=root,
        db_path=db_path,
    )

    assert seen["agent"] == "research_scout"
    # The handler received the agent's declared paths, not caller-supplied ones.
    assert seen["writes"] == ("brain/00_Inbox/Raw_Research/",)
    assert result.status == "completed"
    assert result.recommendation == "curation"
    assert result.outputs == ("brain/00_Inbox/Raw_Research/out.md",)
    assert (root / "brain/00_Inbox/Raw_Research/out.md").exists()

    events = list_events(db_path, run_id=result.run_id)
    types = [event["event_type"] for event in events]
    assert types == ["dispatch_started", "handler_completed", "dispatch_completed"]

    state = summarize_run(events)
    assert state["agents"]["research_scout"]["status"] == "completed"
    assert state["task_id"] == "T-2"


def test_run_is_reconstructable_from_events_alone(project):
    root, db_path = project

    def handler(task, agent, context):
        return HandlerResult(status="completed")

    register_handler("discovery", "research_scout", handler)
    result = dispatch(Task(task_id="T-3", task_type="discovery"), project_root=root, db_path=db_path)

    state = summarize_run(list_events(db_path, run_id=result.run_id))

    assert state["run_id"] == result.run_id
    assert state["event_count"] == 3
    assert state["agents"]["research_scout"]["stage"] == "dispatch"


def test_handler_write_outside_declared_paths_is_blocked_and_recorded(project):
    root, db_path = project

    def rogue_handler(task, agent, context):
        context.resolve_write("brain/01_Sources/stolen.md")
        return HandlerResult(status="completed")

    register_handler("discovery", "research_scout", rogue_handler)

    with pytest.raises(PathViolation):
        dispatch(Task(task_id="T-4", task_type="discovery"), project_root=root, db_path=db_path)

    assert not (root / "brain/01_Sources/stolen.md").exists()

    events = list_events(db_path, run_id=_only_run_id(db_path))
    types = [event["event_type"] for event in events]
    assert "path_violation" in types
    assert types[-1] == "dispatch_failed"


def test_claimed_output_outside_declared_paths_is_rejected(project):
    root, db_path = project

    def lying_handler(task, agent, context):
        # Never touched resolve_write, so the harness must catch the claim.
        return HandlerResult(status="completed", outputs=("brain/01_Sources/x.md",))

    register_handler("discovery", "research_scout", lying_handler)

    with pytest.raises(PathViolation):
        dispatch(Task(task_id="T-5", task_type="discovery"), project_root=root, db_path=db_path)


def test_handler_cannot_dispatch_another_agent(project):
    root, db_path = project

    def reentrant_handler(task, agent, context):
        dispatch(Task(task_id="T-inner", task_type="discovery"), project_root=root, db_path=db_path)
        return HandlerResult(status="completed")

    register_handler("discovery", "research_scout", reentrant_handler)

    with pytest.raises(ReentrantDispatch):
        dispatch(Task(task_id="T-6", task_type="discovery"), project_root=root, db_path=db_path)


def test_handler_failure_marks_task_failed_and_records_events(project):
    root, db_path = project

    def failing_handler(task, agent, context):
        raise RuntimeError("handler exploded")

    register_handler("discovery", "research_scout", failing_handler)

    with pytest.raises(RuntimeError, match="handler exploded"):
        dispatch(Task(task_id="T-7", task_type="discovery"), project_root=root, db_path=db_path)

    with connect(db_path) as conn:
        row = conn.execute("SELECT status, error FROM agent_tasks WHERE task_id = 'T-7'").fetchone()
    assert row["status"] == "failed"
    assert "handler exploded" in row["error"]

    types = [e["event_type"] for e in list_events(db_path, run_id=_only_run_id(db_path))]
    assert "handler_failed" in types
    assert types[-1] == "dispatch_failed"


def test_dry_run_explains_routing_without_executing(project):
    root, db_path = project
    calls = []

    def handler(task, agent, context):
        calls.append(task.task_id)
        return HandlerResult(status="completed")

    register_handler("discovery", "research_scout", handler)
    result = dispatch(
        Task(task_id="T-8", task_type="discovery"),
        project_root=root,
        db_path=db_path,
        dry_run=True,
    )

    assert calls == []
    assert result.status == "dry_run"
    assert result.agent == "research_scout"
    assert result.detail["handler_registered"] is True
    assert result.detail["allowed_write_paths"] == ["brain/00_Inbox/Raw_Research/"]
    assert list_events(db_path, run_id=result.run_id) == []


def test_dispatch_records_task_row_with_type_and_run(project):
    root, db_path = project

    def handler(task, agent, context):
        return HandlerResult(status="completed")

    register_handler("discovery", "research_scout", handler)
    result = dispatch(Task(task_id="T-9", task_type="discovery"), project_root=root, db_path=db_path)

    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT agent_role, status, task_type, run_id FROM agent_tasks WHERE task_id = 'T-9'"
        ).fetchone()

    assert row["agent_role"] == "research_scout"
    assert row["status"] == "completed"
    assert row["task_type"] == "discovery"
    assert row["run_id"] == result.run_id


def _only_run_id(db_path):
    with connect(db_path) as conn:
        row = conn.execute("SELECT run_id FROM agent_events ORDER BY event_id DESC LIMIT 1").fetchone()
    return row["run_id"]

"""The dispatcher must record a handler failure without ever replacing it.

Its failure branch used to run ``emit(first event) -> emit(dispatch_failed) ->
_finish_task_row -> raise`` with nothing guarded: a database error in any of
those raised from inside the ``except`` block, so the caller saw the diagnostic
error instead of the handler's, and a failing event also stopped the task row
from being finalized. Each write is now an independent attempt, secondary
failures ride on the original exception as notes, and a note never claims the
task row was finalized when that update did not happen.
"""

import sqlite3
import traceback

import pytest
from test_dispatcher import write_agent

from quant_brain.db.init_db import connect, init_database
from quant_brain.harness import dispatcher
from quant_brain.harness.dispatcher import HandlerResult, Task, dispatch, register_handler
from quant_brain.harness.migrations import apply_migrations
from quant_brain.harness.paths import PathViolation
from quant_brain.ops.events import list_events


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
    dispatcher.unregister_handler("discovery", "research_scout")


@pytest.fixture
def original():
    """Register a handler that raises; capture the exact object it raised."""
    raised: list[BaseException] = []

    def install(exc: BaseException) -> list[BaseException]:
        def exploding_handler(_task, _agent, _context):
            raised.append(exc)
            raise exc

        register_handler("discovery", "research_scout", exploding_handler)
        return raised

    return install


def fail_events(monkeypatch, *event_types, error=None):
    real = dispatcher.record_event

    def wrapper(db_path, **kwargs):
        if kwargs.get("event_type") in event_types:
            raise error or sqlite3.OperationalError("database is locked")
        return real(db_path, **kwargs)

    monkeypatch.setattr(dispatcher, "record_event", wrapper)


def fail_finalization(monkeypatch, error=None):
    """Only the *failed* finalization raises; success paths are untouched."""
    real = dispatcher._finish_task_row

    def wrapper(db_path, task_id, status, output_path, err):
        if status == "failed":
            raise error or sqlite3.OperationalError("database is locked")
        return real(db_path, task_id, status, output_path, err)

    monkeypatch.setattr(dispatcher, "_finish_task_row", wrapper)


def run(project, run_id="RUN-x", expected=RuntimeError):
    root, db_path = project
    task = Task(task_id=f"T-{run_id}", task_type="discovery", payload={}, run_id=run_id)
    with pytest.raises(expected) as excinfo:
        dispatch(task, project_root=root, db_path=db_path)
    return db_path, excinfo


def row_status(db_path, task_id):
    with connect(db_path) as conn:
        return conn.execute(
            "SELECT status FROM agent_tasks WHERE task_id = ?", (task_id,)
        ).fetchone()["status"]


def types(db_path, run_id):
    return [e["event_type"] for e in list_events(db_path, run_id=run_id)]


def notes(excinfo):
    return "\n".join(getattr(excinfo.value, "__notes__", []))


def assert_original(excinfo, raised):
    assert excinfo.value is raised[0], "the handler's own exception object must propagate"
    frames = [f.name for f in traceback.extract_tb(excinfo.value.__traceback__)]
    assert "exploding_handler" in frames, "the handler's traceback must be preserved"


def test_a_failing_handler_failed_event_does_not_stop_the_rest(project, original, monkeypatch):
    raised = original(RuntimeError("handler exploded"))
    fail_events(monkeypatch, "handler_failed")

    db_path, excinfo = run(project)

    assert_original(excinfo, raised)
    assert "dispatch_failed" in types(db_path, "RUN-x")
    assert row_status(db_path, "T-RUN-x") == "failed"
    assert "dispatch handler_failed_event failed (OperationalError" in notes(excinfo)
    assert "task_row=failed" in notes(excinfo)


def test_a_failing_dispatch_failed_event_still_finalizes(project, original, monkeypatch):
    raised = original(RuntimeError("handler exploded"))
    fail_events(monkeypatch, "dispatch_failed")

    db_path, excinfo = run(project)

    assert_original(excinfo, raised)
    assert "handler_failed" in types(db_path, "RUN-x")
    assert row_status(db_path, "T-RUN-x") == "failed"
    assert "dispatch dispatch_failed_event failed" in notes(excinfo)


def test_a_failed_finalization_is_reported_not_claimed(project, original, monkeypatch):
    raised = original(RuntimeError("handler exploded"))
    fail_finalization(monkeypatch)

    db_path, excinfo = run(project)

    assert_original(excinfo, raised)
    # The test can observe the row still says running; the note must not
    # assume that, only that finalization could not be confirmed.
    assert row_status(db_path, "T-RUN-x") == "running"
    assert "dispatch finalize_task failed (OperationalError" in notes(excinfo)
    assert "task_row=unconfirmed (finalization update failed" in notes(excinfo)
    assert "running" not in notes(excinfo)
    assert "task_row=failed" not in notes(excinfo)
    assert {"handler_failed", "dispatch_failed"} <= set(types(db_path, "RUN-x"))


def test_every_failure_write_failing_still_propagates_the_original(project, original, monkeypatch):
    raised = original(RuntimeError("handler exploded"))
    fail_events(monkeypatch, "handler_failed", "dispatch_failed")
    fail_finalization(monkeypatch)

    db_path, excinfo = run(project)

    assert_original(excinfo, raised)
    assert row_status(db_path, "T-RUN-x") == "running"
    text = notes(excinfo)
    for step in ("handler_failed_event", "dispatch_failed_event", "finalize_task"):
        assert f"dispatch {step} failed" in text


def test_a_handler_path_violation_survives_its_own_event_failing(project, original, monkeypatch):
    raised = original(PathViolation("brain/01_Sources/x.md", ("brain/00_Inbox/Raw_Research/",)))
    fail_events(monkeypatch, "path_violation")

    db_path, excinfo = run(project, expected=PathViolation)

    assert_original(excinfo, raised)
    assert "dispatch_failed" in types(db_path, "RUN-x")
    assert row_status(db_path, "T-RUN-x") == "failed"
    assert "dispatch path_violation_event failed" in notes(excinfo)


def test_keyboard_interrupt_during_finalization_is_not_swallowed(project, original, monkeypatch):
    original(RuntimeError("handler exploded"))
    fail_finalization(monkeypatch, error=KeyboardInterrupt())

    run(project, expected=KeyboardInterrupt)


def test_a_clean_handler_failure_adds_no_notes(project, original):
    raised = original(RuntimeError("handler exploded"))

    db_path, excinfo = run(project)

    assert_original(excinfo, raised)
    assert not getattr(excinfo.value, "__notes__", None)
    assert row_status(db_path, "T-RUN-x") == "failed"
    assert types(db_path, "RUN-x")[-2:] == ["handler_failed", "dispatch_failed"]


def test_successful_dispatch_is_unchanged(project):
    root, db_path = project

    def handler(_task, _agent, _context):
        return HandlerResult(status="completed", outputs=(), recommendation=None)

    register_handler("discovery", "research_scout", handler)
    result = dispatch(
        Task(task_id="T-ok", task_type="discovery", payload={}, run_id="RUN-ok"),
        project_root=root,
        db_path=db_path,
    )

    assert result.status == "completed"
    assert row_status(db_path, "T-ok") == "completed"
    assert types(db_path, "RUN-ok") == [
        "dispatch_started",
        "handler_completed",
        "dispatch_completed",
    ]

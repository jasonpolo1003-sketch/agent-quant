"""Discovery's fail-closed path must survive failures in its own diagnostics.

A Failed_Runs receipt that cannot be written, or an event the database refuses,
is secondary to the research failure that triggered it. Before this, a
PathViolation on the receipt path (or any non-OSError, or any database error in
the surrounding events or the reset) escaped ``_fail_closed_discovery``: raw-note
cleanup and the ``queued`` reset were skipped, and the original research
exception was replaced by the diagnostic one.

Each test drives the real dispatcher -> scout handler -> executor path, spies on
(never replaces) the real ``_fail_closed_discovery``, and checks that the
*original* exception object propagates with its traceback.
"""

import sqlite3
import traceback
from pathlib import Path

import pytest
from test_discovery_handler import (  # reuse the established fixtures
    CURATOR_DECLARATION,
    SCOUT_DECLARATION,
    stub_validated_qwen,
)
from test_failed_run_provenance import THREE_URLS, _dispatch, _receipt_payload

from quant_brain.db.init_db import init_database
from quant_brain.harness.dispatcher import dispatch, unregister_handler
from quant_brain.harness.paths import PathViolation, resolve_write_target
from quant_brain.llm.qwen_call import QwenAttempt, QwenValidationError
from quant_brain.research import executor
from quant_brain.research.intake import add_research_question, update_research_status

ALL_WRITE_PATHS = (
    "brain/00_Inbox/Raw_Research/",
    "brain/00_Inbox/Source_Snapshots/",
    "brain/00_Inbox/Failed_Runs/",
)


@pytest.fixture
def project(tmp_path):
    db_path = tmp_path / "brain.sqlite"
    init_database(db_path)
    agents = tmp_path / "agents"
    agents.mkdir()
    (agents / "research_scout.md").write_text(SCOUT_DECLARATION, encoding="utf-8")
    (agents / "knowledge_curator.md").write_text(CURATOR_DECLARATION, encoding="utf-8")
    for folder in ("Raw_Research", "Source_Snapshots", "Failed_Runs", "Curator_Reviews"):
        (tmp_path / "brain" / "00_Inbox" / folder).mkdir(parents=True)
    return tmp_path, db_path


@pytest.fixture(autouse=True)
def clean_handlers():
    yield
    unregister_handler("discovery", "research_scout")
    unregister_handler("curation", "knowledge_curator")


@pytest.fixture
def original(monkeypatch):
    """The research failure: the Qwen ladder rejects every attempt.

    Returns a holder that captures the exact exception object raised, so tests
    can assert identity rather than merely type.
    """
    raised: list[QwenValidationError] = []

    def failing_qwen_runner(_prompt, _evidence, **_kwargs):
        attempt = QwenAttempt(
            model="qwen3:14b",
            duration_seconds=1.0,
            prompt_hash="p" * 64,
            response_hash="r" * 64,
            validator_ok=False,
            validator_reasons=("quote:S1: exact evidence is absent from snapshot",),
        )
        exc = QwenValidationError([attempt])
        raised.append(exc)
        raise exc

    monkeypatch.setattr("quant_brain.llm.qwen_call.qwen_call", failing_qwen_runner)
    return raised


@pytest.fixture
def spy(monkeypatch):
    """Wrap the real handler; record its inputs and the note's state on entry."""
    calls: list[dict] = []
    real = executor._fail_closed_discovery

    def wrapper(**kwargs):
        note = kwargs["note_path"]
        calls.append(
            {
                **kwargs,
                "note_existed": note is not None and note.exists(),
                "note_bytes": note.read_bytes() if note is not None and note.exists() else None,
            }
        )
        return real(**kwargs)

    monkeypatch.setattr(executor, "_fail_closed_discovery", wrapper)
    return calls


def fail_events(monkeypatch, exc_factory, *event_types):
    """Make only the named scout events raise; every other event is real."""
    real = executor._record_scout_event

    def wrapper(db_path, **kwargs):
        if kwargs.get("event_type") in event_types:
            raise exc_factory()
        return real(db_path, **kwargs)

    monkeypatch.setattr(executor, "_record_scout_event", wrapper)


def run(project, run_id, *, research_id=None):
    root, db_path, research_id, task = _dispatch(
        project, urls=THREE_URLS, run_id=run_id, research_id=research_id
    )
    with pytest.raises(QwenValidationError) as excinfo:
        dispatch(task, project_root=root, db_path=db_path)
    return root, db_path, research_id, excinfo


def scaffold_path(root, research_id):
    return root / "brain" / "00_Inbox" / "Raw_Research" / f"{research_id}.md"


def question_state(db_path, research_id):
    with sqlite3.connect(db_path) as conn:
        return conn.execute(
            "SELECT status, raw_note_path FROM research_questions WHERE research_id = ?",
            (research_id,),
        ).fetchone()


def task_status(db_path, task_id):
    with sqlite3.connect(db_path) as conn:
        return conn.execute(
            "SELECT status FROM agent_tasks WHERE task_id = ?", (task_id,)
        ).fetchone()[0]


def event_types(db_path, run_id):
    with sqlite3.connect(db_path) as conn:
        return [
            row[0]
            for row in conn.execute(
                "SELECT event_type FROM agent_events WHERE run_id = ? ORDER BY event_id",
                (run_id,),
            )
        ]


def assert_original_propagated(excinfo, original, spy, db_path, run_id):
    """The checks every case shares."""
    assert len(spy) == 1, "the real fail-closed handler must run exactly once"
    assert spy[0]["stage"] == "qwen_extract"
    assert excinfo.value is original[0], "the original exception object must propagate"
    frames = [frame.name for frame in traceback.extract_tb(excinfo.value.__traceback__)]
    assert "failing_qwen_runner" in frames, "the original traceback must be preserved"
    assert task_status(db_path, f"T-{run_id}") == "failed"


def notes(excinfo):
    return "\n".join(getattr(excinfo.value, "__notes__", []))


def receipt_text(root, run_id):
    return (root / "brain" / "00_Inbox" / "Failed_Runs" / f"{run_id}.md").read_text(
        encoding="utf-8"
    )


def assert_held_receipt(root, run_id, leftover):
    """A failed raw-note recovery must never read as an ordinary retry."""
    text = receipt_text(root, run_id)
    assert "retryable: false" in text
    assert "Manual inspection required" in text
    assert str(leftover) in text
    assert "was returned to `queued`" not in text
    assert "dispatch_task.py --type discovery" not in text
    # Runnable as written: two literal release commands, no placeholder to fill.
    assert "clear_raw_note_path=True)" in text
    assert "clear_raw_note_path=False)" in text
    assert "<" not in text.split("## Retry", 1)[1]


def assert_complete_recovery(root, run_id, raw_note):
    """Preserving or restoring a pre-existing note is success, not a cleanup failure."""
    recovery = _receipt_payload(root)["recovery"]
    assert recovery["raw_note"] == raw_note
    assert recovery["question"] == "queued"
    assert recovery["complete"] is True
    text = receipt_text(root, run_id)
    assert "retryable: true" in text
    assert "was returned to `queued`" in text


# --- receipt write failures -------------------------------------------------


def test_receipt_path_violation_does_not_skip_recovery(project, original, spy):
    """Real enforcement: Failed_Runs/ is not in the agent's write paths."""
    root, _ = project
    (root / "agents" / "research_scout.md").write_text(
        SCOUT_DECLARATION.replace("  - brain/00_Inbox/Failed_Runs/\n", ""), encoding="utf-8"
    )

    root, db_path, research_id, excinfo = run(project, "RUN-rpv")

    assert_original_propagated(excinfo, original, spy, db_path, "RUN-rpv")
    assert spy[0]["created_scaffold"] is True and spy[0]["note_existed"]
    assert not list((root / "brain" / "00_Inbox" / "Failed_Runs").iterdir())
    assert not scaffold_path(root, research_id).exists()
    assert question_state(db_path, research_id) == ("queued", None)
    assert "fail-closed receipt failed (PathViolation" in notes(excinfo)
    types = event_types(db_path, "RUN-rpv")
    assert "discovery_failed" in types
    assert "failed_run_written" not in types


def test_receipt_oserror_does_not_skip_recovery(project, original, spy):
    """Real OSError: Failed_Runs is a file, so creating the receipt fails."""
    root, _ = project
    failed_runs = root / "brain" / "00_Inbox" / "Failed_Runs"
    failed_runs.rmdir()
    failed_runs.write_text("not a directory", encoding="utf-8")

    root, db_path, research_id, excinfo = run(project, "RUN-ros")

    assert_original_propagated(excinfo, original, spy, db_path, "RUN-ros")
    assert failed_runs.read_text(encoding="utf-8") == "not a directory"
    assert not scaffold_path(root, research_id).exists()
    assert question_state(db_path, research_id) == ("queued", None)
    assert "fail-closed receipt failed" in notes(excinfo)


def test_keyboard_interrupt_is_not_swallowed(project, original, spy, monkeypatch):
    """Process control is not a diagnostic failure and must propagate."""

    def interrupted(*_args, **_kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(executor, "_write_failed_run_note", interrupted)
    root, db_path, research_id, task = _dispatch(project, urls=THREE_URLS, run_id="RUN-kbi")

    with pytest.raises(KeyboardInterrupt):
        dispatch(task, project_root=root, db_path=db_path)

    assert len(spy) == 1
    # Recovery precedes the receipt, so it had already happened.
    assert not scaffold_path(root, research_id).exists()
    assert question_state(db_path, research_id) == ("queued", None)


# --- event failures ---------------------------------------------------------

EVENT_ERRORS = [
    pytest.param(lambda: PathViolation("events", ()), id="PathViolation"),
    pytest.param(lambda: OSError("disk full"), id="OSError"),
    pytest.param(lambda: sqlite3.OperationalError("database is locked"), id="sqlite"),
]


@pytest.mark.parametrize("make_error", EVENT_ERRORS)
def test_discovery_failed_event_error_is_secondary(project, original, spy, monkeypatch, make_error):
    """This event used to run *before* the handler, unguarded."""
    fail_events(monkeypatch, make_error, "discovery_failed")

    root, db_path, research_id, excinfo = run(project, "RUN-dfe")

    assert_original_propagated(excinfo, original, spy, db_path, "RUN-dfe")
    assert not scaffold_path(root, research_id).exists()
    assert question_state(db_path, research_id) == ("queued", None)
    payload = _receipt_payload(root)
    assert payload["recovery"]["question"] == "queued"
    assert payload["recovery"]["complete"] is True
    assert [f["step"] for f in payload["recovery"]["secondary_failures"]] == [
        "discovery_failed_event"
    ]
    assert "fail-closed discovery_failed_event failed" in notes(excinfo)


@pytest.mark.parametrize("make_error", EVENT_ERRORS)
def test_failed_run_written_event_error_is_secondary(
    project, original, spy, monkeypatch, make_error
):
    """The receipt was written; an event failure must not un-write it."""
    fail_events(monkeypatch, make_error, "failed_run_written")

    root, db_path, research_id, excinfo = run(project, "RUN-fwe")

    assert_original_propagated(excinfo, original, spy, db_path, "RUN-fwe")
    assert (root / "brain" / "00_Inbox" / "Failed_Runs" / "RUN-fwe.md").exists()
    assert not scaffold_path(root, research_id).exists()
    assert question_state(db_path, research_id) == ("queued", None)
    assert "receipt=written" in notes(excinfo)
    assert "fail-closed failed_run_written_event failed" in notes(excinfo)


def test_receipt_and_both_events_failing_still_recovers(project, original, spy, monkeypatch):
    root, _ = project
    (root / "agents" / "research_scout.md").write_text(
        SCOUT_DECLARATION.replace("  - brain/00_Inbox/Failed_Runs/\n", ""), encoding="utf-8"
    )
    fail_events(
        monkeypatch,
        lambda: sqlite3.OperationalError("database is locked"),
        "discovery_failed",
        "failed_run_written",
    )

    root, db_path, research_id, excinfo = run(project, "RUN-all")

    assert_original_propagated(excinfo, original, spy, db_path, "RUN-all")
    assert not scaffold_path(root, research_id).exists()
    assert question_state(db_path, research_id) == ("queued", None)
    text = notes(excinfo)
    assert "discovery_failed_event failed" in text
    assert "receipt failed (PathViolation" in text


# --- recovery failures ------------------------------------------------------


def test_cleanup_refused_by_path_enforcement_is_not_bypassed(project, original, monkeypatch):
    """Scaffold creation and the research failure happen normally with the full
    declaration; only the recovery-time mutation is denied, by the real resolver."""
    asked: list[str] = []
    real = executor._fail_closed_discovery
    root, _ = project
    denying_paths = tuple(p for p in ALL_WRITE_PATHS if "Raw_Research" not in p)

    def denying_resolver(target):
        asked.append(str(target))
        return resolve_write_target(root, target, denying_paths)

    calls: list[dict] = []

    def spy_with_denying_resolver(**kwargs):
        note = kwargs["note_path"]
        calls.append({**kwargs, "note_bytes": note.read_bytes() if note.exists() else None})
        return real(**{**kwargs, "resolve_write": denying_resolver})

    monkeypatch.setattr(executor, "_fail_closed_discovery", spy_with_denying_resolver)

    root, db_path, research_id, excinfo = run(project, "RUN-deny")

    assert len(calls) == 1
    assert calls[0]["stage"] == "qwen_extract"
    assert calls[0]["created_scaffold"] is True
    note = scaffold_path(root, research_id)
    assert calls[0]["note_bytes"] is not None, "the scaffold existed when recovery began"
    assert excinfo.value is original[0]
    assert any(target.endswith(f"{research_id}.md") for target in asked)
    # Not bypassed: the scaffold is exactly as recovery found it.
    assert note.read_bytes() == calls[0]["note_bytes"]
    # Held, not queued, and the pointer stays with the file that is still there.
    status, pointer = question_state(db_path, research_id)
    assert status == "needs_review"
    assert Path(pointer) == note
    assert_held_receipt(root, "RUN-deny", note)
    assert "raw_note_recovery failed (PathViolation" in notes(excinfo)
    assert "question=needs_review" in notes(excinfo)
    assert "discovery_cleanup_failed" in event_types(db_path, "RUN-deny")


def test_cleanup_oserror_holds_the_question_for_review(project, original, spy, monkeypatch):
    def locked(*_args, **_kwargs):
        raise PermissionError("file is locked")

    monkeypatch.setattr(executor, "_discard_incomplete_raw_note", locked)

    root, db_path, research_id, excinfo = run(project, "RUN-cos")

    assert_original_propagated(excinfo, original, spy, db_path, "RUN-cos")
    note = scaffold_path(root, research_id)
    assert note.exists(), "a leftover the run could not remove is preserved, not retried over"
    status, pointer = question_state(db_path, research_id)
    assert status == "needs_review"
    assert Path(pointer) == note
    payload = _receipt_payload(root)
    assert payload["recovery"]["raw_note"] == "failed"
    assert payload["recovery"]["question"] == "needs_review"
    assert payload["recovery"]["complete"] is False
    assert_held_receipt(root, "RUN-cos", note)
    assert "raw_note_recovery failed (PermissionError" in notes(excinfo)


def test_reset_failure_is_reported_honestly(project, original, spy, monkeypatch):
    """The receipt must not claim the question went back to queued."""

    def locked(*_args, **_kwargs):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr("quant_brain.research.intake.reset_research_for_retry", locked)

    root, db_path, research_id, excinfo = run(project, "RUN-rst")

    assert_original_propagated(excinfo, original, spy, db_path, "RUN-rst")
    assert not scaffold_path(root, research_id).exists(), "cleanup is independent of reset"
    assert question_state(db_path, research_id)[0] != "queued"
    receipt = (root / "brain" / "00_Inbox" / "Failed_Runs" / "RUN-rst.md").read_text(
        encoding="utf-8"
    )
    assert "Recovery incomplete" in receipt
    assert "was returned to `queued`" not in receipt
    assert "retryable: false" in receipt
    assert _receipt_payload(root)["recovery"]["question"] == "update-failed"
    assert "reset_for_retry failed (OperationalError" in notes(excinfo)


def test_a_clean_failure_reports_success_from_the_flag_not_the_value(project, original, spy):
    """reset_research_for_retry returns None on success; that is not a failure."""
    root, db_path, research_id, excinfo = run(project, "RUN-clean")

    assert_original_propagated(excinfo, original, spy, db_path, "RUN-clean")
    assert question_state(db_path, research_id) == ("queued", None)
    payload = _receipt_payload(root)
    assert payload["recovery"] == {
        "raw_note": "removed",
        "question": "queued",
        "complete": True,
        "secondary_failures": [],
    }
    receipt = (root / "brain" / "00_Inbox" / "Failed_Runs" / "RUN-clean.md").read_text(
        encoding="utf-8"
    )
    assert "was returned to `queued`" in receipt
    assert "retryable: true" in receipt
    assert not getattr(excinfo.value, "__notes__", None)
    assert event_types(db_path, "RUN-clean").count("discovery_failed") == 1


# --- ownership of pre-existing notes ----------------------------------------


def _preexisting_note(project):
    root, db_path = project
    research_id = add_research_question(
        db_path, "Research ETF RSI mean reversion exit rules", "mean_reversion"
    )["research_id"]
    note = scaffold_path(root, research_id)
    original_text = (
        f"---\nid: {research_id}\ntype: raw_research\nstatus: researching\n---\n\n"
        "# Prepared note\n\nHuman-pasted finding that must survive.\n\nScout findings go here.\n"
    )
    note.write_text(original_text, encoding="utf-8")
    update_research_status(db_path, research_id, "researching", raw_note_path=str(note))
    return research_id, note, note.read_bytes()


def test_a_preexisting_note_is_never_deleted_by_an_early_failure(project, original, spy):
    """Previously unlinked: the run neither created nor modified this file."""
    research_id, note, before = _preexisting_note(project)

    root, db_path, _, excinfo = run(project, "RUN-pre", research_id=research_id)

    assert_original_propagated(excinfo, original, spy, db_path, "RUN-pre")
    assert spy[0]["created_scaffold"] is False
    assert note.read_bytes() == before
    assert question_state(db_path, research_id) == ("queued", str(note))
    assert_complete_recovery(root, "RUN-pre", "untouched-preexisting")


def test_a_restored_preexisting_note_keeps_its_pointer(project, spy, monkeypatch):
    """Restored bytes are useless if the pointer is dropped and a retry
    recreates -- and overwrites -- the note at the same deterministic path."""
    research_id, note, before = _preexisting_note(project)
    stub_validated_qwen(monkeypatch)

    def finalize_failed(*_args, **_kwargs):
        raise RuntimeError("db finalize failed")

    monkeypatch.setattr(executor, "update_research_status", finalize_failed)
    root, db_path, _, task = _dispatch(
        project, urls=THREE_URLS, run_id="RUN-rest", research_id=research_id
    )

    with pytest.raises(RuntimeError, match="db finalize failed"):
        dispatch(task, project_root=root, db_path=db_path)

    assert len(spy) == 1 and spy[0]["stage"] == "write_note"
    assert note.read_bytes() == before
    assert question_state(db_path, research_id) == ("queued", str(note))
    assert_complete_recovery(root, "RUN-rest", "restored")


# --- the needs_review hold --------------------------------------------------


def _held_question(project):
    """A question a failed run left held, with its leftover note on disk."""
    research_id, note, before = _preexisting_note(project)
    _, db_path = project
    update_research_status(db_path, research_id, "needs_review")
    return research_id, note, before


def test_explicit_dispatch_refuses_a_held_question(project, spy):
    """Refused before the task binds, so fail-closed cannot undo the hold."""
    research_id, note, before = _held_question(project)
    root, db_path, _, task = _dispatch(
        project, urls=THREE_URLS, run_id="RUN-held", research_id=research_id
    )

    with pytest.raises(ValueError, match="held for manual review"):
        dispatch(task, project_root=root, db_path=db_path)

    assert spy == [], "no recovery runs for a question that was never loaded"
    assert question_state(db_path, research_id) == ("needs_review", str(note))
    assert note.read_bytes() == before
    assert not list((root / "brain" / "00_Inbox" / "Failed_Runs").iterdir())
    assert not list((root / "brain" / "00_Inbox" / "Source_Snapshots").rglob("*"))
    assert task_status(db_path, "T-RUN-held") == "failed"


def test_queue_selection_skips_a_held_question(project):
    research_id, note, before = _held_question(project)
    root, db_path = project

    with pytest.raises(ValueError, match="no researching task found"):
        executor.execute_discovery_task(root, db_path)

    assert question_state(db_path, research_id) == ("needs_review", str(note))
    assert note.read_bytes() == before


def test_a_failed_hold_is_reported_not_claimed(project, original, spy, monkeypatch):
    """Cleanup fails AND the hold update fails: say so, and claim neither state."""

    def locked(*_args, **_kwargs):
        raise PermissionError("file is locked")

    def db_locked(*_args, **_kwargs):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(executor, "_discard_incomplete_raw_note", locked)
    monkeypatch.setattr("quant_brain.research.intake.update_research_status", db_locked)

    root, db_path, research_id, excinfo = run(project, "RUN-hold")

    assert_original_propagated(excinfo, original, spy, db_path, "RUN-hold")
    note = scaffold_path(root, research_id)
    assert note.exists()
    assert question_state(db_path, research_id)[0] == "researching"
    recovery = _receipt_payload(root)["recovery"]
    assert recovery["raw_note"] == "failed"
    assert recovery["question"] == "update-failed"
    assert recovery["complete"] is False
    text = receipt_text(root, "RUN-hold")
    assert "retryable: false" in text
    assert "Recovery incomplete" in text
    assert str(note) in text
    assert "was returned to `queued`" not in text
    assert "hold_for_review failed (OperationalError" in notes(excinfo)


# --- through the dispatcher -------------------------------------------------


def test_executor_and_dispatcher_failures_both_ride_on_the_original(
    project, original, spy, monkeypatch
):
    """End to end: a scout event fails inside discovery, then the dispatcher's
    own dispatch_failed event fails after the executor re-raises. The caller
    still gets the Qwen exception object, carrying notes from both layers."""
    from quant_brain.harness import dispatcher as dispatcher_mod

    fail_events(monkeypatch, lambda: OSError("disk full"), "discovery_failed")
    real_record = dispatcher_mod.record_event

    def dispatch_events(db_path, **kwargs):
        if kwargs.get("event_type") == "dispatch_failed":
            raise sqlite3.OperationalError("database is locked")
        return real_record(db_path, **kwargs)

    monkeypatch.setattr(dispatcher_mod, "record_event", dispatch_events)

    root, db_path, research_id, excinfo = run(project, "RUN-e2e")

    assert_original_propagated(excinfo, original, spy, db_path, "RUN-e2e")
    text = notes(excinfo)
    assert "fail-closed discovery_failed_event failed (OSError" in text
    assert "dispatch dispatch_failed_event failed (OperationalError" in text
    assert "task_row=failed" in text
    assert question_state(db_path, research_id) == ("queued", None)
    assert not scaffold_path(root, research_id).exists()

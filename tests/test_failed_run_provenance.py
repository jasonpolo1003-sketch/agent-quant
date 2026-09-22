"""A failure receipt must say what the run actually fetched.

Found by the first real Scout child run (``RUN-4e9d910742``): discovery fetched
and snapshotted five arXiv papers, the Qwen ladder then failed validation, and
the receipt recorded only ``task_id`` and ``created_scaffold``. Five snapshot
files were left on disk that no receipt and no event referenced, so nothing tied
them to the run that produced them.

The cause was that candidate evidence rode on ``error.detail``, which only
``InsufficientUpstreamSources`` defines. Provenance now belongs to the *run*, so
every post-fetch failure mode carries it -- and the snapshot keys the receipt
reads are actually populated, which they never were.
"""

import hashlib
import json
import sqlite3

import pytest
from test_discovery_handler import (  # reuse the established fixtures
    CURATOR_DECLARATION,
    PAGE_BODY,
    SCOUT_DECLARATION,
    stub_validated_qwen,
)

from quant_brain.db.init_db import init_database
from quant_brain.harness.dispatcher import Task, dispatch, unregister_handler
from quant_brain.harness.handlers import register_default_handlers
from quant_brain.llm.qwen_call import QwenAttempt, QwenValidationError
from quant_brain.research.intake import add_research_question

THREE_URLS = (
    "https://arxiv.org/abs/1411.5062",
    "https://arxiv.org/abs/2309.16008",
    "https://arxiv.org/abs/1601.04210",
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


def stub_failing_qwen(monkeypatch):
    """Reproduce the real ladder outcome: 14b, one repair, 27b, all invalid.

    Raises directly rather than recording attempts. ``_record_attempt`` falls
    back to ``db_path or DEFAULT_DB_PATH``, so a stub that emitted events
    without an explicit db_path would write into the production database.
    """

    def runner(_prompt, _evidence, **_kwargs):
        attempts = [
            QwenAttempt(
                model=model,
                duration_seconds=1.0,
                prompt_hash="p" * 64,
                response_hash="r" * 64,
                validator_ok=False,
                validator_reasons=("quote:S1: exact evidence is absent from snapshot",),
            )
            for model in ("qwen3:14b", "qwen3:14b", "qwen3.8:27b")
        ]
        raise QwenValidationError(attempts)

    monkeypatch.setattr("quant_brain.llm.qwen_call.qwen_call", runner)


def _dispatch(project, *, urls, run_id, research_id=None, resolve_write=None):
    root, db_path = project
    if research_id is None:
        research_id = add_research_question(
            db_path, "Research ETF RSI mean reversion exit rules", "mean_reversion"
        )["research_id"]
    register_default_handlers()

    def search_fn(question, method_family, *, limit):
        del question, method_family, limit
        return [
            {"title": f"paper-{i}", "url": url, "source_type": "docs", "source_quality": "primary"}
            for i, url in enumerate(urls)
        ]

    def fetch_fn(url):
        return {"url": url, "content": PAGE_BODY, "channel": "web", "backend": "fixture"}

    payload = {
        "research_id": research_id,
        "backend": "live",
        "allow_network": False,
        "search_fn": search_fn,
        "fetch_fn": fetch_fn,
    }
    task = Task(task_id=f"T-{run_id}", task_type="discovery", payload=payload, run_id=run_id)
    return root, db_path, research_id, task


def _receipt_payload(root):
    receipts = list((root / "brain" / "00_Inbox" / "Failed_Runs").glob("*.md"))
    assert len(receipts) == 1
    body = receipts[0].read_text(encoding="utf-8")
    return json.loads(body.split("```json")[1].split("```")[0])


# --- the reported defect ----------------------------------------------------


def test_a_qwen_validation_failure_records_what_was_fetched(project, monkeypatch):
    """The reported defect: the receipt named no source and no snapshot."""
    root, db_path, research_id, task = _dispatch(project, urls=THREE_URLS, run_id="RUN-qwenfail")
    stub_failing_qwen(monkeypatch)

    with pytest.raises(QwenValidationError):
        dispatch(task, project_root=root, db_path=db_path)

    payload = _receipt_payload(root)

    assert payload["run_id"] == "RUN-qwenfail"
    assert payload["task_id"] == "T-RUN-qwenfail"
    assert payload["research_id"] == research_id
    assert payload["stage"] == "qwen_extract"
    assert payload["error_type"] == "QwenValidationError"

    candidates = payload["accepted_candidates"]
    assert {c["url"] for c in candidates} == set(THREE_URLS)
    for candidate in candidates:
        assert candidate["tier"] == "primary"
        # Both were read by the receipt but never set by discovery, so every
        # receipt recorded null for them.
        assert candidate["snapshot_path"], "snapshot path must not be null"
        assert candidate["snapshot_sha256"], "snapshot hash must not be null"
        assert (root / candidate["snapshot_path"]).exists()

    assert payload["distinct_upstream_count"] == 3
    assert payload["required_upstream_count"] == 3
    assert len(payload["snapshot_paths"]) == 3


def test_the_recorded_snapshot_hash_verifies_against_the_file(project, monkeypatch):
    """A hash nobody can check is decoration. Recompute it from disk."""
    root, db_path, _, task = _dispatch(project, urls=THREE_URLS, run_id="RUN-hash")
    stub_failing_qwen(monkeypatch)

    with pytest.raises(QwenValidationError):
        dispatch(task, project_root=root, db_path=db_path)

    # The recorded hash is of the fetched content, which is what the model was
    # shown -- not of the rendered file, whose body the writer rstrips before
    # adding a single trailing newline.
    expected = hashlib.sha256(PAGE_BODY.encode("utf-8")).hexdigest()

    for candidate in _receipt_payload(root)["accepted_candidates"]:
        assert candidate["snapshot_sha256"] == expected
        # Independent agreement: the filename prefix is the same hash, and the
        # snapshot's own frontmatter records it too.
        name = candidate["snapshot_path"].split("/")[-1]
        assert name.startswith(expected[:12])
        text = (root / candidate["snapshot_path"]).read_text(encoding="utf-8")
        assert f"content_hash: {expected}" in text


def test_a_qwen_failure_still_fails_closed(project, monkeypatch):
    """Provenance is added to the receipt; nothing about containment changes."""
    root, db_path, research_id, task = _dispatch(project, urls=THREE_URLS, run_id="RUN-closed")
    stub_failing_qwen(monkeypatch)

    with pytest.raises(QwenValidationError):
        dispatch(task, project_root=root, db_path=db_path)

    note = root / "brain" / "00_Inbox" / "Raw_Research" / f"{research_id}.md"
    text = note.read_text(encoding="utf-8") if note.exists() else ""
    assert "raw_saved" not in text
    assert "curator_recommendation" not in text
    assert not (root / "brain" / "01_Sources").exists()
    assert not list((root / "brain" / "00_Inbox" / "Curator_Reviews").iterdir())

    with sqlite3.connect(db_path) as conn:
        status, raw_note_path = conn.execute(
            "SELECT status, raw_note_path FROM research_questions WHERE research_id = ?",
            (research_id,),
        ).fetchone()
        assert (status, raw_note_path) == ("queued", None)
        assert (
            conn.execute(
                "SELECT status FROM agent_tasks WHERE task_id = ?", ("T-RUN-closed",)
            ).fetchone()[0]
            == "failed"
        )


# --- the later-stage rebinding hazard ---------------------------------------


def test_a_later_failure_reports_discovery_values_not_model_values(project, monkeypatch):
    """``sources`` is rebound to model output after a *successful* qwen call.

    Reading it at failure time would describe a write_note failure with
    model-shaped values. Provenance is captured at the discover stage instead,
    so the receipt still names the tier discovery assigned and the snapshot it
    actually wrote.
    """
    root, db_path, _, task = _dispatch(project, urls=THREE_URLS, run_id="RUN-late")
    stub_validated_qwen(monkeypatch)

    monkeypatch.setattr(
        "quant_brain.research.executor.update_research_status",
        lambda *a, **k: (_ for _ in ()).throw(OSError("simulated write_note failure")),
    )

    with pytest.raises(OSError):
        dispatch(task, project_root=root, db_path=db_path)

    payload = _receipt_payload(root)
    assert payload["stage"] == "write_note"
    candidates = payload["accepted_candidates"]
    assert {c["url"] for c in candidates} == set(THREE_URLS)
    for candidate in candidates:
        assert candidate["tier"] == "primary"
        assert candidate["snapshot_path"], "discovery-side snapshot path must survive"
        assert candidate["snapshot_sha256"], "discovery-side snapshot hash must survive"


# --- early failure ----------------------------------------------------------


def test_a_discovery_failure_before_a_result_invents_no_candidate_evidence(project, monkeypatch):
    """A valid task whose discovery raises before returning a ``DiscoverResult``.

    ``discovered_provenance`` is still empty here, so this is the case
    where the carrier must add run/stage/error context without fabricating
    candidates or snapshots. The real fail-closed handler is spied on, not
    replaced, so the test proves it actually ran on this path.
    """
    root, db_path, research_id, task = _dispatch(project, urls=(), run_id="RUN-early")

    from quant_brain.research import executor

    calls = []
    real_fail_closed = executor._fail_closed_discovery

    def spy(**kwargs):
        calls.append(kwargs)
        return real_fail_closed(**kwargs)

    monkeypatch.setattr(executor, "_fail_closed_discovery", spy)

    # An empty search result makes the real live backend raise inside discover().
    with pytest.raises(Exception) as excinfo:
        dispatch(task, project_root=root, db_path=db_path)

    # The original exception propagates unchanged.
    assert type(excinfo.value).__name__ == "LiveDiscoveryError"
    assert "returned no candidates" in str(excinfo.value)

    assert len(calls) == 1
    assert calls[0]["stage"] == "discover"
    assert calls[0]["error"] is excinfo.value

    receipts = list((root / "brain" / "00_Inbox" / "Failed_Runs").glob("*.md"))
    assert [r.name for r in receipts] == ["RUN-early.md"]
    body = receipts[0].read_text(encoding="utf-8")
    assert "id: RUN-early" in body
    assert f"research_id: {research_id}" in body
    assert "stage: discover" in body
    assert "`LiveDiscoveryError`: live discovery search returned no candidates" in body

    payload = _receipt_payload(root)
    assert payload["task_id"] == "T-RUN-early"
    assert payload["stage"] == "discover"
    assert payload["error_type"] == "LiveDiscoveryError"
    # Nothing was fetched, so nothing may be claimed -- not even an empty list,
    # which would read as "searched and found zero accepted candidates".
    for key in (
        "accepted_candidates",
        "snapshot_paths",
        "distinct_upstream_count",
        "rejected_candidates",
        "search_query_expression",
    ):
        assert key not in payload, key
    assert not list((root / "brain" / "00_Inbox" / "Source_Snapshots").rglob("*"))

    with sqlite3.connect(db_path) as conn:
        assert conn.execute(
            "SELECT status, raw_note_path FROM research_questions WHERE research_id = ?",
            (research_id,),
        ).fetchone() == ("queued", None)


def test_an_unknown_research_id_writes_no_receipt(project):
    """Before any task loads there is nothing to fail closed *on*.

    ``task is None``, so the executor skips ``_fail_closed_discovery`` entirely;
    this pins that pre-task behavior, not the provenance carrier.
    """
    root, db_path = project
    register_default_handlers()
    task = Task(
        task_id="T-unknown",
        task_type="discovery",
        payload={"research_id": "RQ-does-not-exist", "backend": "live", "allow_network": False},
        run_id="RUN-unknown",
    )

    with pytest.raises(KeyError) as excinfo:
        dispatch(task, project_root=root, db_path=db_path)

    assert "RQ-does-not-exist" in str(excinfo.value)
    assert not list((root / "brain" / "00_Inbox" / "Failed_Runs").glob("*.md"))

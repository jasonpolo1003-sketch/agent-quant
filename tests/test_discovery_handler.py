import json
from pathlib import Path

import pytest

from quant_brain.db.init_db import connect, init_database
from quant_brain.discovery.live_discovery import SNAPSHOT_DIR
from quant_brain.harness.dispatcher import (
    ReentrantDispatch,
    Task,
    dispatch,
    unregister_handler,
)
from quant_brain.harness.handlers import (
    register_default_handlers,
    resolve_max_sources,
    run_discovery,
)
from quant_brain.harness.paths import PathViolation
from quant_brain.harness.registry import load_registry
from quant_brain.research.intake import add_research_question, update_research_status

SCOUT_DECLARATION = """---
name: research_scout
handles: [discovery]
model: qwen3:14b
enabled: true
allowed_read_paths:
  - AGENTS.md
  - agents/
  - brain/_system/
  - brain/00_Inbox/
  - brain/01_Sources/
  - brain/02_Strategy_Doors/
allowed_write_paths:
  - brain/00_Inbox/Raw_Research/
  - brain/00_Inbox/Source_Snapshots/
  - brain/00_Inbox/Failed_Runs/
output_contract: raw_research_note_v1
max_sources: 5
---

# Research Scout Agent

Find sources.
"""


CURATOR_DECLARATION = """---
name: knowledge_curator
handles: [curation]
model: null
enabled: true
allowed_read_paths:
  - brain/00_Inbox/
  - brain/01_Sources/
allowed_write_paths:
  - brain/00_Inbox/Curator_Reviews/
  - brain/01_Sources/
output_contract: curator_verdict_v1
---

# Knowledge Curator Agent

Promote useful sources.
"""


# A fetched page must clear the acquisition content floor to reach the model.
# These tests pin dispatch, capping and rollback behaviour, not thin-content
# rejection, so they use a realistic page body rather than a placeholder.
PAGE_BODY = " ".join(
    [
        "Wilder's relative strength index compares the average magnitude of recent",
        "gains to the average magnitude of recent losses over a fixed lookback of",
        "fourteen periods by default. The value is bounded between zero and one",
        "hundred, and readings below thirty are conventionally described as",
        "oversold. Exact evidence passage. The documentation treats these levels as",
        "conventions rather than tested decision rules, and does not establish an",
        "exit condition, a maximum holding period, or any cost assumption. A signal",
        "derived from a closing price is not observable until that close has",
        "occurred, so execution must happen no earlier than the following bar.",
        "Treating a close-derived signal as executable at the same close introduces",
        "lookahead bias and overstates measured performance on any instrument.",
    ]
    * 2
)


@pytest.fixture
def project(tmp_path):
    db_path = tmp_path / "brain.sqlite"
    init_database(db_path)
    agents = tmp_path / "agents"
    agents.mkdir()
    (agents / "research_scout.md").write_text(SCOUT_DECLARATION, encoding="utf-8")
    (agents / "knowledge_curator.md").write_text(CURATOR_DECLARATION, encoding="utf-8")
    (tmp_path / "brain" / "00_Inbox" / "Raw_Research").mkdir(parents=True)
    (tmp_path / "brain" / "00_Inbox" / "Source_Snapshots").mkdir(parents=True)
    (tmp_path / "brain" / "00_Inbox" / "Failed_Runs").mkdir(parents=True)
    (tmp_path / "brain" / "00_Inbox" / "Curator_Reviews").mkdir(parents=True)
    return tmp_path, db_path


@pytest.fixture(autouse=True)
def clean_handlers():
    yield
    unregister_handler("discovery", "research_scout")
    unregister_handler("curation", "knowledge_curator")


def stub_validated_qwen(monkeypatch):
    from types import SimpleNamespace

    def runner(_prompt, evidence, *, expected_research_id, **_kwargs):
        sources = [{
            "source_id": source["source_id"], "title": source["title"],
            "source_type": "docs", "url_or_citation": source["url_or_citation"],
            "main_claim": "The snapshot provides source material.",
            "evidence": source["snapshot_text"], "possible_strategy_rule": "",
            "risks": ["Requires curator review."], "confidence": "medium",
            "source_quality": source["source_quality"], "asset_classes": ["equity"],
            "data_required": ["daily close"], "data_access": "available-now",
            "mvp_testable": False,
        } for source in evidence]
        return SimpleNamespace(
            output={"research_id": expected_research_id, "status": "raw_saved",
                    "sources": sources, "open_questions": [],
                    "curator_recommendation": "needs_more_work"},
            model_used="qwen3:14b", repaired=False, escalated=False, durations=(0.1,),
        )

    monkeypatch.setattr("quant_brain.llm.qwen_call.qwen_call", runner)


def test_registry_lists_research_scout_for_discovery(project):
    root, _ = project
    registry = load_registry(root)

    assert "research_scout" in registry
    assert registry["research_scout"].handles_task("discovery")
    assert "brain/00_Inbox/Source_Snapshots/" in registry["research_scout"].allowed_write_paths
    assert "brain/00_Inbox/Snapshots/" not in registry["research_scout"].allowed_write_paths


def test_dry_run_discovery_routes_to_research_scout(project):
    root, db_path = project
    register_default_handlers()

    result = dispatch(
        Task(task_id="T-dry", task_type="discovery", payload={"backend": "seeded"}),
        project_root=root,
        db_path=db_path,
        dry_run=True,
    )

    assert result.status == "dry_run"
    assert result.agent == "research_scout"
    assert "brain/00_Inbox/Source_Snapshots/" in result.detail["allowed_write_paths"]
    assert result.detail["handler_registered"] is True


def test_dispatch_discovery_uses_scout_and_recommends_curation(project):
    root, db_path = project
    task_row = add_research_question(db_path, "Research ETF RSI mean reversion", "mean_reversion")
    register_default_handlers()

    result = dispatch(
        Task(
            task_id="T-discovery",
            task_type="discovery",
            payload={"research_id": task_row["research_id"], "backend": "seeded"},
        ),
        project_root=root,
        db_path=db_path,
    )

    assert result.agent == "research_scout"
    assert result.status == "completed"
    assert result.recommendation == "curation"
    assert result.detail["backend"] == "seeded"
    note = root / "brain" / "00_Inbox" / "Raw_Research" / f"{task_row['research_id']}.md"
    assert note.exists()
    assert "curator_recommendation" in note.read_text(encoding="utf-8")
    assert not (root / "brain" / "01_Sources").exists()


def test_scout_handler_does_not_run_curator(project, monkeypatch):
    root, db_path = project
    task_row = add_research_question(db_path, "Research ETF RSI mean reversion", "mean_reversion")
    register_default_handlers()

    def boom(*_args, **_kwargs):
        raise AssertionError("scout must not call the curator")

    monkeypatch.setattr("quant_brain.curation.executor.execute_curator_task", boom)

    result = dispatch(
        Task(
            task_id="T-no-curator",
            task_type="discovery",
            payload={"research_id": task_row["research_id"], "backend": "seeded"},
        ),
        project_root=root,
        db_path=db_path,
    )

    assert result.recommendation == "curation"
    assert result.detail["backend"] == "seeded"


def test_scout_cannot_reenter_curation_dispatch(project):
    root, db_path = project
    register_default_handlers()

    def reentrant(task, agent, context):
        dispatch(
            Task(task_id="T-inner-curation", task_type="curation"),
            project_root=root,
            db_path=db_path,
        )
        return run_discovery(task, agent, context)

    from quant_brain.harness.dispatcher import register_handler

    register_handler("discovery", "research_scout", reentrant)

    with pytest.raises(ReentrantDispatch):
        dispatch(
            Task(task_id="T-reenter", task_type="discovery", payload={"backend": "seeded"}),
            project_root=root,
            db_path=db_path,
        )


def test_scout_snapshot_path_is_enforced_and_curated_shelf_is_blocked(project):
    root, _db_path = project
    registry = load_registry(root)
    spec = registry["research_scout"]

    from quant_brain.harness.paths import resolve_write_target

    allowed = spec.allowed_write_paths
    resolved = resolve_write_target(root, f"{SNAPSHOT_DIR}/2026-09-07/abcd.md", allowed)
    assert resolved == (root / SNAPSHOT_DIR / "2026-09-07" / "abcd.md").resolve()

    with pytest.raises(PathViolation):
        resolve_write_target(root, "brain/01_Sources/web/stolen.md", allowed)


def test_dispatched_live_path_writes_snapshots_without_curation(project, monkeypatch):
    root, db_path = project
    task_row = add_research_question(db_path, "Research ETF RSI mean reversion", "mean_reversion")
    register_default_handlers()
    stub_validated_qwen(monkeypatch)

    def search_fn(question, method_family, *, limit):
        return [{"title": "RSI docs", "url": "https://example.com/rsi", "source_type": "docs"}]

    def fetch_fn(url):
        return {
            "url": url,
            "title": "RSI",
            "content": PAGE_BODY,
            "channel": "web",
            "backend": "fixture",
        }

    result = dispatch(
        Task(
            task_id="T-live",
            task_type="discovery",
            payload={
                "research_id": task_row["research_id"],
                "backend": "live",
                "allow_network": False,
                "search_fn": search_fn,
                "fetch_fn": fetch_fn,
            },
        ),
        project_root=root,
        db_path=db_path,
    )

    assert result.agent == "research_scout"
    assert result.recommendation == "curation"
    assert result.detail["backend"] == "live"
    assert result.detail["snapshots"]
    assert all(path.startswith(f"{SNAPSHOT_DIR}/") for path in result.detail["snapshots"])
    assert not (root / "brain" / "01_Sources").exists()
    reviews = root / "brain" / "00_Inbox" / "Curator_Reviews"
    assert not any(reviews.glob("*.md"))


def test_rejected_candidates_are_recorded_in_the_note_and_the_event_ledger(project, monkeypatch):
    """Honest rejection is reported two ways: prose for the curator, events for audit."""
    from quant_brain.ops.events import list_events

    root, db_path = project
    task_row = add_research_question(db_path, "Research ETF RSI mean reversion", "mean_reversion")
    register_default_handlers()
    stub_validated_qwen(monkeypatch)

    def search_fn(question, method_family, *, limit):
        return [
            {"title": "Paper", "url": "https://arxiv.org/abs/2301.04567", "source_type": "paper"},
            {"title": "Guaranteed returns", "url": "https://scam.example/go/x?ref=1"},
        ]

    def fetch_fn(url):
        return {"url": url, "title": "P", "content": PAGE_BODY, "channel": "web"}

    result = dispatch(
        Task(
            task_id="T-reject",
            task_type="discovery",
            run_id="RUN-reject",
            payload={
                "research_id": task_row["research_id"],
                "backend": "live",
                "allow_network": False,
                "search_fn": search_fn,
                "fetch_fn": fetch_fn,
            },
        ),
        project_root=root,
        db_path=db_path,
    )

    assert result.detail["rejected_count"] == 1

    note = (root / "brain" / "00_Inbox" / "Raw_Research" / f"{task_row['research_id']}.md").read_text(
        encoding="utf-8"
    )
    assert "## Rejected Candidates" in note
    assert "scam.example" in note
    # The ledger is prose, deliberately outside the validated JSON contract:
    # RawResearchPayload forbids extra fields.
    payload_block = json.loads(note.split("```json")[1].split("```")[0])
    assert "rejected" not in payload_block
    assert all("scam.example" not in s["url_or_citation"] for s in payload_block["sources"])

    events = list_events(db_path, run_id="RUN-reject")
    rejected_events = [e for e in events if e["event_type"] == "discovery_candidates_rejected"]
    assert len(rejected_events) == 1
    payload = rejected_events[0]["payload"]
    assert payload["rejected_count"] == 1
    assert payload["accepted_count"] == 1
    assert payload["rejected"][0]["signals"]
    assert "scam.example" in payload["rejected"][0]["url"]


def test_dispatched_live_uses_adapter_without_search_fn(project, monkeypatch):
    from quant_brain.discovery.agent_reach import AgentReachAdapter

    root, db_path = project
    task_row = add_research_question(db_path, "Research ETF RSI mean reversion", "mean_reversion")
    register_default_handlers()
    stub_validated_qwen(monkeypatch)
    fixtures = Path(__file__).parent / "fixtures"
    doctor = (fixtures / "agent_reach_doctor_healthy.json").read_text(encoding="utf-8")
    search = (fixtures / "agent_reach_search.json").read_text(encoding="utf-8")
    page = (fixtures / "jina_web_page.md").read_text(encoding="utf-8")

    def runner(argv, timeout=60):
        del timeout
        joined = " ".join(argv)
        if "doctor" in argv:
            return 0, doctor, ""
        if "exa.web_search_exa" in joined:
            return 0, search, ""
        if argv and argv[0] == "gh":
            return 0, "[]", ""
        return 1, "", f"unexpected argv: {argv}"

    adapter = AgentReachAdapter(runner=runner, fetch_impl=lambda _url: page, skip_exe_check=True)
    result = dispatch(
        Task(
            task_id="T-adapter",
            task_type="discovery",
            payload={
                "research_id": task_row["research_id"],
                "backend": "live",
                "allow_network": True,
                "adapter": adapter,
            },
        ),
        project_root=root,
        db_path=db_path,
    )

    assert result.recommendation == "curation"
    assert result.detail["backend"] == "live"
    assert result.detail["sources_count"] >= 1
    assert result.detail["snapshots"]
    assert not (root / "brain" / "01_Sources").exists()


def test_post_write_db_failure_leaves_no_orphan_completed_note(project, monkeypatch):
    """A failure AFTER the note is written must not leave a completed-looking note.

    The note on disk already says ``status: raw_saved`` at that point, so cleanup
    keyed on "still looks like a scaffold" silently spared it while the database
    row was rolled back to queued — a durable artifact with no DB pointer.
    """
    from quant_brain.ops.events import list_events

    root, db_path = project
    task_row = add_research_question(db_path, "Research ETF RSI mean reversion", "mean_reversion")
    register_default_handlers()
    stub_validated_qwen(monkeypatch)

    import quant_brain.research.executor as executor_mod

    def boom(*_args, **_kwargs):
        raise RuntimeError("db finalize failed")

    monkeypatch.setattr(executor_mod, "update_research_status", boom)

    note = root / "brain" / "00_Inbox" / "Raw_Research" / f"{task_row['research_id']}.md"
    with pytest.raises(RuntimeError, match="db finalize failed"):
        dispatch(
            Task(
                task_id="T-postwrite",
                task_type="discovery",
                payload={
                    "research_id": task_row["research_id"],
                    "backend": "live",
                    "allow_network": False,
                    "search_fn": lambda *_a, **_k: [
                        {"title": "RSI docs", "url": "https://example.com/rsi",
                         "source_type": "docs", "source_quality": "primary"}
                    ],
                    "fetch_fn": lambda url: {"url": url, "content": PAGE_BODY,
                                             "channel": "web", "backend": "fixture"},
                },
                run_id="RUN-postwrite",
            ),
            project_root=root,
            db_path=db_path,
        )

    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT status, raw_note_path FROM research_questions WHERE research_id = ?",
            (task_row["research_id"],),
        ).fetchone()
    assert row["status"] == "queued"
    assert row["raw_note_path"] is None
    assert not note.exists(), "a completed-looking raw note survived a post-write failure"
    assert (root / "brain" / "00_Inbox" / "Failed_Runs" / "RUN-postwrite.md").exists()
    types = [e["event_type"] for e in list_events(db_path, run_id="RUN-postwrite")]
    assert "discovery_failed" in types
    assert "failed_run_written" in types


def test_post_write_failure_restores_preexisting_note_bytes(project, monkeypatch):
    """If an existing note was being updated, restore it rather than delete it."""
    root, db_path = project
    task_row = add_research_question(db_path, "Research ETF RSI mean reversion", "mean_reversion")
    register_default_handlers()
    stub_validated_qwen(monkeypatch)

    note = root / "brain" / "00_Inbox" / "Raw_Research" / f"{task_row['research_id']}.md"
    note.parent.mkdir(parents=True, exist_ok=True)
    original = (
        f"---\nid: {task_row['research_id']}\ntype: raw_research\nstatus: researching\n---\n\n"
        "# Pre-existing note\n\nScout findings go here.\n"
    )
    note.write_text(original, encoding="utf-8")
    update_research_status(db_path, task_row["research_id"], "researching", raw_note_path=str(note))

    import quant_brain.research.executor as executor_mod

    def boom(*_args, **_kwargs):
        raise RuntimeError("db finalize failed")

    monkeypatch.setattr(executor_mod, "update_research_status", boom)

    with pytest.raises(RuntimeError, match="db finalize failed"):
        dispatch(
            Task(
                task_id="T-restore",
                task_type="discovery",
                payload={
                    "research_id": task_row["research_id"],
                    "backend": "live",
                    "allow_network": False,
                    "search_fn": lambda *_a, **_k: [
                        {"title": "RSI docs", "url": "https://example.com/rsi",
                         "source_type": "docs", "source_quality": "primary"}
                    ],
                    "fetch_fn": lambda url: {"url": url, "content": PAGE_BODY,
                                             "channel": "web", "backend": "fixture"},
                },
                run_id="RUN-restore",
            ),
            project_root=root,
            db_path=db_path,
        )

    assert note.exists(), "a pre-existing note must be restored, not deleted"
    assert note.read_text(encoding="utf-8") == original


def test_live_discovery_failure_is_retryable_and_leaves_no_orphan_note(project):
    from quant_brain.ops.events import list_events

    root, db_path = project
    task_row = add_research_question(db_path, "Research ETF RSI mean reversion", "mean_reversion")
    register_default_handlers()

    def search_fn(question, method_family, *, limit):
        raise RuntimeError("upstream search down")

    with pytest.raises(RuntimeError, match="upstream search down"):
        dispatch(
            Task(
                task_id="T-fail",
                task_type="discovery",
                payload={
                    "research_id": task_row["research_id"],
                    "backend": "live",
                    "allow_network": False,
                    "search_fn": search_fn,
                    "fetch_fn": lambda url: {"url": url, "content": PAGE_BODY},
                },
                run_id="RUN-fail1",
            ),
            project_root=root,
            db_path=db_path,
        )

    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT status, raw_note_path FROM research_questions WHERE research_id = ?",
            (task_row["research_id"],),
        ).fetchone()
    assert row["status"] == "queued"
    assert row["raw_note_path"] is None
    note = root / "brain" / "00_Inbox" / "Raw_Research" / f"{task_row['research_id']}.md"
    assert not note.exists()
    failed = root / "brain" / "00_Inbox" / "Failed_Runs" / "RUN-fail1.md"
    assert failed.exists()
    text = failed.read_text(encoding="utf-8")
    assert "retryable: true" in text
    assert task_row["research_id"] in text
    events = list_events(db_path, run_id="RUN-fail1")
    types = [event["event_type"] for event in events]
    assert "discovery_started" in types
    assert "discovery_failed" in types
    assert "failed_run_written" in types
    assert "handler_failed" in types
    assert "dispatch_failed" in types


def test_task_max_sources_narrows_but_never_widens(project, monkeypatch):
    root, db_path = project
    task_row = add_research_question(db_path, "Research ETF RSI mean reversion", "mean_reversion")
    register_default_handlers()
    stub_validated_qwen(monkeypatch)
    seen: list[int] = []

    def search_fn(question, method_family, *, limit):
        seen.append(limit)
        return [
            {"title": f"src-{idx}", "url": f"https://example.com/{idx}", "source_type": "docs"}
            for idx in range(limit)
        ]

    def fetch_fn(url):
        return {"url": url, "content": PAGE_BODY, "channel": "web", "backend": "fixture"}

    dispatch(
        Task(
            task_id="T-narrow",
            task_type="discovery",
            payload={
                "research_id": task_row["research_id"],
                "backend": "live",
                "allow_network": False,
                "search_fn": search_fn,
                "fetch_fn": fetch_fn,
                "max_sources": 2,
            },
        ),
        project_root=root,
        db_path=db_path,
    )
    assert seen == [2]

    task_row_wide = add_research_question(db_path, "Research look-ahead bias", "mean_reversion")
    dispatch(
        Task(
            task_id="T-wide",
            task_type="discovery",
            payload={
                "research_id": task_row_wide["research_id"],
                "backend": "live",
                "allow_network": False,
                "search_fn": search_fn,
                "fetch_fn": fetch_fn,
                "max_sources": 9,
            },
        ),
        project_root=root,
        db_path=db_path,
    )
    assert seen == [2, 5]


def test_production_live_scout_uses_validated_qwen_and_only_recommends_curation(
    project, monkeypatch
):
    from types import SimpleNamespace

    root, db_path = project
    task_row = add_research_question(db_path, "Research RSI evidence", "mean_reversion")
    register_default_handlers()
    seen = {}

    def runner(prompt, evidence, **kwargs):
        seen.update(prompt=prompt, evidence=evidence, kwargs=kwargs)
        source = evidence[0]
        output = {
            "research_id": task_row["research_id"], "status": "raw_saved",
            "sources": [{
                "source_id": source["source_id"], "title": source["title"],
                "source_type": "docs", "url_or_citation": source["url_or_citation"],
                "main_claim": "RSI documentation.", "evidence": "Exact evidence passage.",
                "possible_strategy_rule": "", "risks": ["No performance evidence."],
                "confidence": "medium", "source_quality": source["source_quality"],
                "asset_classes": ["equity"], "data_required": ["daily close"],
                "data_access": "available-now", "mvp_testable": False,
            }], "open_questions": ["What rule is supported?"],
            "curator_recommendation": "needs_more_work",
        }
        return SimpleNamespace(output=output, model_used="qwen3:14b", repaired=False,
                               escalated=False, durations=(0.1,))

    # Injected below the production task-payload boundary: the handler refuses
    # Qwen controls in a payload, so the seam is the module attribute itself.
    monkeypatch.setattr("quant_brain.llm.qwen_call.qwen_call", runner)

    result = dispatch(
        Task(task_id="T-qwen", task_type="discovery", run_id="RUN-qwen",
             payload={
                 "research_id": task_row["research_id"], "backend": "live",
                 "allow_network": False,
                 "search_fn": lambda *_args, **_kwargs: [{
                     "title": "RSI docs", "url": "https://example.com/rsi",
                     "source_type": "docs", "source_quality": "primary",
                 }],
                 "fetch_fn": lambda url: {"url": url, "content": PAGE_BODY,
                                          "channel": "web", "backend": "fixture"},
             }),
        project_root=root, db_path=db_path,
    )

    assert seen["evidence"][0]["source_id"] == "S1"
    assert "Exact evidence passage." in seen["evidence"][0]["snapshot_text"]
    assert result.recommendation == "curation"
    assert result.detail["model_used"] == "qwen3:14b"
    assert not (root / "brain" / "01_Sources").exists()


@pytest.mark.parametrize("bypass", [{"use_qwen": False}, {"qwen_runner": lambda: None}])
def test_production_live_scout_rejects_qwen_bypass_payload(project, bypass):
    root, db_path = project
    register_default_handlers()

    with pytest.raises(ValueError, match="Qwen controls are not accepted"):
        dispatch(
            Task(
                task_id="T-qwen-bypass",
                task_type="discovery",
                payload={"backend": "live", **bypass},
            ),
            project_root=root,
            db_path=db_path,
        )


def test_resolve_max_sources_validates_and_takes_the_minimum():
    assert resolve_max_sources(5, 2) == 2
    assert resolve_max_sources(5, 9) == 5
    assert resolve_max_sources(5, None) == 5
    assert resolve_max_sources(None, 3) == 3
    with pytest.raises(ValueError, match="positive integer"):
        resolve_max_sources(0, 2)
    with pytest.raises(ValueError, match="positive integer"):
        resolve_max_sources(5, -1)
    with pytest.raises(TypeError, match="positive integer"):
        resolve_max_sources(5, True)
    with pytest.raises(TypeError, match="positive integer"):
        resolve_max_sources(True, 2)

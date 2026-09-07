import pytest

from quant_brain.db.init_db import init_database
from quant_brain.discovery.live_discovery import SNAPSHOT_DIR, LiveDiscoveryBackend
from quant_brain.harness.dispatcher import (
    ReentrantDispatch,
    Task,
    dispatch,
    unregister_handler,
)
from quant_brain.harness.handlers import register_default_handlers, run_discovery
from quant_brain.harness.paths import PathViolation
from quant_brain.harness.registry import load_registry
from quant_brain.research.intake import add_research_question

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

    def boom(*args, **kwargs):
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
    root, db_path = project
    registry = load_registry(root)
    spec = registry["research_scout"]

    from quant_brain.harness.paths import resolve_write_target

    allowed = spec.allowed_write_paths
    resolved = resolve_write_target(root, f"{SNAPSHOT_DIR}/2026-09-07/abcd.md", allowed)
    assert resolved == (root / SNAPSHOT_DIR / "2026-09-07" / "abcd.md").resolve()

    with pytest.raises(PathViolation):
        resolve_write_target(root, "brain/01_Sources/web/stolen.md", allowed)


def test_dispatched_live_path_writes_snapshots_without_curation(project):
    root, db_path = project
    task_row = add_research_question(db_path, "Research ETF RSI mean reversion", "mean_reversion")
    register_default_handlers()

    def search_fn(question, method_family, *, limit):
        return [{"title": "RSI docs", "url": "https://example.com/rsi", "source_type": "docs"}]

    def fetch_fn(url):
        return {
            "url": url,
            "title": "RSI",
            "content": "Wilder RSI documentation body.",
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

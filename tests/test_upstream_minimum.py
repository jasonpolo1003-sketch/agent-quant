"""The Phase 6 upstream minimum: counted by distinct work, quarantined when thin.

Two properties matter here and neither is about arithmetic:

* the bar counts distinct upstream *works*, so one paper cited twice cannot
  satisfy it twice; and
* falling short is preserved as evidence rather than discarded or half-promoted.
"""

import json

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
from quant_brain.research.executor import (
    MIN_UPSTREAM_SOURCES,
    InsufficientUpstreamSources,
    distinct_upstream_keys,
)
from quant_brain.research.intake import add_research_question


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


def test_the_phase_6_minimum_is_three():
    assert MIN_UPSTREAM_SOURCES == 3


def test_the_probe_and_the_pipeline_share_one_constant():
    """They were two independent literals, and only the probe checked anything."""
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "scripts" / "gate_readiness.py"
    spec = importlib.util.spec_from_file_location("gate_readiness_probe", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.PHASE_6_MIN_SOURCES == MIN_UPSTREAM_SOURCES


# --- duplicate inflation ----------------------------------------------------


def test_one_arxiv_paper_in_many_forms_counts_once():
    """v1/bare and http/https are one work. len(sources) would say four."""
    sources = [
        {"url_or_citation": "http://arxiv.org/abs/1909.04327v1"},
        {"url_or_citation": "https://arxiv.org/abs/1909.04327"},
        {"url_or_citation": "https://www.arxiv.org/abs/1909.04327v3"},
        {"url_or_citation": "https://arxiv.org/abs/1909.04327"},
    ]

    assert len(sources) == 4
    assert distinct_upstream_keys(sources) == ["https://arxiv.org/abs/1909.04327"]


def test_pdf_and_abs_renderings_of_one_paper_count_once():
    """Found in review: three links to one paper satisfied a floor of three."""
    sources = [
        {"url_or_citation": "https://arxiv.org/pdf/2301.04567"},
        {"url_or_citation": "https://arxiv.org/abs/2301.04567"},
        {"url_or_citation": "https://arxiv.org/pdf/2301.04567v2.pdf"},
    ]

    assert distinct_upstream_keys(sources) == ["https://arxiv.org/abs/2301.04567"]
    assert len(distinct_upstream_keys(sources)) < MIN_UPSTREAM_SOURCES


def test_a_bare_version_marker_does_not_split_one_work():
    sources = [
        {"url_or_citation": "https://arxiv.org/abs/2301.04567"},
        {"url_or_citation": "https://arxiv.org/abs/2301.04567v"},
    ]

    assert len(distinct_upstream_keys(sources)) == 1


def test_trailing_slash_and_scheme_variants_count_once():
    sources = [
        {"url_or_citation": "https://example.com/rsi"},
        {"url_or_citation": "https://example.com/rsi/"},
    ]

    assert len(distinct_upstream_keys(sources)) == 1


def test_genuinely_distinct_works_each_count():
    sources = [
        {"url_or_citation": "https://arxiv.org/abs/1909.04327"},
        {"url_or_citation": "https://arxiv.org/abs/1411.5062"},
        {"url_or_citation": "https://example.com/rsi"},
    ]

    assert len(distinct_upstream_keys(sources)) == 3


def test_a_source_without_a_url_still_counts_once_by_citation():
    sources = [
        {"url_or_citation": "Wilder 1978, New Concepts in Technical Trading Systems"},
        {"url_or_citation": "wilder 1978, New Concepts in Technical Trading Systems"},
    ]

    assert len(distinct_upstream_keys(sources)) == 1


def test_sources_without_any_identity_are_not_counted():
    assert distinct_upstream_keys([{"url_or_citation": ""}, {}]) == []


# --- quarantine -------------------------------------------------------------


def _sparse_dispatch(project, monkeypatch, urls):
    root, db_path = project
    task_row = add_research_question(db_path, "Research ETF RSI mean reversion", "mean_reversion")
    register_default_handlers()
    stub_validated_qwen(monkeypatch)

    def search_fn(question, method_family, *, limit):
        del question, method_family, limit
        return [
            {"title": f"src-{i}", "url": url, "source_type": "docs", "source_quality": "primary"}
            for i, url in enumerate(urls)
        ]

    def fetch_fn(url):
        return {"url": url, "content": PAGE_BODY, "channel": "web", "backend": "fixture"}

    with pytest.raises(InsufficientUpstreamSources) as excinfo:
        dispatch(
            Task(
                task_id="T-sparse",
                task_type="discovery",
                payload={
                    "research_id": task_row["research_id"],
                    "backend": "live",
                    "allow_network": False,
                    "search_fn": search_fn,
                    "fetch_fn": fetch_fn,
                },
                run_id="RUN-sparse",
            ),
            project_root=root,
            db_path=db_path,
        )
    return root, task_row, excinfo.value


def test_a_sparse_result_writes_no_raw_note_and_no_curator_recommendation(project, monkeypatch):
    root, task_row, _ = _sparse_dispatch(
        project, monkeypatch, ["https://example.com/a", "https://example.com/b"]
    )

    note = root / "brain" / "00_Inbox" / "Raw_Research" / f"{task_row['research_id']}.md"
    text = note.read_text(encoding="utf-8") if note.exists() else ""
    assert "raw_saved" not in text
    assert "curator_recommendation" not in text
    assert not (root / "brain" / "01_Sources").exists()
    assert not list((root / "brain" / "00_Inbox" / "Curator_Reviews").iterdir())


def test_a_sparse_result_is_preserved_as_a_failed_run_receipt(project, monkeypatch):
    """Thin literature is a finding. It must be retained, with what was found."""
    root, _, error = _sparse_dispatch(
        project, monkeypatch, ["https://example.com/a", "https://example.com/b"]
    )

    receipts = list((root / "brain" / "00_Inbox" / "Failed_Runs").glob("*.md"))
    assert len(receipts) == 1
    body = receipts[0].read_text(encoding="utf-8")
    payload = json.loads(body.split("```json")[1].split("```")[0])

    assert payload["distinct_upstream_count"] == 2
    assert payload["required_upstream_count"] == MIN_UPSTREAM_SOURCES
    assert len(payload["accepted_candidates"]) == 2
    assert {c["url"] for c in payload["accepted_candidates"]} == {
        "https://example.com/a",
        "https://example.com/b",
    }
    assert all("tier" in c and "snapshot_path" in c for c in payload["accepted_candidates"])
    assert payload["follow_up"]
    assert "Not a refutation" in payload["follow_up"]
    assert error.detail["distinct_upstream_count"] == 2
    # Requirement: the query is recorded. Without it a reader cannot tell a thin
    # literature from a badly-formed search -- which is the whole point of the
    # receipt in the case where it matters most.
    assert payload["search_query_expression"]
    assert "all:" in payload["search_query_expression"]


def test_duplicates_cannot_buy_a_passing_run(project, monkeypatch):
    """Four citations of two works is still two works, and must still stop."""
    _, _, error = _sparse_dispatch(
        project,
        monkeypatch,
        [
            "http://arxiv.org/abs/1909.04327v1",
            "https://arxiv.org/abs/1909.04327",
            "https://example.com/rsi",
            "https://example.com/rsi/",
        ],
    )

    # Acquisition already collapses the trailing-slash pair, so three candidates
    # survive to the executor. The two arXiv forms are the ones only this layer
    # can collapse, and they are why the count is 2 rather than 3.
    assert error.detail["distinct_upstream_count"] == 2
    assert len(error.detail["accepted_candidates"]) == 3

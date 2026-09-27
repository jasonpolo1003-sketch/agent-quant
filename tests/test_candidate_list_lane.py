"""The pre-registered candidate-list lane (PROP-004).

A list may name the URLs a Scout run fetches, and where each was found. It may
not name anything else: not a tier, a title, a claim or evidence. Everything
after the candidate pool is formed is the unchanged live path -- classify,
rank, fetch, content floor, snapshot, Qwen, validators -- and the source
minimum counts what was actually acquired, never what was listed.

Not the ``seeded`` backend: that is the offline starter-catalog stub, which
never fetches and never runs the model.
"""

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest
from test_discovery_handler import (  # reuse the established fixtures
    CURATOR_DECLARATION,
    PAGE_BODY,
    SCOUT_DECLARATION,
    stub_validated_qwen,
)
from test_failed_run_provenance import _receipt_payload

from quant_brain.db.init_db import init_database
from quant_brain.discovery.acquisition import dedupe_candidates, rank_candidates
from quant_brain.discovery.candidate_list import (
    CANDIDATE_LIST_DIR,
    LANE,
    MAX_CANDIDATES,
    CandidateList,
    CandidateListError,
    load_candidate_list,
)
from quant_brain.discovery.live_discovery import LiveDiscoveryBackend, get_discovery_backend
from quant_brain.harness.dispatcher import Task, dispatch, unregister_handler
from quant_brain.harness.handlers import register_default_handlers
from quant_brain.llm.ollama_client import OllamaResponse
from quant_brain.llm.qwen_call import QwenValidationError
from quant_brain.ops.events import list_events
from quant_brain.research.executor import InsufficientUpstreamSources
from quant_brain.research.intake import add_research_question

THIN_BODY = "Too short to be evidence."

# Seven distinct works on hosts whose tiers the unmodified classifier decides.
URLS = (
    "https://chartschool.stockcharts.com/table-of-contents/trading-strategies/rsi-2",
    "https://articles.stockcharts.com/article/arthurhill-rsi-mean-reversion",
    "https://doi.org/10.15405/epms.2022.10.4",
    "https://www.naaim.org/wp-content/uploads/2014/04/pagonidis.pdf",
    "https://connorsresearch.com/does-mean-reversion-still-work",
    "https://thepatternsite.com/Double7sSetup.html",
    "https://www.quantstart.com/articles/backtesting-costs",
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
    (tmp_path / CANDIDATE_LIST_DIR).mkdir(parents=True)
    return tmp_path, db_path


@pytest.fixture(autouse=True)
def clean_handlers():
    yield
    unregister_handler("discovery", "research_scout")
    unregister_handler("curation", "knowledge_curator")


def _entry(url, **extra):
    return {
        "url": url,
        "found_via": "E1 dossier screening",
        "added_by": "test",
        "added_on": "2026-09-26",
        **extra,
    }


def write_list(root, research_id, urls, *, name=None, entries=None, **top):
    payload = {
        "research_id": research_id,
        "selection_rule": "every screened target with a located exit-rule span",
        "screening_reference": "brain/00_Inbox/Gate_D_Seed_Dossier_2026-09-26.md",
        "registered_by": "test",
        "registered_on": "2026-09-26",
        "candidates": entries if entries is not None else [_entry(url) for url in urls],
        **top,
    }
    relative = f"{CANDIDATE_LIST_DIR}/{name or research_id}.md"
    text = f"# Candidate list\n\n```json\n{json.dumps(payload, indent=2)}\n```\n"
    (root / relative).write_text(text, encoding="utf-8")
    return relative


def forbidden_search(*_args, **_kwargs):
    raise AssertionError("search must not run when a pre-registered list drives the run")


class Fetcher:
    """Counts fetch attempts; returns a thin body for the named URLs."""

    def __init__(self, thin=()):
        self.thin = set(thin)
        self.calls = []

    def __call__(self, url):
        self.calls.append(url)
        body = THIN_BODY if url in self.thin else PAGE_BODY
        return {"url": url, "content": body, "channel": "web", "backend": "fixture"}


def new_question(db_path):
    return add_research_question(
        db_path, "What exit rules pair with daily ETF RSI oversold entries?", "mean_reversion"
    )["research_id"]


def dispatch_list(project, list_path, fetcher, *, research_id, run_id="RUN-list", **payload):
    root, db_path = project
    register_default_handlers()
    task = Task(
        task_id=f"T-{run_id}",
        task_type="discovery",
        payload={
            "research_id": research_id,
            "backend": "live",
            "allow_network": False,
            "search_fn": forbidden_search,
            "fetch_fn": fetcher,
            "candidate_list": list_path,
            **payload,
        },
        run_id=run_id,
    )
    return dispatch(task, project_root=root, db_path=db_path)


def question_state(db_path, research_id):
    with sqlite3.connect(db_path) as conn:
        return conn.execute(
            "SELECT status, raw_note_path FROM research_questions WHERE research_id = ?",
            (research_id,),
        ).fetchone()


# --- loader -------------------------------------------------------------------


def test_a_valid_list_loads_with_the_sha256_of_its_bytes(project):
    root, _ = project
    relative = write_list(root, "RQ-1", URLS[:3])

    loaded = load_candidate_list(root, relative)

    assert loaded.research_id == "RQ-1"
    assert loaded.urls == URLS[:3]
    assert loaded.path == relative
    assert loaded.sha256 == hashlib.sha256((root / relative).read_bytes()).hexdigest()
    provenance = loaded.as_provenance()
    assert provenance["lane"] == LANE
    assert provenance["candidate_list_sha256"] == loaded.sha256
    assert provenance["candidate_count"] == 3


@pytest.mark.parametrize(
    "field", ["source_quality", "tier", "title", "main_claim", "evidence", "confidence"]
)
def test_a_candidate_cannot_carry_anything_but_url_and_provenance(project, field):
    root, _ = project
    entries = [_entry(URLS[0], **{field: "primary"}), _entry(URLS[1])]
    relative = write_list(root, "RQ-1", (), entries=entries)

    with pytest.raises(CandidateListError, match="Extra inputs are not permitted"):
        load_candidate_list(root, relative)


def test_an_unknown_top_level_field_is_rejected(project):
    root, _ = project
    relative = write_list(root, "RQ-1", URLS[:3], approved_by_curator=True)

    with pytest.raises(CandidateListError):
        load_candidate_list(root, relative)


@pytest.mark.parametrize("missing", ["found_via", "added_by", "added_on"])
def test_every_candidate_needs_its_discovery_provenance(project, missing):
    root, _ = project
    entry = _entry(URLS[0])
    entry[missing] = "  "
    relative = write_list(root, "RQ-1", (), entries=[entry])

    with pytest.raises(CandidateListError):
        load_candidate_list(root, relative)


@pytest.mark.parametrize("url", ["/relative/path", "stockcharts.com/rsi", "ftp://x.org/a", "https://"])
def test_candidate_urls_must_be_absolute_http(project, url):
    root, _ = project
    relative = write_list(root, "RQ-1", (url,))

    with pytest.raises(CandidateListError):
        load_candidate_list(root, relative)


def test_a_list_is_bounded(project):
    root, _ = project
    too_many = [f"https://example{i}.org/paper" for i in range(MAX_CANDIDATES + 1)]
    with pytest.raises(CandidateListError):
        load_candidate_list(root, write_list(root, "RQ-1", too_many))
    with pytest.raises(CandidateListError):
        load_candidate_list(root, write_list(root, "RQ-1", (), name="empty"))


def test_one_work_listed_twice_is_rejected_before_anything_is_fetched(project):
    """Three URLs, two works: the list itself must not inflate the minimum."""
    root, _ = project
    relative = write_list(
        root,
        "RQ-1",
        (
            "https://doi.org/10.15405/epms.2022.10.4",
            "https://www.europeanproceedings.com/article/10.15405/epms.2022.10.4",
            URLS[0],
        ),
    )

    with pytest.raises(CandidateListError, match="one upstream work twice"):
        load_candidate_list(root, relative)


def test_a_list_must_live_in_the_registration_directory(project):
    root, _ = project
    write_list(root, "RQ-1", URLS[:3])
    outside = root / "brain" / "00_Inbox" / "Raw_Research" / "RQ-1.md"
    outside.write_text((root / CANDIDATE_LIST_DIR / "RQ-1.md").read_text(), encoding="utf-8")

    with pytest.raises(CandidateListError, match="must live under"):
        load_candidate_list(root, "brain/00_Inbox/Raw_Research/RQ-1.md")
    with pytest.raises(CandidateListError, match="must live under"):
        load_candidate_list(root, f"{CANDIDATE_LIST_DIR}/../Raw_Research/RQ-1.md")


def test_a_list_must_be_markdown_with_exactly_one_json_block(project):
    root, _ = project
    (root / CANDIDATE_LIST_DIR / "RQ-1.json").write_text("{}", encoding="utf-8")
    with pytest.raises(CandidateListError, match=r"\.md"):
        load_candidate_list(root, f"{CANDIDATE_LIST_DIR}/RQ-1.json")

    relative = write_list(root, "RQ-1", URLS[:3])
    path = root / relative
    path.write_text(path.read_text() + "\n```json\n{}\n```\n", encoding="utf-8")
    with pytest.raises(CandidateListError, match="exactly one"):
        load_candidate_list(root, relative)


# --- the list drives the unchanged live path ----------------------------------


def test_a_list_run_never_searches_and_writes_a_validated_note(project, monkeypatch):
    root, db_path = project
    stub_validated_qwen(monkeypatch)
    research_id = new_question(db_path)
    relative = write_list(root, research_id, URLS[:3])
    fetcher = Fetcher()

    result = dispatch_list(project, relative, fetcher, research_id=research_id)

    assert result.status == "completed"
    assert sorted(fetcher.calls) == sorted(URLS[:3])
    lane = result.detail["discovery_lane"]
    assert lane["lane"] == LANE
    assert lane["candidate_list_sha256"] == load_candidate_list(root, relative).sha256

    status, note_path = question_state(db_path, research_id)
    assert status == "raw_saved"
    note = Path(note_path).read_text(encoding="utf-8")
    assert "## Discovery Lane" in note
    assert lane["candidate_list_sha256"] in note
    # Prose outside the validated JSON block, like the rejection ledger: it sits
    # before the payload's fenced block, and the payload is unchanged by it.
    lane_at = note.index("## Discovery Lane")
    payload_at = note.index("```json", lane_at)
    payload = json.loads(note[payload_at:].split("```json")[1].split("```")[0])
    assert "discovery_lane" not in json.dumps(payload)

    events = {e["event_type"]: e for e in list_events(db_path, run_id="RUN-list")}
    for event_type in ("discovery_started", "discovery_completed"):
        recorded = events[event_type]["payload"]["discovery_lane"]
        assert recorded["candidate_list_sha256"] == lane["candidate_list_sha256"]


def test_tiers_come_from_the_classifier_not_from_the_list(project):
    root, _ = project
    backend = LiveDiscoveryBackend(
        fetch_fn=Fetcher(),
        candidate_list=load_candidate_list(root, write_list(root, "RQ-1", URLS[:4])),
    )

    result = backend.discover("q", "mean_reversion", limit=5, project_root=root)

    tiers = {source["url_or_citation"]: source["source_quality"] for source in result.sources}
    assert tiers[URLS[0]] == "practitioner"
    assert tiers[URLS[1]] == "practitioner"
    assert tiers[URLS[2]] == "primary"
    assert tiers[URLS[3]] == "discovery-only"


def test_entry_fields_never_reach_the_source_record(project):
    """Defence in depth: even a list object built past the loader carries only URLs."""
    root, _ = project
    smuggled = CandidateList(
        path=f"{CANDIDATE_LIST_DIR}/x.md",
        sha256="0" * 64,
        research_id="RQ-1",
        selection_rule="test",
        entries=(
            {
                "url": URLS[3],
                "main_claim": "INJECTED CLAIM",
                "evidence": "INJECTED EVIDENCE",
                "source_quality": "primary",
                "confidence": "high",
                "mvp_testable": True,
            },
        ),
    )
    backend = LiveDiscoveryBackend(fetch_fn=Fetcher(), candidate_list=smuggled)

    (source,) = backend.discover("q", None, limit=5, project_root=root).sources

    assert source["source_quality"] == "discovery-only"
    assert "INJECTED" not in json.dumps(source)
    assert source["confidence"] == "low"
    assert source["mvp_testable"] is False


def test_the_search_lane_is_not_consulted_even_when_it_is_available(project):
    root, _ = project

    def search(*_args, **_kwargs):
        raise AssertionError("off-topic search hits must not join a pre-registered pool")

    backend = LiveDiscoveryBackend(
        search_fn=search,
        fetch_fn=Fetcher(),
        candidate_list=load_candidate_list(root, write_list(root, "RQ-1", URLS[:3])),
    )

    result = backend.discover("q", None, limit=5, project_root=root)

    assert sorted(s["url_or_citation"] for s in result.sources) == sorted(URLS[:3])
    assert backend.last_query_expression is None


# --- budget: exactly as the loop behaves --------------------------------------


def _backend(root, urls, fetcher):
    return LiveDiscoveryBackend(
        fetch_fn=fetcher,
        candidate_list=load_candidate_list(root, write_list(root, "RQ-1", urls)),
    )


def test_seven_good_candidates_cost_five_fetches_for_five_sources(project):
    root, _ = project
    fetcher = Fetcher()

    result = _backend(root, URLS, fetcher).discover("q", None, limit=5, project_root=root)

    assert len(fetcher.calls) == 5
    assert len(result.sources) == 5
    over_budget = [r for r in result.rejected if "over-budget" in r["signals"]]
    assert len(over_budget) == 2


def test_thin_pages_are_backfilled_so_attempts_can_exceed_the_source_cap(project):
    """The cap is five accepted sources, not five fetch attempts."""
    root, _ = project
    # Thin pages among the first five by rank, so backfill has work to do.
    accepted, _ = rank_candidates(
        dedupe_candidates([{"url": u, "source_type": "web"} for u in URLS]), "q", limit=5
    )
    fetcher = Fetcher(thin=[c.url for c in accepted[:2]])
    backend = _backend(root, URLS, fetcher)

    result = backend.discover("q", None, limit=5, project_root=root)

    assert len(fetcher.calls) == 7
    assert len(result.sources) == 5


def test_attempts_never_exceed_the_list_length(project):
    root, _ = project
    urls = [f"https://example{i}.org/paper" for i in range(MAX_CANDIDATES)]
    fetcher = Fetcher(thin=urls)

    with pytest.raises(Exception, match="every fetched page was rejected"):
        _backend(root, urls, fetcher).discover("q", None, limit=5, project_root=root)

    assert len(fetcher.calls) == MAX_CANDIDATES
    assert not list((root / "brain" / "00_Inbox" / "Source_Snapshots").rglob("*.md"))


def test_a_listed_url_the_classifier_rejects_is_never_fetched(project):
    root, _ = project
    affiliate = "https://robotwealth.com/go/special-offer"
    fetcher = Fetcher()

    result = _backend(root, (*URLS[:3], affiliate), fetcher).discover(
        "q", None, limit=5, project_root=root
    )

    assert affiliate not in fetcher.calls
    assert any(r["url"] == affiliate and r["tier"] == "reject" for r in result.rejected)


# --- the minimum counts what was acquired, not what was listed -----------------


def test_listed_candidates_that_fail_the_content_floor_do_not_count(project, monkeypatch):
    root, db_path = project
    stub_validated_qwen(monkeypatch)
    research_id = new_question(db_path)
    relative = write_list(root, research_id, URLS[:4])
    fetcher = Fetcher(thin=URLS[:2])

    with pytest.raises(InsufficientUpstreamSources) as caught:
        dispatch_list(project, relative, fetcher, research_id=research_id, run_id="RUN-thin")

    assert caught.value.detail["distinct_upstream_count"] == 2
    sha = load_candidate_list(root, relative).sha256
    assert caught.value.detail["discovery_lane"]["candidate_list_sha256"] == sha
    assert question_state(db_path, research_id) == ("queued", None)
    assert not list((root / "brain" / "00_Inbox" / "Raw_Research").glob(f"{research_id}*"))
    receipt = _receipt_payload(root)
    assert receipt["discovery_lane"]["candidate_list_sha256"] == sha
    assert receipt["distinct_upstream_count"] == 2


def test_a_doi_alias_found_by_search_cannot_fill_two_slots(project, monkeypatch):
    """The same inflation through the search lane: counted once, run quarantined."""
    root, db_path = project
    stub_validated_qwen(monkeypatch)
    research_id = new_question(db_path)
    register_default_handlers()

    def search(_question, _family, *, limit):
        del limit
        return [
            {"url": "https://doi.org/10.15405/epms.2022.10.4"},
            {"url": "https://www.europeanproceedings.com/article/10.15405/epms.2022.10.4"},
            {"url": URLS[0]},
        ]

    task = Task(
        task_id="T-alias",
        task_type="discovery",
        payload={
            "research_id": research_id,
            "backend": "live",
            "allow_network": False,
            "search_fn": search,
            "fetch_fn": Fetcher(),
        },
        run_id="RUN-alias",
    )
    with pytest.raises(InsufficientUpstreamSources) as caught:
        dispatch(task, project_root=root, db_path=db_path)

    assert len(caught.value.detail["accepted_candidates"]) == 3
    assert caught.value.detail["distinct_upstream_count"] == 2
    assert question_state(db_path, research_id) == ("queued", None)


# --- failure receipts name the list ------------------------------------------


def test_a_failure_inside_discovery_still_names_the_list(project):
    root, db_path = project
    research_id = new_question(db_path)
    relative = write_list(root, research_id, URLS[:3])

    with pytest.raises(Exception, match="every fetched page was rejected"):
        dispatch_list(
            project, relative, Fetcher(thin=URLS[:3]), research_id=research_id, run_id="RUN-early"
        )

    receipt = _receipt_payload(root)
    assert receipt["stage"] == "discover"
    assert receipt["discovery_lane"]["candidate_list_sha256"] == (
        load_candidate_list(root, relative).sha256
    )
    # The list is an input, not a finding: nothing fetched, nothing claimed.
    for key in ("accepted_candidates", "snapshot_paths", "distinct_upstream_count"):
        assert key not in receipt, key
    assert question_state(db_path, research_id) == ("queued", None)


# --- the real ladder and validators run on list-driven snapshots --------------


class GroundingClient:
    """Stands in for Ollama only; qwen_call's ladder and validators are real."""

    def __init__(self, evidence, *, grounded):
        self.evidence = evidence
        self.grounded = grounded
        self.models = []

    def generate(self, prompt, model, **_kwargs):
        self.models.append(model)
        quote = "Exact evidence passage." if self.grounded else "RSI(2) exits above 70 on SPY."
        payload = {
            "research_id": self.research_id,
            "status": "raw_saved",
            "sources": [
                {
                    "source_id": item["source_id"],
                    "title": item["title"],
                    "source_type": "web",
                    "url_or_citation": item["url_or_citation"],
                    "main_claim": quote,
                    "evidence": quote,
                    "possible_strategy_rule": "",
                    "risks": ["Requires curator review."],
                    "confidence": "low",
                    "source_quality": item["source_quality"],
                    "asset_classes": ["equity"],
                    "data_required": ["daily close"],
                    "data_access": "available-now",
                    "mvp_testable": False,
                }
                for item in self.evidence
            ],
            "open_questions": [],
            "curator_recommendation": "needs_more_work",
        }
        text = json.dumps(payload)
        digest = hashlib.sha256(prompt.encode()).hexdigest()
        return OllamaResponse(text, model, 0.01, digest, hashlib.sha256(text.encode()).hexdigest())


def use_real_ladder(monkeypatch, *, grounded):
    import quant_brain.llm.qwen_call as module

    real = module.qwen_call
    seen = {"clients": [], "evidence": [], "calls": []}

    def ladder(prompt, evidence, *, expected_research_id, **kwargs):
        client = GroundingClient(evidence, grounded=grounded)
        client.research_id = expected_research_id
        # One extraction call per source: record every call, not just the last.
        seen["clients"].append(client)
        seen["evidence"].extend(evidence)
        seen["calls"].append(evidence)
        return real(prompt, evidence, expected_research_id=expected_research_id,
                    client=client, **kwargs)

    monkeypatch.setattr(module, "qwen_call", ladder)
    return seen


def test_grounded_extraction_of_list_sources_passes_the_real_validators(project, monkeypatch):
    root, db_path = project
    seen = use_real_ladder(monkeypatch, grounded=True)
    research_id = new_question(db_path)
    relative = write_list(root, research_id, URLS[:3])

    result = dispatch_list(project, relative, Fetcher(), research_id=research_id)

    assert result.status == "completed"
    assert [client.models for client in seen["clients"]] == [["qwen3:14b"]] * 3
    # Exactly one source per extraction call.
    assert [len(call) for call in seen["calls"]] == [1, 1, 1]
    # The model was shown the persisted snapshots, one per acquired source.
    for item in seen["evidence"]:
        assert "Exact evidence passage." in item["snapshot_text"]
        assert item["snapshot_text"].startswith("---\nurl: ")
    assert sorted(item["url_or_citation"] for item in seen["evidence"]) == sorted(URLS[:3])


def test_ungrounded_extraction_of_list_sources_fails_closed(project, monkeypatch):
    root, db_path = project
    seen = use_real_ladder(monkeypatch, grounded=False)
    research_id = new_question(db_path)
    relative = write_list(root, research_id, URLS[:3])

    with pytest.raises(QwenValidationError, match="failed closed"):
        dispatch_list(project, relative, Fetcher(), research_id=research_id, run_id="RUN-bad")

    # The first source exhausts its ladder and the run stops: no later source is tried.
    assert [client.models for client in seen["clients"]] == [
        ["qwen3:14b", "qwen3:14b", "qwen3.8:27b"]
    ]
    receipt = _receipt_payload(root)
    assert receipt["stage"] == "qwen_extract"
    assert receipt["discovery_lane"]["candidate_list_sha256"] == (
        load_candidate_list(root, relative).sha256
    )
    assert sorted(c["url"] for c in receipt["accepted_candidates"]) == sorted(URLS[:3])
    assert all(c["snapshot_sha256"] for c in receipt["accepted_candidates"])
    assert question_state(db_path, research_id) == ("queued", None)


# --- guards --------------------------------------------------------------------


def test_a_list_registered_for_another_question_is_refused_before_any_fetch(project):
    root, db_path = project
    research_id = new_question(db_path)
    relative = write_list(root, "RQ-someone-else", URLS[:3])
    fetcher = Fetcher()

    with pytest.raises(ValueError, match="registered for RQ-someone-else"):
        dispatch_list(project, relative, fetcher, research_id=research_id)

    assert fetcher.calls == []
    assert question_state(db_path, research_id)[0] == "queued"


def test_a_list_requires_the_live_backend(project):
    root, db_path = project
    research_id = new_question(db_path)
    relative = write_list(root, research_id, URLS[:3])

    with pytest.raises(ValueError, match="requires the live backend"):
        dispatch_list(project, relative, Fetcher(), research_id=research_id, backend="seeded")
    with pytest.raises(ValueError, match="requires the live backend"):
        get_discovery_backend("seeded", candidate_list=load_candidate_list(root, relative))


def test_a_list_requires_an_explicit_research_id(project):
    root, _ = project
    relative = write_list(root, "RQ-1", URLS[:3])

    with pytest.raises(ValueError, match="explicit research_id"):
        dispatch_list(project, relative, Fetcher(), research_id=None)

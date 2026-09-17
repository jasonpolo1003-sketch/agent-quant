"""Agent Reach adapter: health, routing, bounded search, fetch, fail-closed."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from quant_brain.discovery.agent_reach import (
    AgentReachAdapter,
    AgentReachError,
    AgentReachUnavailable,
    is_channel_usable,
    parse_channel_health,
    plan_queries,
)
from quant_brain.discovery.live_discovery import LiveDiscoveryBackend, LiveDiscoveryError

FIXTURES = Path(__file__).parent / "fixtures"
DOCTOR_JSON = (FIXTURES / "agent_reach_doctor.json").read_text(encoding="utf-8")
SEARCH_JSON = (FIXTURES / "agent_reach_search.json").read_text(encoding="utf-8")
PAGE_MD = (FIXTURES / "jina_web_page.md").read_text(encoding="utf-8")


def _fake_runner(argv: list[str], timeout: int = 60) -> tuple[int, str, str]:
    del timeout
    joined = " ".join(argv)
    if "doctor" in argv:
        return 0, DOCTOR_JSON, ""
    if "mcporter" in argv and "exa.web_search_exa" in joined:
        return 0, SEARCH_JSON, ""
    if argv and argv[0] == "gh":
        payload = json.dumps(
            [
                {
                    "url": "https://github.com/example/repo",
                    "name": "repo",
                    "description": "example",
                }
            ]
        )
        return 0, payload, ""
    return 1, "", f"unexpected argv: {argv}"


def test_plan_queries_is_bounded_and_deterministic() -> None:
    first = plan_queries("What published papers cover overnight reversal?", "equities", max_queries=3)
    second = plan_queries("What published papers cover overnight reversal?", "equities", max_queries=3)
    assert first == second
    assert 1 <= len(first) <= 3
    assert first[0] == "What published papers cover overnight reversal?"
    assert "equities" in first[1]


def test_plan_queries_rejects_empty_question() -> None:
    with pytest.raises(AgentReachError, match="empty"):
        plan_queries("   ", None)


def test_health_uses_doctor_json_not_config_yaml() -> None:
    calls: list[list[str]] = []

    def runner(argv: list[str], timeout: int = 60) -> tuple[int, str, str]:
        del timeout
        calls.append(argv)
        return 0, DOCTOR_JSON, ""

    adapter = AgentReachAdapter(runner=runner, skip_exe_check=True)
    health = adapter.check_health()
    assert "search" in health
    assert health["search"].status == "ok"
    assert health["web"].active_backend == "jina"
    assert "doctor" in calls[0]
    assert "--json" in calls[0]
    assert not any("config.yaml" in part for argv in calls for part in argv)
    assert not any(cmd in calls[0] for cmd in ("install", "uninstall", "configure"))
    assert is_channel_usable(health, "search") is True
    assert is_channel_usable(health, "reddit") is False


def test_parse_channel_health_accepts_wrapped_and_flat_doctor_json() -> None:
    flat = parse_channel_health(DOCTOR_JSON)
    wrapped = parse_channel_health({"ok": True, "channels": json.loads(DOCTOR_JSON)})
    assert set(flat) == set(wrapped)
    assert flat["github"].status == "warn"


def test_health_fails_closed_when_doctor_unhealthy() -> None:
    def runner(argv: list[str], timeout: int = 60) -> tuple[int, str, str]:
        del argv, timeout
        return 0, json.dumps({"ok": False, "issues": ["venv missing"]}), ""

    adapter = AgentReachAdapter(runner=runner, skip_exe_check=True)
    with pytest.raises(AgentReachUnavailable, match="unhealthy"):
        adapter.check_health()


def test_forbidden_subcommands_never_run() -> None:
    adapter = AgentReachAdapter(runner=_fake_runner, skip_exe_check=True)
    for cmd in ("install", "uninstall", "configure"):
        with pytest.raises(AgentReachError, match="refusing Agent Reach subcommand"):
            adapter._run(["agent-reach", cmd])


def test_search_exa_then_github_fallback() -> None:
    adapter = AgentReachAdapter(runner=_fake_runner, skip_exe_check=True)
    hits = adapter.search_for_question("overnight reversal equities", None, limit=3)
    urls = [hit["url"] for hit in hits]
    assert "https://www.investopedia.com/terms/r/rsi.asp" in urls
    assert any(url.startswith("https://github.com/") for url in urls)


def test_search_github_when_exa_empty() -> None:
    def runner(argv: list[str], timeout: int = 60) -> tuple[int, str, str]:
        del timeout
        if "doctor" in argv:
            return 0, DOCTOR_JSON, ""
        if "exa.web_search_exa" in " ".join(argv):
            return 0, json.dumps({"results": []}), ""
        if argv and argv[0] == "gh":
            return 0, json.dumps(
                [{"url": "https://github.com/quant/paper", "name": "paper", "description": "code"}]
            ), ""
        return 1, "", "unexpected"

    adapter = AgentReachAdapter(runner=runner, skip_exe_check=True)
    hits = adapter.search_for_question("foo", None, limit=2)
    assert hits[0]["url"] == "https://github.com/quant/paper"
    assert hits[0]["source_type"] == "repo"


def test_search_fails_closed_when_no_usable_channel() -> None:
    def runner(argv: list[str], timeout: int = 60) -> tuple[int, str, str]:
        del argv, timeout
        return 0, json.dumps(
            {
                "search": {"status": "error", "active_backend": None, "message": "down"},
                "github": {"status": "error", "active_backend": None, "message": "down"},
                "web": {"status": "ok", "active_backend": "jina", "message": "ok"},
            }
        ), ""

    adapter = AgentReachAdapter(runner=runner, skip_exe_check=True)
    with pytest.raises(AgentReachError, match="no usable Agent Reach search channel"):
        adapter.search_for_question("overnight reversal", None, limit=2)


def test_production_live_backend_discovers_without_search_fn_injection(tmp_path: Path) -> None:
    """CLI production path: adapter + fetch_impl, no Python search_fn."""
    adapter = AgentReachAdapter(
        runner=_fake_runner,
        fetch_impl=lambda _url: PAGE_MD,
        skip_exe_check=True,
    )
    backend = LiveDiscoveryBackend(allow_network=True, adapter=adapter)
    result = backend.discover(
        "What published papers cover overnight reversal?",
        "mean_reversion",
        limit=2,
        project_root=tmp_path,
    )
    assert result.backend == "live"
    assert len(result.sources) == 2
    assert len(result.snapshots) == 2
    assert (tmp_path / "brain" / "00_Inbox" / "Source_Snapshots").is_dir()
    assert any((tmp_path / "brain" / "00_Inbox" / "Source_Snapshots").rglob("*.md"))
    assert all("url_or_citation" in source for source in result.sources)


def test_live_backend_without_injection_requires_network_flag() -> None:
    with pytest.raises(LiveDiscoveryError, match="network is disabled"):
        LiveDiscoveryBackend(allow_network=False).discover("ETF RSI", "mean_reversion")


def test_a_research_question_containing_the_word_install_is_not_refused() -> None:
    """The guard protects the subcommand slot, not every token in the argv."""
    from quant_brain.discovery.agent_reach import plan_queries

    adapter = AgentReachAdapter(runner=_fake_runner, skip_exe_check=True)
    query = plan_queries("how do I install and configure a backtesting library", None)[0]

    hits = adapter.search_exa(query, limit=2)
    assert hits


def test_agent_reach_install_subcommand_is_still_refused() -> None:
    adapter = AgentReachAdapter(exe="agent-reach", runner=_fake_runner, skip_exe_check=True)
    for forbidden in ("install", "uninstall", "configure"):
        with pytest.raises(AgentReachError, match=forbidden):
            adapter._run(["agent-reach", forbidden, "web"])


def test_hits_differing_only_by_a_trailing_slash_are_deduped() -> None:
    from quant_brain.discovery.agent_reach import _dedupe_hits

    hits = [
        {"title": "A", "url": "https://example.com/terms/rsi.asp"},
        {"title": "B", "url": "https://example.com/terms/rsi.asp/"},
        {"title": "C", "url": "https://EXAMPLE.com/terms/rsi.asp"},
    ]
    assert len(_dedupe_hits(hits)) == 1


def test_an_arxiv_pdf_link_is_rewritten_to_its_abstract_page() -> None:
    from quant_brain.discovery.agent_reach import prefer_arxiv_abstract

    assert prefer_arxiv_abstract("https://arxiv.org/pdf/2301.04567") == (
        "https://arxiv.org/abs/2301.04567"
    )
    assert prefer_arxiv_abstract("https://arxiv.org/pdf/2301.04567v2.pdf") == (
        "https://arxiv.org/abs/2301.04567"
    )
    # Non-arXiv URLs and existing abstract links pass through untouched.
    assert prefer_arxiv_abstract("https://arxiv.org/abs/2301.04567") == (
        "https://arxiv.org/abs/2301.04567"
    )
    assert prefer_arxiv_abstract("https://example.com/pdf/x") == "https://example.com/pdf/x"


def test_search_returns_a_candidate_pool_larger_than_the_source_cap() -> None:
    """Truncating to the cap in the adapter would make downstream ranking a no-op."""
    from quant_brain.discovery.agent_reach import CANDIDATE_POOL_FACTOR

    assert CANDIDATE_POOL_FACTOR > 1

    many = json.dumps(
        {"results": [{"title": f"h{i}", "url": f"https://e{i}.example/p"} for i in range(12)]}
    )

    def runner(argv: list[str], timeout: int = 60) -> tuple[int, str, str]:
        del timeout
        if "doctor" in argv:
            return 0, DOCTOR_JSON, ""
        return 0, many, ""

    adapter = AgentReachAdapter(runner=runner, skip_exe_check=True)
    hits = adapter.search_for_question("exit rules", "mean_reversion", limit=2)

    assert len(hits) > 2
    assert len(hits) <= 2 * CANDIDATE_POOL_FACTOR


def test_only_operational_lanes_are_dispatched() -> None:
    """Declared lanes state what is real; login-backed channels appear nowhere."""
    from quant_brain.discovery.agent_reach import (
        LOGIN_BACKED_CHANNELS,
        SEARCH_LANES,
        operational_lanes,
    )

    assert {lane.name for lane in operational_lanes()} == {"exa", "github"}
    assert {lane.status for lane in SEARCH_LANES} <= {
        "operational",
        "fixture-only",
        "deferred",
    }
    assert all(lane.channel not in LOGIN_BACKED_CHANNELS for lane in SEARCH_LANES)


def test_fetch_web_passes_its_timeout_to_a_fetcher_that_accepts_one() -> None:
    seen: dict[str, object] = {}

    def fetch_impl(url, *, timeout=None):
        seen["timeout"] = timeout
        return {"url": url, "content": "body", "channel": "web"}

    AgentReachAdapter(
        runner=_fake_runner, fetch_impl=fetch_impl, timeout=45, skip_exe_check=True
    ).fetch_web("https://example.com/x")

    assert seen["timeout"] == 45


def test_fetch_web_still_supports_a_fetcher_that_takes_only_a_url() -> None:
    result = AgentReachAdapter(
        runner=_fake_runner, fetch_impl=lambda url: PAGE_MD, skip_exe_check=True
    ).fetch_web("https://example.com/x")

    assert result["content"] == PAGE_MD

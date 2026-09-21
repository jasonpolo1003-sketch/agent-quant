"""Agent Reach adapter: health, routing, bounded search, fetch, fail-closed."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from quant_brain.discovery.agent_reach import (
    ENABLED_CHANNELS,
    SEARCH_CHANNELS,
    AgentReachAdapter,
    AgentReachError,
    AgentReachUnavailable,
    default_runner,
    is_channel_usable,
    operational_lanes,
    parse_channel_health,
    plan_queries,
)
from quant_brain.discovery.live_discovery import LiveDiscoveryBackend, LiveDiscoveryError

FIXTURES = Path(__file__).parent / "fixtures"
# Synthetic: exa_search forced ok so dispatch tests exercise dispatch.
DOCTOR_JSON = (FIXTURES / "agent_reach_doctor_healthy.json").read_text(encoding="utf-8")
# Verbatim capture: exa_search really is "off", names are literal UTF-8.
DOCTOR_LIVE_JSON = (FIXTURES / "agent_reach_doctor_live.json").read_text(encoding="utf-8")
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
    first = plan_queries(
        "What published papers cover overnight reversal?", "equities", max_queries=3
    )
    second = plan_queries(
        "What published papers cover overnight reversal?", "equities", max_queries=3
    )
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
    assert "exa_search" in health
    assert health["exa_search"].status == "ok"
    # "Jina Reader" is what the real doctor reports; the old invented fixture
    # said "jina", which is the kind of drift these fixtures now prevent.
    assert health["web"].active_backend == "Jina Reader"
    assert "doctor" in calls[0]
    assert "--json" in calls[0]
    assert not any("config.yaml" in part for argv in calls for part in argv)
    assert not any(cmd in calls[0] for cmd in ("install", "uninstall", "configure"))
    assert is_channel_usable(health, "exa_search") is True
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
            return (
                0,
                json.dumps(
                    [
                        {
                            "url": "https://github.com/quant/paper",
                            "name": "paper",
                            "description": "code",
                        }
                    ]
                ),
                "",
            )
        return 1, "", "unexpected"

    adapter = AgentReachAdapter(runner=runner, skip_exe_check=True)
    hits = adapter.search_for_question("foo", None, limit=2)
    assert hits[0]["url"] == "https://github.com/quant/paper"
    assert hits[0]["source_type"] == "repo"


def test_search_fails_closed_when_no_usable_channel() -> None:
    def runner(argv: list[str], timeout: int = 60) -> tuple[int, str, str]:
        del argv, timeout
        return (
            0,
            json.dumps(
                {
                    "exa_search": {"status": "error", "active_backend": None, "message": "down"},
                    "github": {"status": "error", "active_backend": None, "message": "down"},
                    "web": {"status": "ok", "active_backend": "jina", "message": "ok"},
                }
            ),
            "",
        )

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

    assert {lane.name for lane in operational_lanes()} == {"exa", "github", "arxiv"}
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


def test_default_runner_decodes_utf8_output_under_a_non_utf8_locale() -> None:
    """text=True alone decodes with the locale codec (cp1252 here), losing UTF-8.

    The real failure this pins: agent-reach doctor emits UTF-8 channel names, the
    locale decode raises on subprocess's reader thread where no caller can catch
    it, and stdout silently becomes None. Must use a real subprocess -- the defect
    lives inside subprocess.run's decode, which no injected runner reaches.
    """
    completed = default_runner(
        [
            sys.executable,
            "-c",
            "import sys; sys.stdout.buffer.write('全网语义搜索'.encode('utf-8'))",
        ],
        timeout=60,
    )

    assert completed.returncode == 0
    assert completed.stdout == "全网语义搜索"


def test_check_health_fails_loudly_when_stdout_is_none() -> None:
    """A null stdout must name its own cause, not surface as a TypeError."""

    def runner(argv: list[str], timeout: int = 60) -> subprocess.CompletedProcess[str]:
        del timeout
        # A real CompletedProcess: the tuple path coerces None to "" and would
        # hide exactly the condition under test.
        return subprocess.CompletedProcess(argv, 0, None, "")

    adapter = AgentReachAdapter(runner=runner, skip_exe_check=True)
    with pytest.raises(AgentReachUnavailable, match="no decodable stdout"):
        adapter.check_health()


def test_doctor_payload_with_non_ascii_channel_names_parses() -> None:
    """The real doctor emits UTF-8; parsing must survive it end to end."""
    adapter = AgentReachAdapter(
        runner=lambda argv, timeout=60: (0, DOCTOR_LIVE_JSON, ""),
        skip_exe_check=True,
    )
    health = adapter.check_health()

    assert health["exa_search"].channel == "exa_search"
    # Load-bearing: fails if the live fixture is ever flattened to ASCII, which
    # would silently delete the coverage the encoding fix depends on.
    assert any(ord(ch) > 127 for ch in health["exa_search"].message)


def test_the_live_doctor_fixture_is_not_edited_into_a_healthy_one() -> None:
    """The verbatim capture must stay verbatim.

    A fixture edited to be convenient, while still called a recording, is what
    let the channel-name defect survive a whole gate.
    """
    payload = json.loads(DOCTOR_LIVE_JSON)

    assert payload["exa_search"]["status"] == "off"
    assert any(ord(ch) > 127 for ch in DOCTOR_LIVE_JSON)
    escape_marker = chr(92) + "u"  # avoid an escape sequence in this file
    assert escape_marker not in DOCTOR_LIVE_JSON, "escapes decode fine under cp1252"


def test_the_search_channel_consulted_is_the_real_doctor_key() -> None:
    """Constants must name reality, not a guess."""
    assert SEARCH_CHANNELS == ("exa_search",)
    assert "search" not in ENABLED_CHANNELS
    assert "exa" not in ENABLED_CHANNELS
    # The general invariant: every dispatched lane that Agent Reach routes must
    # name an enabled channel. This catches the whole defect class, not just
    # this instance. A lane with channel None is not routed by Agent Reach at
    # all (arXiv needs no account or router), so it is exempt by construction
    # rather than by omission -- and must still be a declared lane.
    routed = {lane.channel for lane in operational_lanes() if lane.channel is not None}
    assert routed <= ENABLED_CHANNELS
    assert any(lane.channel is None for lane in operational_lanes())


def test_a_channel_reported_off_is_not_usable() -> None:
    """The verbatim exa_search record from the real doctor on this machine."""
    health = parse_channel_health(
        {
            "exa_search": {
                "status": "off",
                "active_backend": None,
                # Verbatim doctor text. The fullwidth punctuation is real
                # output, so RUF001 is suppressed rather than the text edited.
                "message": (
                    "mcporter 已装但 Exa 未配置。运行：\n"  # noqa: RUF001
                    "  mcporter config add exa https://mcp.exa.ai/mcp --scope home"
                ),
                "name": "全网语义搜索",
            }
        }
    )

    assert is_channel_usable(health, "exa_search") is False


def test_search_fails_closed_when_the_only_search_channel_is_unconfigured() -> None:
    """The real machine state must fail closed cleanly, never crash.

    With exa_search off but github usable, search proceeds GitHub-only. With
    both unavailable it raises. Neither path may raise an encoding or type
    error.
    """
    base = json.loads(DOCTOR_LIVE_JSON)
    assert base["exa_search"]["status"] == "off"

    def runner(argv: list[str], timeout: int = 60) -> tuple[int, str, str]:
        del timeout
        if "doctor" in argv:
            return 0, json.dumps(base, ensure_ascii=False), ""
        if argv and argv[0] == "gh":
            return 0, json.dumps([{"url": "https://github.com/x/y", "name": "y"}]), ""
        return 1, "", "exa is off; must not be called"

    hits = AgentReachAdapter(runner=runner, skip_exe_check=True).search_for_question(
        "exit rules", None, limit=2
    )
    assert [hit["url"] for hit in hits] == ["https://github.com/x/y"]

    both_off = json.loads(DOCTOR_LIVE_JSON)
    both_off["github"]["status"] = "off"

    def runner_both_off(argv: list[str], timeout: int = 60) -> tuple[int, str, str]:
        del timeout
        if "doctor" in argv:
            return 0, json.dumps(both_off, ensure_ascii=False), ""
        return 1, "", "no channel should be called"

    adapter = AgentReachAdapter(runner=runner_both_off, skip_exe_check=True)
    with pytest.raises(AgentReachError, match="no usable Agent Reach search channel"):
        adapter.search_for_question("exit rules", None, limit=2)


def test_a_long_research_question_is_trimmed_to_githubs_query_limit() -> None:
    """GitHub rejects >=256 chars, turning an empty result into a query error.

    Trimming does not make a long question answerable by GitHub; it makes the
    reported reason truthful.
    """
    from quant_brain.discovery.agent_reach import (
        GITHUB_QUERY_MAX_CHARS,
        bound_github_query,
    )

    long_question = (
        "What source-supported EXIT rules pair with daily ETF RSI oversold "
        "entries (locked candidates: Wilder RSI(14)<30 at close or RSI(2)<20 "
        "at close; next-bar fill) for SPY/QQQ/IWM, without optimizing? Return "
        "at most TWO exit candidates, each with exact rule text, upstream "
        "citation, and instrument/timeframe assumptions. OUT OF SCOPE: "
        "changing entries, backtests, best RSI settings."
    )
    assert len(long_question) > GITHUB_QUERY_MAX_CHARS

    bounded = bound_github_query(long_question)
    assert len(bounded) < GITHUB_QUERY_MAX_CHARS
    assert not bounded.endswith(" ")
    assert long_question.startswith(bounded)

    short = "ETF mean reversion exit rules"
    assert bound_github_query(short) == short


def test_search_github_sends_the_bounded_query() -> None:
    sent: list[str] = []

    def runner(argv: list[str], timeout: int = 60) -> tuple[int, str, str]:
        del timeout
        sent.append(argv[3])
        return 0, json.dumps([]), ""

    adapter = AgentReachAdapter(runner=runner, skip_exe_check=True)
    adapter.search_github("word " * 200, limit=3)

    from quant_brain.discovery.agent_reach import GITHUB_QUERY_MAX_CHARS

    assert sent and len(sent[0]) < GITHUB_QUERY_MAX_CHARS

from pathlib import Path

from quant_brain.research.live_discovery import (
    DiscoveryCandidate,
    build_opencli_search_command,
    condense_search_query,
    dedupe_and_rank,
    parse_search_results,
    save_source_snapshot,
)


def test_parse_search_results_and_rank_primary_sources_above_promotional_noise():
    raw = """[
      {"rank": 1, "title": "Secret RSI Strategy", "url": "https://spam.example/95-win", "snippet": "Guaranteed 95% wins"},
      {"rank": 2, "title": "RSI documentation", "url": "https://www.quantconnect.com/docs/rsi", "snippet": "Official indicator documentation and timing"},
      {"rank": 3, "title": "Duplicate RSI docs", "url": "https://www.quantconnect.com/docs/rsi/", "snippet": "Same page"}
    ]"""

    candidates = parse_search_results(raw, query="RSI exit rule timing")
    ranked = dedupe_and_rank(candidates, query="RSI exit rule timing", limit=5)

    assert len(ranked) == 2
    assert ranked[0].url == "https://www.quantconnect.com/docs/rsi"
    assert ranked[0].source_quality == "primary"
    assert ranked[1].source_quality == "discovery-only"


def test_save_source_snapshot_writes_provenance_content_and_checksum(tmp_path):
    candidate = DiscoveryCandidate(
        title="Example source",
        url="https://example.com/research",
        snippet="Example",
        source_quality="practitioner",
        score=2.0,
    )

    snapshot = save_source_snapshot(
        tmp_path,
        research_id="RQ-test",
        source_id="S1",
        candidate=candidate,
        fetched_text="# Research\n\nExact evidence passage.",
    )

    path = Path(snapshot["snapshot_path"])
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "source_id: S1" in text
    assert "https://example.com/research" in text
    assert "Exact evidence passage" in text
    assert len(snapshot["content_hash"]) == 64


def test_dedupe_and_rank_keeps_bounded_candidate_count():
    candidates = [
        DiscoveryCandidate(
            title=f"Source {index}",
            url=f"https://example{index}.com/article",
            snippet="RSI exit holding period costs",
            source_quality="practitioner",
        )
        for index in range(10)
    ]

    ranked = dedupe_and_rank(candidates, query="RSI exit holding period costs", limit=4)

    assert len(ranked) == 4
    assert all(item.score > 0 for item in ranked)


def test_condense_search_query_keeps_core_terms_and_bounds_length():
    question = (
        "Find high-quality sources for simple non-optimized exit conditions and maximum "
        "holding periods that could pair with daily ETF RSI oversold entries. Compare at most "
        "two source-supported choices, explain timing and regime risks, and propose fixed "
        "transaction-cost assumptions. Do not backtest or optimize."
    )

    query = condense_search_query(question, max_chars=150)

    assert len(query) <= 150
    assert "RSI" in query
    assert "exit" in query.lower()
    assert "holding" in query.lower()
    assert "backtest" not in query.lower()


def test_opencli_search_command_uses_node_for_windows_cmd_shim():
    command = build_opencli_search_command(
        "RSI exit rules",
        executable="C:/Users/jason/AppData/Roaming/npm/opencli.cmd",
        windows=True,
        node_executable="C:/Program Files/nodejs/node.exe",
        opencli_script="C:/Users/jason/AppData/Roaming/npm/node_modules/@jackwener/opencli/dist/src/main.js",
    )

    assert command == [
        "C:/Program Files/nodejs/node.exe",
        str(
            Path(
                "C:/Users/jason/AppData/Roaming/npm/node_modules/@jackwener/opencli/dist/src/main.js"
            )
        ),
        "yahoo",
        "search",
        "RSI exit rules",
        "-f",
        "json",
    ]

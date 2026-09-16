import json
from pathlib import Path

from quant_brain.db.init_db import connect, init_database
from quant_brain.ops.events import list_events, summarize_run
from quant_brain.research.intake import add_research_question
from quant_brain.research.live_discovery import DiscoveryCandidate
from quant_brain.research.live_executor import execute_live_research


def test_execute_live_research_writes_raw_note_updates_task_and_emits_handoffs(tmp_path):
    db_path = tmp_path / "brain.sqlite"
    init_database(db_path)
    task = add_research_question(
        db_path,
        "Find evidence-backed RSI exits and holding periods",
        method_family="mean_reversion",
        priority=1,
    )

    def searcher(query):
        assert "RSI" in query
        return [
            DiscoveryCandidate(
                title="Official source",
                url="https://www.quantconnect.com/docs/rsi-exits",
                snippet="RSI exit evidence",
                source_quality="primary",
                score=10,
            )
        ]

    def fetcher(url):
        assert url == "https://www.quantconnect.com/docs/rsi-exits"
        return "Official evidence says exit timing remains unresolved."

    def worker(research_id, question, snapshots):
        return {
            "passed": True,
            "validation": {"passed": True, "failures": []},
            "attempts": [{"model": "qwen3:14b", "elapsed_seconds": 1.0}],
            "payload": {
                "research_id": research_id,
                "decision": "needs_more_work",
                "sources": [
                    {
                        "source_id": "S1",
                        "title": "Official source",
                        "url": "https://www.quantconnect.com/docs/rsi-exits",
                        "source_type": "docs",
                        "source_quality": "primary",
                        "main_claim": "Exit timing remains unresolved.",
                        "evidence_quote": "exit timing remains unresolved",
                        "possible_strategy_rule": "",
                        "risks": ["Do not invent an exit."],
                        "confidence": "high",
                        "asset_classes": ["equities"],
                        "data_required": ["daily close"],
                        "data_access": "available-now",
                        "mvp_testable": False,
                    }
                ],
                "open_questions": ["Which source defines an exit?"],
                "curator_recommendation": "needs_more_work",
            },
        }

    result = execute_live_research(
        tmp_path,
        db_path,
        research_id=task["research_id"],
        run_id="RUN-test",
        searcher=searcher,
        fetcher=fetcher,
        worker=worker,
        doctor=lambda: {"web": {"status": "ok"}},
        max_sources=3,
    )

    raw_path = Path(result["raw_note_path"])
    assert raw_path.exists()
    raw_text = raw_path.read_text(encoding="utf-8")
    assert "source_quality" in raw_text
    assert "https://www.quantconnect.com/docs/rsi-exits" in raw_text
    json_block = raw_text.split("```json", 1)[1].split("```", 1)[0]
    payload = json.loads(json_block)
    assert payload["research_id"] == task["research_id"]
    assert payload["sources"][0]["url_or_citation"].endswith("rsi-exits")

    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT status, raw_note_path FROM research_questions WHERE research_id = ?",
            (task["research_id"],),
        ).fetchone()
    assert row["status"] == "raw_saved"
    assert row["raw_note_path"] == str(raw_path)

    events = list_events(db_path, run_id="RUN-test")
    roles = {event["agent_role"] for event in events}
    state = summarize_run(events)
    assert {"research_scout", "qwen3:14b", "knowledge_curator"}.issubset(roles)
    assert state["agents"]["research_scout"]["status"] == "completed"
    assert state["agents"]["qwen3:14b"]["status"] == "completed"
    assert state["agents"]["knowledge_curator"]["status"] == "waiting"
    assert events[-1]["status"] == "completed"
    assert result["sources_fetched"] == 1

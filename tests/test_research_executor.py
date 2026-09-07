from pathlib import Path

from quant_brain.db.init_db import connect, init_database
from quant_brain.research.executor import (
    execute_research_task,
    format_findings_markdown,
    select_candidate_sources,
)
from quant_brain.research.intake import add_research_question, update_research_status
from quant_brain.research.scout_runner import create_raw_research_note, build_scout_prompt


def test_select_candidate_sources_matches_method_family():
    sources = select_candidate_sources("mean_reversion", "ETF RSI mean reversion")

    assert len(sources) >= 3
    assert any("RSI" in source["title"] or "relative strength" in source["main_claim"].lower() for source in sources)
    assert all("title" in source and "url_or_citation" in source for source in sources)


def test_format_findings_markdown_includes_sources_and_required_json():
    task = {
        "research_id": "RQ-test",
        "question": "Research ETF mean reversion",
        "method_family": "mean_reversion",
    }
    sources = select_candidate_sources("mean_reversion", "ETF RSI mean reversion")[:2]

    text = format_findings_markdown(task, sources)

    assert "## Scout Findings" in text
    assert "Source 1" in text
    assert "```json" in text
    assert '"research_id": "RQ-test"' in text
    assert '"curator_recommendation"' in text


def test_execute_research_task_fills_raw_note_and_marks_raw_saved(tmp_path):
    db_path = tmp_path / "brain.sqlite"
    init_database(db_path)
    task = add_research_question(db_path, "Research ETF mean reversion", "mean_reversion")
    raw_path = create_raw_research_note(tmp_path, db_path, task, build_scout_prompt(task))

    result = execute_research_task(tmp_path, db_path, task["research_id"])

    assert result["status"] == "raw_saved"
    assert result["sources_count"] >= 3
    text = Path(raw_path).read_text(encoding="utf-8")
    assert "## Scout Findings" in text
    assert "curator_recommendation" in text
    assert '"data_access"' in text
    assert "Scout findings go here." not in text

    with connect(db_path) as conn:
        row = conn.execute(
            "select status, raw_note_path from research_questions where research_id = ?",
            (task["research_id"],),
        ).fetchone()

    assert row["status"] == "raw_saved"
    assert row["raw_note_path"] == raw_path


def test_execute_research_task_requires_existing_raw_note(tmp_path):
    db_path = tmp_path / "brain.sqlite"
    init_database(db_path)
    task = add_research_question(db_path, "Research ETF mean reversion", "mean_reversion")
    update_research_status(db_path, task["research_id"], "researching")

    try:
        execute_research_task(tmp_path, db_path, task["research_id"])
    except ValueError as exc:
        assert "raw note" in str(exc).lower()
    else:
        raise AssertionError("Expected missing raw note to be rejected")

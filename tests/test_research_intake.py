from pathlib import Path

from quant_brain.db.init_db import connect, init_database
from quant_brain.research.intake import (
    add_research_question,
    create_research_brief,
    list_research_questions,
    update_research_status,
)


def test_add_research_question_creates_queue_row(tmp_path):
    db_path = tmp_path / "brain.sqlite"
    init_database(db_path)

    task = add_research_question(
        db_path=db_path,
        question="What is RSI mean reversion?",
        method_family="mean_reversion",
        priority=2,
    )

    assert task["research_id"].startswith("RQ-")
    assert task["status"] == "queued"
    assert task["method_family"] == "mean_reversion"

    with connect(db_path) as conn:
        row = conn.execute("select question, priority from research_questions").fetchone()

    assert row["question"] == "What is RSI mean reversion?"
    assert row["priority"] == 2


def test_list_research_questions_orders_by_status_priority_and_created(tmp_path):
    db_path = tmp_path / "brain.sqlite"
    init_database(db_path)

    add_research_question(db_path, "Low priority", priority=5)
    add_research_question(db_path, "High priority", priority=1)

    rows = list_research_questions(db_path)

    assert [row["question"] for row in rows] == ["High priority", "Low priority"]


def test_update_research_status_records_output_paths(tmp_path):
    db_path = tmp_path / "brain.sqlite"
    init_database(db_path)
    task = add_research_question(db_path, "Find trend following sources")

    update_research_status(
        db_path,
        research_id=task["research_id"],
        status="curated",
        raw_note_path="brain/00_Inbox/RQ-test.md",
        source_note_path="brain/01_Sources/test.md",
    )

    rows = list_research_questions(db_path)
    assert rows[0]["status"] == "curated"
    assert rows[0]["raw_note_path"] == "brain/00_Inbox/RQ-test.md"
    assert rows[0]["source_note_path"] == "brain/01_Sources/test.md"


def test_create_research_brief_writes_markdown_with_agent_instructions(tmp_path):
    db_path = tmp_path / "brain.sqlite"
    project_root = tmp_path
    init_database(db_path)
    task = add_research_question(
        db_path,
        "Find legal public sources for ETF mean reversion strategies",
        method_family="mean_reversion",
    )

    brief_path = create_research_brief(project_root, task)

    assert Path(brief_path).exists()
    text = Path(brief_path).read_text(encoding="utf-8")
    assert "Research Question" in text
    assert "Allowed Write Locations" in text
    assert "Do not download copyrighted books illegally" in text
    assert "Find legal public sources" in text

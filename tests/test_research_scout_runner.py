from pathlib import Path

from quant_brain.db.init_db import connect, init_database
from quant_brain.research.intake import add_research_question, update_research_status
from quant_brain.research.scout_runner import (
    build_scout_prompt,
    claim_next_research_task,
    create_raw_research_note,
    prepare_next_research_run,
)


def test_claim_next_research_task_picks_highest_priority_queued(tmp_path):
    db_path = tmp_path / "brain.sqlite"
    init_database(db_path)
    add_research_question(db_path, "Low priority", priority=5)
    high = add_research_question(db_path, "High priority", priority=1)

    claimed = claim_next_research_task(db_path)

    assert claimed["research_id"] == high["research_id"]
    assert claimed["status"] == "researching"

    with connect(db_path) as conn:
        row = conn.execute(
            "select status from research_questions where research_id = ?",
            (high["research_id"],),
        ).fetchone()
    assert row["status"] == "researching"


def test_claim_next_research_task_ignores_non_queued(tmp_path):
    db_path = tmp_path / "brain.sqlite"
    init_database(db_path)
    task = add_research_question(db_path, "Already raw", priority=1)
    update_research_status(db_path, task["research_id"], "raw_saved")

    assert claim_next_research_task(db_path) is None


def test_build_scout_prompt_contains_scope_output_schema_and_guardrails():
    task = {
        "research_id": "RQ-test",
        "question": "Research ETF mean reversion",
        "method_family": "mean_reversion",
    }

    prompt = build_scout_prompt(task)

    assert "Research Scout" in prompt
    assert "Research ETF mean reversion" in prompt
    assert "Do not create strategy cards" in prompt
    assert "Required JSON Block" in prompt
    assert "Source URL / citation" in prompt
    assert "brain/00_Inbox" in prompt
    assert "Agent Reach" in prompt
    assert "not restricted to one asset class" in prompt
    assert "Discovery is not proof" in prompt
    assert "source quality" in prompt.lower()


def test_create_raw_research_note_writes_agent_ready_note_and_updates_status(tmp_path):
    db_path = tmp_path / "brain.sqlite"
    init_database(db_path)
    task = add_research_question(db_path, "Research ETF mean reversion", "mean_reversion")

    path = create_raw_research_note(tmp_path, db_path, task, prompt="Prompt text")

    note = Path(path)
    assert note.exists()
    text = note.read_text(encoding="utf-8")
    assert "Raw Research Note" in text
    assert "Prompt text" in text
    assert "Paste / Agent Findings" in text

    with connect(db_path) as conn:
        row = conn.execute("select status, raw_note_path from research_questions").fetchone()
    assert row["status"] == "researching"
    assert row["raw_note_path"] == str(note)


def test_prepare_next_research_run_claims_task_and_creates_prompt_note(tmp_path):
    db_path = tmp_path / "brain.sqlite"
    init_database(db_path)
    add_research_question(db_path, "Research ETF trend following", "trend_following", priority=1)

    prepared = prepare_next_research_run(tmp_path, db_path)

    assert prepared is not None
    assert prepared["research_id"].startswith("RQ-")
    assert Path(prepared["raw_note_path"]).exists()
    assert "Research Scout" in prepared["prompt"]

from pathlib import Path

from quant_brain.curation.promotion import (
    CuratedSource,
    PromotionDecision,
    create_curator_review,
    promote_source_note,
)
from quant_brain.db.init_db import connect, init_database
from quant_brain.research.intake import add_research_question


def test_create_curator_review_writes_review_to_inbox(tmp_path):
    db_path = tmp_path / "brain.sqlite"
    init_database(db_path)
    task = add_research_question(db_path, "Research RSI mean reversion", "mean_reversion")

    decision = PromotionDecision(
        research_id=task["research_id"],
        verdict="promote_source",
        reason="Source has clear testable RSI rules and risks.",
        source_quality="medium",
        next_location="brain/01_Sources/blogs/rsi-mean-reversion.md",
    )

    path = create_curator_review(tmp_path, decision)

    text = Path(path).read_text(encoding="utf-8")
    assert "Curator Review" in text
    assert "promote_source" in text
    assert "Source has clear testable RSI rules" in text
    assert Path(path).parent.name == "Curator_Reviews"


def test_promote_source_note_creates_markdown_and_database_source(tmp_path):
    db_path = tmp_path / "brain.sqlite"
    init_database(db_path)
    task = add_research_question(db_path, "Research RSI mean reversion", "mean_reversion")

    source = CuratedSource(
        research_id=task["research_id"],
        title="RSI Mean Reversion Notes",
        source_type="blog",
        url="https://example.com/rsi",
        summary="A source discussing RSI-style mean reversion rules.",
        useful_claims=["RSI can be used to define oversold conditions."],
        strategy_rules=["Buy next day when RSI is below a threshold."],
        risks=["May fail in persistent downtrends."],
        confidence="medium",
        method_family="mean_reversion",
    )

    path = promote_source_note(tmp_path, db_path, source)

    text = Path(path).read_text(encoding="utf-8")
    assert "RSI Mean Reversion Notes" in text
    assert "https://example.com/rsi" in text
    assert "Buy next day" in text

    with connect(db_path) as conn:
        source_row = conn.execute("select title, url, source_type from sources").fetchone()
        question_row = conn.execute("select status, source_note_path from research_questions").fetchone()

    assert dict(source_row) == {
        "title": "RSI Mean Reversion Notes",
        "url": "https://example.com/rsi",
        "source_type": "blog",
    }
    assert question_row["status"] == "curated"
    assert question_row["source_note_path"] == str(path)


def test_promote_source_note_requires_evidence_or_unverified_label(tmp_path):
    db_path = tmp_path / "brain.sqlite"
    init_database(db_path)
    task = add_research_question(db_path, "Research RSI mean reversion", "mean_reversion")

    source = CuratedSource(
        research_id=task["research_id"],
        title="Weak Notes",
        source_type="blog",
        url="https://example.com/weak",
        summary="Unsourced confident claim.",
        useful_claims=["This always beats the market."],
        strategy_rules=[],
        risks=[],
        confidence="high",
        method_family="mean_reversion",
    )

    try:
        promote_source_note(tmp_path, db_path, source)
    except ValueError as exc:
        assert "evidence" in str(exc).lower() or "unverified" in str(exc).lower()
    else:
        raise AssertionError("Expected weak promoted source to be rejected")

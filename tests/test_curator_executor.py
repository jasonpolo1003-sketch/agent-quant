import json
from pathlib import Path

from quant_brain.curation.executor import (
    CuratorResult,
    execute_curator_task,
    extract_scout_json,
    source_payload_to_curated_source,
)
from quant_brain.db.init_db import connect, init_database
from quant_brain.research.intake import add_research_question, update_research_status


def write_raw_note(path: Path, research_id: str, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""---
id: {research_id}
type: raw_research
status: raw_saved
---

# Raw Research Note — {research_id}

## Scout Findings

Some findings.

```json
{json.dumps(payload, indent=2)}
```
""",
        encoding="utf-8",
    )


def sample_payload(research_id="RQ-test"):
    return {
        "research_id": research_id,
        "status": "raw_saved",
        "sources": [
            {
                "title": "Look-Ahead Bias Notes",
                "source_type": "docs",
                "url_or_citation": "https://example.com/lookahead",
                "main_claim": "Signals must avoid future data.",
                "evidence": (
                    "Signals must avoid future data. Enter no earlier than the next bar."
                ),
                "possible_strategy_rule": "Enter no earlier than the next bar.",
                "risks": ["Cheating with future data inflates performance."],
                "confidence": "high",
                "source_quality": "primary",
                "asset_classes": ["equity", "etf"],
                "data_required": ["daily bars with next-bar execution"],
                "data_access": "available-now",
                "mvp_testable": True,
            },
            {
                "title": "Background Book",
                "source_type": "book",
                "url_or_citation": "Example Book, 2020",
                "main_claim": "General quant background.",
                "evidence": "Citation only.",
                "possible_strategy_rule": "Do not promote rules without exact evidence.",
                "risks": ["Background only."],
                "confidence": "medium",
                "source_quality": "practitioner",
                "asset_classes": ["equity"],
                "data_required": ["user-owned copy"],
                "data_access": "available-later",
                "mvp_testable": False,
            },
            {
                "title": "Unsourced Video Claim",
                "source_type": "other",
                "url_or_citation": "https://example.com/video",
                "main_claim": "A screenshot says the strategy always wins.",
                "evidence": "No reproducible evidence.",
                "possible_strategy_rule": "Unknown.",
                "risks": ["Discovery lead only."],
                "confidence": "low",
                "source_quality": "discovery-only",
                "asset_classes": [],
                "data_required": [],
                "data_access": "not-realistic",
                "mvp_testable": True,
            },
        ],
        "open_questions": ["Which RSI threshold first?"],
        "curator_recommendation": "promote_source",
    }


def test_extract_scout_json_reads_final_fenced_json_block(tmp_path):
    payload = sample_payload("RQ-json")
    raw_note = tmp_path / "raw.md"
    write_raw_note(raw_note, "RQ-json", payload)

    parsed = extract_scout_json(raw_note)

    assert parsed["research_id"] == "RQ-json"
    assert len(parsed["sources"]) == 3
    assert parsed["sources"][0]["title"] == "Look-Ahead Bias Notes"


def test_source_payload_to_curated_source_maps_fields():
    source = source_payload_to_curated_source(
        "RQ-map",
        sample_payload("RQ-map")["sources"][0],
        method_family="mean_reversion",
    )

    assert source.research_id == "RQ-map"
    assert source.title == "Look-Ahead Bias Notes"
    assert source.url == "https://example.com/lookahead"
    assert source.useful_claims == ["Signals must avoid future data."]
    assert source.strategy_rules == ["Enter no earlier than the next bar."]
    assert source.method_family == "mean_reversion"
    assert source.trust_level == "primary"


def test_execute_curator_task_promotes_mvp_sources_and_records_review(tmp_path):
    db_path = tmp_path / "brain.sqlite"
    init_database(db_path)
    task = add_research_question(db_path, "Research ETF mean reversion", "mean_reversion")
    raw_note = tmp_path / "brain" / "00_Inbox" / "Raw_Research" / f"{task['research_id']}.md"
    write_raw_note(raw_note, task["research_id"], sample_payload(task["research_id"]))
    update_research_status(db_path, task["research_id"], "raw_saved", raw_note_path=str(raw_note))

    result = execute_curator_task(tmp_path, db_path, task["research_id"])

    assert isinstance(result, CuratorResult)
    assert result.status == "curated"
    assert result.promoted_sources_count == 1
    assert result.skipped_sources_count == 2
    assert Path(result.curator_note_path).exists()
    assert len(result.promoted_paths) == 1
    assert Path(result.promoted_paths[0]).exists()

    with connect(db_path) as conn:
        rq = conn.execute("select status, curator_note_path from research_questions").fetchone()
        sources_count = conn.execute("select count(*) from sources").fetchone()[0]
        findings_count = conn.execute("select count(*) from research_findings").fetchone()[0]

    assert rq["status"] == "curated"
    assert rq["curator_note_path"] == result.curator_note_path
    assert sources_count == 1
    assert findings_count == 1


def test_model_judgment_alone_cannot_authorize_promotion(tmp_path):
    """mvp_testable/confidence/recommendation are advisory, not promotion authority.

    The reviewer's payload: a benign, exact quotation paired with an invented
    "robust strategy" conclusion and every model field set to favor promotion.
    Nothing in the source text supports the conclusion, so no durable source
    note may be written.
    """
    db_path = tmp_path / "brain.sqlite"
    init_database(db_path)
    task = add_research_question(db_path, "Research ETF mean reversion", "mean_reversion")
    payload = sample_payload(task["research_id"])
    payload["sources"] = [
        {
            "title": "Benign Note",
            "source_type": "docs",
            "url_or_citation": "https://example.com/benign",
            "main_claim": "A robust strategy is supported.",
            "evidence": "The page describes an indicator.",
            "possible_strategy_rule": "",
            "risks": ["Unverified interpretation."],
            "confidence": "high",
            "source_quality": "primary",
            "asset_classes": ["equity"],
            "data_required": ["daily close"],
            "data_access": "available-now",
            "mvp_testable": True,
        }
    ]
    payload["curator_recommendation"] = "promote_source"
    raw_note = tmp_path / "brain" / "00_Inbox" / "Raw_Research" / f"{task['research_id']}.md"
    write_raw_note(raw_note, task["research_id"], payload)
    update_research_status(db_path, task["research_id"], "raw_saved", raw_note_path=str(raw_note))

    result = execute_curator_task(tmp_path, db_path, task["research_id"])

    assert result.promoted_sources_count == 0
    assert result.promoted_paths == []
    assert result.status == "rejected"
    with connect(db_path) as conn:
        assert conn.execute("select count(*) from sources").fetchone()[0] == 0
    assert not (tmp_path / "brain" / "01_Sources").exists()


def test_generic_ungrounded_claim_cannot_authorize_promotion(tmp_path):
    """Promotion requires extractive support even without known risk keywords."""
    db_path = tmp_path / "brain.sqlite"
    init_database(db_path)
    task = add_research_question(db_path, "Research ETF mean reversion", "mean_reversion")
    payload = sample_payload(task["research_id"])
    payload["sources"] = [
        {
            "title": "Benign Note",
            "source_type": "docs",
            "url_or_citation": "https://example.com/benign",
            "main_claim": "This proves the method works reliably.",
            "evidence": "The page describes an indicator.",
            "possible_strategy_rule": "",
            "risks": ["Requires review."],
            "confidence": "high",
            "source_quality": "primary",
            "asset_classes": ["equity"],
            "data_required": ["daily close"],
            "data_access": "available-now",
            "mvp_testable": True,
        }
    ]
    payload["curator_recommendation"] = "promote_source"
    raw_note = tmp_path / "brain" / "00_Inbox" / "Raw_Research" / f"{task['research_id']}.md"
    write_raw_note(raw_note, task["research_id"], payload)
    update_research_status(db_path, task["research_id"], "raw_saved", raw_note_path=str(raw_note))

    result = execute_curator_task(tmp_path, db_path, task["research_id"])

    assert result.status == "rejected"
    assert result.promoted_sources_count == 0
    assert not (tmp_path / "brain" / "01_Sources").exists()


def test_generic_ungrounded_strategy_rule_cannot_become_durable(tmp_path):
    """Curator independently blocks a rule absent from exact evidence."""
    db_path = tmp_path / "brain.sqlite"
    init_database(db_path)
    task = add_research_question(db_path, "Research ETF mean reversion", "mean_reversion")
    payload = sample_payload(task["research_id"])
    payload["sources"] = [
        {
            "title": "Benign Note",
            "source_type": "docs",
            "url_or_citation": "https://example.com/benign",
            "main_claim": "The page describes an indicator.",
            "evidence": "The page describes an indicator.",
            "possible_strategy_rule": "This method works reliably.",
            "risks": ["Requires review."],
            "confidence": "high",
            "source_quality": "primary",
            "asset_classes": ["equity"],
            "data_required": ["daily close"],
            "data_access": "available-now",
            "mvp_testable": True,
        }
    ]
    payload["curator_recommendation"] = "promote_source"
    raw_note = tmp_path / "brain" / "00_Inbox" / "Raw_Research" / f"{task['research_id']}.md"
    write_raw_note(raw_note, task["research_id"], payload)
    update_research_status(db_path, task["research_id"], "raw_saved", raw_note_path=str(raw_note))

    result = execute_curator_task(tmp_path, db_path, task["research_id"])

    assert result.status == "rejected"
    assert result.promoted_sources_count == 0
    assert not (tmp_path / "brain" / "01_Sources").exists()


def test_execute_curator_task_rejects_missing_json(tmp_path):
    db_path = tmp_path / "brain.sqlite"
    init_database(db_path)
    task = add_research_question(db_path, "Research ETF mean reversion", "mean_reversion")
    raw_note = tmp_path / "brain" / "00_Inbox" / "Raw_Research" / f"{task['research_id']}.md"
    raw_note.parent.mkdir(parents=True, exist_ok=True)
    raw_note.write_text("# Raw note with no JSON", encoding="utf-8")
    update_research_status(db_path, task["research_id"], "raw_saved", raw_note_path=str(raw_note))

    try:
        execute_curator_task(tmp_path, db_path, task["research_id"])
    except ValueError as exc:
        assert "json" in str(exc).lower()
    else:
        raise AssertionError("Expected missing JSON block to be rejected")


def test_execute_curator_task_rejects_illegal_data_access_and_does_not_promote(tmp_path):
    from quant_brain.research.schema import RawResearchSchemaError

    db_path = tmp_path / "brain.sqlite"
    init_database(db_path)
    task = add_research_question(db_path, "Research ETF mean reversion", "mean_reversion")
    payload = sample_payload(task["research_id"])
    payload["sources"][0]["data_access"] = "partial"
    raw_note = tmp_path / "brain" / "00_Inbox" / "Raw_Research" / f"{task['research_id']}.md"
    write_raw_note(raw_note, task["research_id"], payload)
    update_research_status(db_path, task["research_id"], "raw_saved", raw_note_path=str(raw_note))

    try:
        execute_curator_task(tmp_path, db_path, task["research_id"])
    except RawResearchSchemaError as exc:
        assert "data_access" in str(exc)
    else:
        raise AssertionError("Expected illegal data_access to fail closed")

    sources_dir = tmp_path / "brain" / "01_Sources"
    assert not sources_dir.exists() or not any(sources_dir.rglob("*.md"))
    with connect(db_path) as conn:
        row = conn.execute(
            "select status from research_questions where research_id = ?",
            (task["research_id"],),
        ).fetchone()
        findings = conn.execute("select count(*) from research_findings").fetchone()[0]
    assert row["status"] == "raw_saved"
    assert findings == 0


def test_execute_curator_task_writes_rejected_review_when_nothing_is_promoted(tmp_path):
    db_path = tmp_path / "brain.sqlite"
    init_database(db_path)
    task = add_research_question(db_path, "Research weak source", "mean_reversion")
    payload = sample_payload(task["research_id"])
    payload["sources"] = [payload["sources"][2]]
    payload["curator_recommendation"] = "rejected"
    raw_note = tmp_path / "brain" / "00_Inbox" / "Raw_Research" / f"{task['research_id']}.md"
    write_raw_note(raw_note, task["research_id"], payload)
    update_research_status(db_path, task["research_id"], "raw_saved", raw_note_path=str(raw_note))

    result = execute_curator_task(tmp_path, db_path, task["research_id"])

    assert result.status == "rejected"
    assert result.curator_note_path.endswith("-rejected.md")
    review = Path(result.curator_note_path).read_text(encoding="utf-8")
    assert "verdict: rejected" in review
    assert "## Verdict\n\nrejected" in review

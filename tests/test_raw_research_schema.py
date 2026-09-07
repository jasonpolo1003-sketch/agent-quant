import json
from pathlib import Path

import pytest

from quant_brain.research.schema import (
    DATA_ACCESS_VALUES,
    RawResearchSchemaError,
    validate_raw_research_note,
    validate_raw_research_payload,
)


def legal_source(**overrides):
    source = {
        "title": "Look-Ahead Bias Notes",
        "source_type": "docs",
        "url_or_citation": "https://example.com/lookahead",
        "main_claim": "Signals must avoid future data.",
        "evidence": "Close-based signal needs next-bar execution.",
        "possible_strategy_rule": "Enter no earlier than the next bar.",
        "risks": ["Cheating with future data inflates performance."],
        "confidence": "high",
        "source_quality": "primary",
        "asset_classes": ["equity", "etf"],
        "data_required": ["daily bars"],
        "data_access": "available-now",
        "mvp_testable": True,
    }
    source.update(overrides)
    return source


def legal_payload(research_id="RQ-test", **overrides):
    payload = {
        "research_id": research_id,
        "status": "raw_saved",
        "sources": [legal_source()],
        "open_questions": ["What exit rule?"],
        "curator_recommendation": "needs_more_work",
    }
    payload.update(overrides)
    return payload


@pytest.mark.parametrize("data_access", DATA_ACCESS_VALUES)
def test_legal_data_access_enums_are_accepted(data_access):
    payload = legal_payload(sources=[legal_source(data_access=data_access)])

    validated = validate_raw_research_payload(payload)

    assert validated["sources"][0]["data_access"] == data_access


def test_illegal_data_access_is_rejected():
    payload = legal_payload(sources=[legal_source(data_access="partial")])

    with pytest.raises(RawResearchSchemaError, match="data_access") as exc:
        validate_raw_research_payload(payload)

    assert "partial" in str(exc.value) or "data_access" in str(exc.value)


def test_missing_required_source_field_is_rejected():
    source = legal_source()
    del source["source_quality"]

    with pytest.raises(RawResearchSchemaError, match="source_quality"):
        validate_raw_research_payload(legal_payload(sources=[source]))


def test_unknown_field_is_rejected():
    payload = legal_payload()
    payload["sources"][0]["secret_alpha"] = "do not silently accept"

    with pytest.raises(RawResearchSchemaError):
        validate_raw_research_payload(payload)


def test_validate_raw_research_note_reads_final_json_block(tmp_path):
    payload = legal_payload("RQ-note")
    path = tmp_path / "RQ-note.md"
    path.write_text(
        "# Raw\n\n```json\n" + json.dumps(payload) + "\n```\n",
        encoding="utf-8",
    )

    validated = validate_raw_research_note(path)

    assert validated["research_id"] == "RQ-note"


def test_cli_rejects_illegal_payload(tmp_path, capsys):
    from quant_brain.research.schema import main

    path = tmp_path / "bad.json"
    path.write_text(json.dumps(legal_payload(sources=[legal_source(data_access="partial")])), encoding="utf-8")

    assert main([str(path)]) == 2
    captured = capsys.readouterr()
    assert "data_access" in captured.err

import hashlib
import json
from copy import deepcopy

import pytest

from quant_brain.llm.ollama_client import OllamaResponse
from quant_brain.llm.qwen_call import QwenValidationError, qwen_call
from quant_brain.ops.events import list_events


def evidence():
    return [{
        "source_id": "S1", "title": "Study", "url_or_citation": "https://example.test/study",
        "source_quality": "primary", "snapshot_text": "Exact passage. RSI below 30.",
    }]


def valid_payload():
    return {
        "research_id": "RQ-test", "status": "raw_saved",
        "sources": [{
            "source_id": "S1", "title": "Study", "source_type": "paper",
            "url_or_citation": "https://example.test/study", "main_claim": "RSI below 30.",
            "evidence": "Exact passage.", "possible_strategy_rule": "RSI below 30.",
            "risks": ["Caveat"], "confidence": "medium", "source_quality": "primary",
            "asset_classes": ["equity"], "data_required": ["daily close"],
            "data_access": "available-now", "mvp_testable": True,
        }], "open_questions": [], "curator_recommendation": "promote_source",
    }


class StubClient:
    def __init__(self, payloads):
        self.payloads = iter(payloads)
        self.calls = []

    def generate(self, prompt, model, **kwargs):
        self.calls.append((prompt, model, kwargs))
        text = json.dumps(next(self.payloads))
        return OllamaResponse(text, model, 0.25, hashlib.sha256(prompt.encode()).hexdigest(),
                              hashlib.sha256(text.encode()).hexdigest())


def invalid_payload():
    payload = deepcopy(valid_payload())
    payload["sources"][0]["source_id"] = "S9"
    return payload


def test_first_pass_uses_14b_temp_zero_schema_mode_and_records_event(tmp_path):
    client = StubClient([valid_payload()])
    result = qwen_call("Extract", evidence(), expected_research_id="RQ-test", client=client,
                       db_path=tmp_path / "brain.sqlite", run_id="RUN-1", task_id="TASK-1")
    assert result.model_used == "qwen3:14b"
    assert not result.repaired and not result.escalated
    assert client.calls[0][2]["temperature"] == 0.0
    assert isinstance(client.calls[0][2]["format"], dict)
    events = [e for e in list_events(tmp_path / "brain.sqlite", run_id="RUN-1")
              if e["event_type"] == "qwen_attempt"]
    assert len(events) == 1
    assert set(events[0]["payload"]) >= {"model", "duration_seconds", "prompt_hash",
                                         "response_hash", "validator_ok", "validator_reasons"}


def test_exactly_one_14b_repair_then_success():
    client = StubClient([invalid_payload(), valid_payload()])
    result = qwen_call("Extract", evidence(), expected_research_id="RQ-test", client=client)
    assert result.repaired and not result.escalated
    assert [call[1] for call in client.calls] == ["qwen3:14b", "qwen3:14b"]
    assert "Validator failures" in client.calls[1][0]


def test_failed_repair_escalates_once_to_27b():
    client = StubClient([invalid_payload(), invalid_payload(), valid_payload()])
    result = qwen_call("Extract", evidence(), expected_research_id="RQ-test", client=client)
    assert result.repaired and result.escalated
    assert result.model_used == "qwen3.8:27b"
    assert [call[1] for call in client.calls] == ["qwen3:14b", "qwen3:14b", "qwen3.8:27b"]


def test_final_invalid_response_fails_closed_without_loop():
    client = StubClient([invalid_payload(), invalid_payload(), invalid_payload()])
    with pytest.raises(QwenValidationError) as caught:
        qwen_call("Extract", evidence(), expected_research_id="RQ-test", client=client)
    assert len(caught.value.attempts) == 3
    assert [call[1] for call in client.calls] == ["qwen3:14b", "qwen3:14b", "qwen3.8:27b"]


class FailingClient:
    def __init__(self, error_factory):
        self.error_factory = error_factory
        self.calls = []

    def generate(self, prompt, model, **kwargs):
        self.calls.append((prompt, model, kwargs))
        raise self.error_factory()


@pytest.mark.parametrize(
    "error_factory, expected_reason",
    [
        (lambda: TimeoutError("timed out"), "TimeoutError: timed out"),
        (lambda: ConnectionError("connection lost"), "ConnectionError: connection lost"),
        (lambda: AttributeError("malformed envelope"), "AttributeError: malformed envelope"),
    ],
)
def test_generate_exceptions_are_audited_and_bounded(
    tmp_path, error_factory, expected_reason
):
    client = FailingClient(error_factory)
    db_path = tmp_path / "brain.sqlite"
    with pytest.raises(QwenValidationError) as caught:
        qwen_call(
            "Extract",
            evidence(),
            expected_research_id="RQ-test",
            client=client,
            db_path=db_path,
            run_id="RUN-error",
            task_id="TASK-error",
        )

    assert len(caught.value.attempts) == 3
    assert len(client.calls) == 3
    assert [attempt.model for attempt in caught.value.attempts] == [
        "qwen3:14b", "qwen3:14b", "qwen3.8:27b"
    ]
    assert all(attempt.prompt_hash for attempt in caught.value.attempts)
    assert all(attempt.response_hash == "" for attempt in caught.value.attempts)
    assert all(expected_reason in attempt.validator_reasons[0] for attempt in caught.value.attempts)
    events = [
        event for event in list_events(db_path, run_id="RUN-error")
        if event["event_type"] == "qwen_attempt"
    ]
    assert len(events) == 3
    assert all(event["payload"]["response_hash"] == "" for event in events)
    assert all(event["payload"]["validator_ok"] is False for event in events)

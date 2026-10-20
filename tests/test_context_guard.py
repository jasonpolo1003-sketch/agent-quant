"""Extraction prompts must fit the model's context, or fail closed.

Both Scout runs before this guard existed had every prompt silently cut by
Ollama to ``num_ctx // 2 + 2`` tokens, keeping only the tail: the models never
saw the instruction, the question or most of the sources. These tests pin the
three layers that now prevent that -- one source per extraction call, an
explicit context with server-side truncation disabled, and client-side checks
that hold whatever the server does -- and that a context failure stops the
ladder rather than feeding a longer prompt to the next attempt.
"""

import hashlib
import io
import json
import time
import urllib.error
from copy import deepcopy

import pytest
from test_candidate_list_lane import (  # noqa: F401  (fixtures used by name)
    URLS,
    clean_handlers,
    dispatch_list,
    new_question,
    project,
    question_state,
    write_list,
)
from test_discovery_handler import PAGE_BODY
from test_failed_run_provenance import _receipt_payload

from quant_brain.discovery.live_discovery import DiscoveryDeadlineExceeded, LiveDiscoveryBackend
from quant_brain.llm import ollama_client
from quant_brain.llm.ollama_client import ContextOverflowError, OllamaResponse
from quant_brain.llm.qwen_call import (
    EXTRACTION_NUM_CTX,
    EXTRACTION_NUM_PREDICT,
    EXTRACTION_TIMEOUT,
    PROMPT_TOKEN_BUDGET,
    ContextBudgetError,
    QwenValidationError,
    estimate_prompt_tokens,
    qwen_call,
)
from quant_brain.ops.events import list_events
from quant_brain.research.executor import _merge_extractions

# Verbatim from Ollama 0.34.3 when a prompt exceeds num_ctx with truncate=false.
SERVER_OVERFLOW_BODY = (
    '{"error":"{\\"error\\":{\\"code\\":400,\\"message\\":\\"request (3192 tokens) exceeds '
    'the available context size (2048 tokens), try increasing it\\",\\"type\\":'
    '\\"exceed_context_size_error\\",\\"n_prompt_tokens\\":3192,\\"n_ctx\\":2048}}"}'
)


# --- the client: explicit context, no silent truncation ------------------------


def _fake_post(response):
    captured = {}

    def fake(path, payload, host, timeout):
        captured.update(path=path, payload=payload, timeout=timeout)
        return response

    return fake, captured


def _generate(**overrides):
    kwargs = {"num_ctx": 4096, "num_predict": 512, "prompt_token_budget": 3000}
    kwargs.update(overrides)
    return ollama_client.generate("prompt", "qwen3:14b", **kwargs)


def test_every_generate_call_declares_its_context_and_disables_truncation(monkeypatch):
    fake, captured = _fake_post({"response": "{}", "prompt_eval_count": 40, "done_reason": "stop"})
    monkeypatch.setattr(ollama_client, "_post", fake)

    response = _generate()

    assert captured["payload"]["options"]["num_ctx"] == 4096
    assert captured["payload"]["options"]["num_predict"] == 512
    # Must be the boolean False: an absent flag means the server may truncate.
    assert captured["payload"]["truncate"] is False
    assert captured["payload"]["shift"] is False
    assert response.prompt_eval_count == 40
    assert response.num_ctx == 4096


def test_generate_cannot_be_called_without_a_context_window():
    with pytest.raises(TypeError):
        ollama_client.generate("prompt", "qwen3:14b")  # type: ignore[call-arg]


def test_the_silent_truncation_signature_is_refused(monkeypatch):
    # Exactly what the E3 run looked like: num_ctx 4096 cut every prompt to 2050.
    fake, _ = _fake_post({"response": "{}", "prompt_eval_count": 2050, "done_reason": "stop"})
    monkeypatch.setattr(ollama_client, "_post", fake)

    with pytest.raises(ContextOverflowError, match="silent-truncation"):
        _generate(prompt_token_budget=None)


def test_a_response_that_cannot_show_its_prompt_was_read_is_refused(monkeypatch):
    fake, _ = _fake_post({"response": "{}", "done_reason": "stop"})
    monkeypatch.setattr(ollama_client, "_post", fake)

    with pytest.raises(ContextOverflowError, match="no prompt_eval_count"):
        _generate()


def test_a_prompt_over_the_comfort_budget_is_refused_after_the_fact(monkeypatch):
    fake, _ = _fake_post({"response": "{}", "prompt_eval_count": 3001, "done_reason": "stop"})
    monkeypatch.setattr(ollama_client, "_post", fake)

    with pytest.raises(ContextOverflowError, match="above the 3000-token budget"):
        _generate()


def test_an_output_cut_at_the_limit_is_refused(monkeypatch):
    fake, _ = _fake_post({"response": '{"a": 1', "prompt_eval_count": 40, "done_reason": "length"})
    monkeypatch.setattr(ollama_client, "_post", fake)

    with pytest.raises(ContextOverflowError, match="done_reason=length"):
        _generate()


def test_the_servers_own_overflow_refusal_becomes_a_context_error(monkeypatch):
    def refuse(request, timeout):
        raise urllib.error.HTTPError(
            request.full_url, 400, "Bad Request", {}, io.BytesIO(SERVER_OVERFLOW_BODY.encode())
        )

    monkeypatch.setattr(ollama_client.urllib.request, "urlopen", refuse)

    with pytest.raises(ContextOverflowError, match="exceeds the available context size"):
        _generate()


def test_other_http_errors_stay_ordinary_client_errors(monkeypatch):
    def fail(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 500, "boom", {}, io.BytesIO(b"model crashed"))

    monkeypatch.setattr(ollama_client.urllib.request, "urlopen", fail)

    with pytest.raises(ollama_client.OllamaError) as caught:
        _generate()
    assert not isinstance(caught.value, ContextOverflowError)


# --- the ladder: a context failure stops it ------------------------------------


def evidence(snapshot="Exact passage. RSI below 30."):
    return [{
        "source_id": "S1", "title": "Study", "url_or_citation": "https://example.test/study",
        "source_quality": "primary", "snapshot_text": snapshot,
    }]


def valid_payload():
    return {
        "research_id": "RQ-test", "status": "raw_saved",
        "sources": [{
            "source_id": "S1", "title": "Study", "source_type": "paper",
            "url_or_citation": "https://example.test/study", "main_claim": "RSI below 30.",
            "evidence": "Exact passage.", "possible_strategy_rule": "",
            "risks": ["Caveat"], "confidence": "medium", "source_quality": "primary",
            "asset_classes": ["equity"], "data_required": ["daily close"],
            "data_access": "available-now", "mvp_testable": False,
        }], "open_questions": [], "curator_recommendation": "needs_more_work",
    }


class Client:
    def __init__(self, outcomes):
        self.outcomes = iter(outcomes)
        self.calls = []

    def generate(self, prompt, model, **kwargs):
        self.calls.append((prompt, model, kwargs))
        outcome = next(self.outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        text = json.dumps(outcome)
        return OllamaResponse(text, model, 0.1, hashlib.sha256(prompt.encode()).hexdigest(),
                              hashlib.sha256(text.encode()).hexdigest(), prompt_eval_count=50)


def oversize_prompt():
    return "x" * ((PROMPT_TOKEN_BUDGET + 1) * 4)


def test_an_oversize_prompt_is_refused_before_the_model_is_called(tmp_path):
    client = Client([])
    db_path = tmp_path / "brain.sqlite"

    with pytest.raises(ContextBudgetError, match="context: prompt needs") as caught:
        qwen_call(oversize_prompt(), evidence(), expected_research_id="RQ-test", client=client,
                  db_path=db_path, run_id="RUN-big", task_id="TASK-big")

    assert client.calls == []
    assert isinstance(caught.value, QwenValidationError)  # every fail-closed path still applies
    assert len(caught.value.attempts) == 1
    [event] = [e for e in list_events(db_path, run_id="RUN-big") if e["event_type"] == "qwen_attempt"]
    assert event["payload"]["validator_ok"] is False
    assert event["payload"]["source_ids"] == ["S1"]
    assert event["payload"]["num_ctx"] == EXTRACTION_NUM_CTX
    assert event["payload"]["estimated_prompt_tokens"] > PROMPT_TOKEN_BUDGET
    assert event["payload"]["prompt_eval_count"] is None


def test_a_context_overflow_from_the_model_stops_the_ladder_at_once():
    client = Client([ContextOverflowError("context: cut"), valid_payload(), valid_payload()])

    with pytest.raises(ContextBudgetError, match="context: cut") as caught:
        qwen_call("Extract", evidence(), expected_research_id="RQ-test", client=client)

    # No repair and no escalation: both prompts would be longer still.
    assert [call[1] for call in client.calls] == ["qwen3:14b"]
    assert len(caught.value.attempts) == 1


def test_a_repair_prompt_that_outgrows_the_budget_is_refused_before_sending():
    # The first prompt fits; the repair adds the previous response and the
    # validator's reasons, which pushes it over.
    base = "y" * ((PROMPT_TOKEN_BUDGET - 200) * 4)
    invalid = deepcopy(valid_payload())
    invalid["sources"][0]["main_claim"] = "z" * 4000
    invalid["sources"][0]["evidence"] = "not in the snapshot"
    client = Client([invalid])

    with pytest.raises(ContextBudgetError, match="context: prompt needs"):
        qwen_call(base, evidence(), expected_research_id="RQ-test", client=client)

    assert len(client.calls) == 1


def test_qwen_call_sends_the_extraction_budget_and_timeout():
    client = Client([valid_payload()])

    result = qwen_call("Extract", evidence(), expected_research_id="RQ-test", client=client)

    kwargs = client.calls[0][2]
    assert kwargs["num_ctx"] == EXTRACTION_NUM_CTX
    assert kwargs["num_predict"] == EXTRACTION_NUM_PREDICT
    assert kwargs["prompt_token_budget"] == PROMPT_TOKEN_BUDGET
    assert kwargs["timeout"] == EXTRACTION_TIMEOUT
    assert not result.repaired


def test_qwen_call_refuses_to_start_after_the_run_deadline():
    client = Client([])

    with pytest.raises(QwenValidationError, match="wall-clock"):
        qwen_call(
            "Extract",
            evidence(),
            expected_research_id="RQ-test",
            client=client,
            deadline=time.monotonic() - 1,
        )

    assert client.calls == []


def test_qwen_call_limits_the_http_timeout_to_the_run_deadline():
    client = Client([valid_payload()])

    qwen_call(
        "Extract",
        evidence(),
        expected_research_id="RQ-test",
        client=client,
        deadline=time.monotonic() + 5,
    )

    timeout = client.calls[0][2]["timeout"]
    assert 0 < timeout <= 5


def test_live_discovery_refuses_an_expired_run_deadline_before_search(tmp_path):
    calls = []

    def search(_question, _family, *, limit):
        calls.append(limit)
        return []

    backend = LiveDiscoveryBackend(
        search_fn=search,
        fetch_fn=lambda _url: {"content": "unused"},
    )
    with pytest.raises(DiscoveryDeadlineExceeded, match="wall-clock"):
        backend.discover(
            "question",
            None,
            project_root=tmp_path,
            deadline=time.monotonic() - 1,
        )

    assert calls == []


def test_the_budget_leaves_room_for_the_output_inside_the_window():
    assert PROMPT_TOKEN_BUDGET + EXTRACTION_NUM_PREDICT <= int(EXTRACTION_NUM_CTX * 0.8)
    # Above the silent-truncation length the server refuses (truncate=false) and
    # the response's own count is checked, so the budget may exceed it.
    assert estimate_prompt_tokens("abcd" * 10) == 10


# --- the executor: one source per call, bounded, all or nothing ----------------


def big_body(url, kilobytes):
    """A snapshot body of roughly `kilobytes` KB that passes the content floor."""
    repeats = kilobytes * 1024 // (len(PAGE_BODY) + 1) + 1
    return f"Page {url}.\n" + "\n".join([PAGE_BODY] * repeats)


class SizedFetcher:
    def __init__(self, sizes):
        self.sizes = sizes
        self.calls = []

    def __call__(self, url):
        self.calls.append(url)
        return {"url": url, "content": big_body(url, self.sizes.get(url, 30)),
                "channel": "web", "backend": "fixture"}


def recording_runner(monkeypatch, research_id, *, ground=True):
    calls = []

    def runner(prompt, evidence, *, expected_research_id, **kwargs):
        calls.append({"prompt": prompt, "evidence": evidence, "deadline": kwargs.get("deadline")})
        sources = [
            {
                "source_id": item["source_id"], "title": item["title"], "source_type": "web",
                "url_or_citation": item["url_or_citation"],
                "main_claim": "Exact evidence passage." if ground else "RSI(2) exits above 70.",
                "evidence": "Exact evidence passage." if ground else "RSI(2) exits above 70.",
                "possible_strategy_rule": "", "risks": ["Requires review."],
                "confidence": "low", "source_quality": item["source_quality"],
                "asset_classes": ["equity"], "data_required": ["daily close"],
                "data_access": "available-now", "mvp_testable": False,
            }
            for item in evidence
        ]
        from types import SimpleNamespace

        return SimpleNamespace(
            output={"research_id": expected_research_id, "status": "raw_saved",
                    "sources": sources, "open_questions": [],
                    "curator_recommendation": "needs_more_work"},
            model_used="qwen3:14b", repaired=False, escalated=False,
        )

    monkeypatch.setattr("quant_brain.llm.qwen_call.qwen_call", runner)
    return calls


def test_five_sources_too_large_together_are_extracted_one_per_call(project, monkeypatch):  # noqa: F811
    root, db_path = project
    research_id = new_question(db_path)
    urls = list(URLS[:2]) + list(URLS[3:6])  # five distinct works the classifier accepts
    relative = write_list(root, research_id, urls)
    calls = recording_runner(monkeypatch, research_id)

    result = dispatch_list(project, relative, SizedFetcher({}), research_id=research_id)

    assert result.status == "completed"
    assert [len(call["evidence"]) for call in calls] == [1] * 5
    assert [call["evidence"][0]["source_id"] for call in calls] == ["S1", "S2", "S3", "S4", "S5"]
    assert isinstance(calls[0]["deadline"], float)
    assert {call["deadline"] for call in calls} == {calls[0]["deadline"]}
    total = sum(estimate_prompt_tokens(call["prompt"]) for call in calls)
    assert total > PROMPT_TOKEN_BUDGET  # one prompt holding all five could not have fit
    for call in calls:
        item = call["evidence"][0]
        assert estimate_prompt_tokens(call["prompt"]) <= PROMPT_TOKEN_BUDGET
        # Only this source's snapshot is in its prompt, verbatim, not JSON-escaped.
        assert item["snapshot_text"] in call["prompt"]
        others = [c["evidence"][0] for c in calls if c is not call]
        assert all(f"Page {o['url_or_citation']}." not in call["prompt"] for o in others)
    note = (root / result.outputs[0]).read_text(encoding="utf-8")
    payload = json.loads(note.split("```json")[-1].split("```")[0])
    assert [s["source_id"] for s in payload["sources"]] == ["S1", "S2", "S3", "S4", "S5"]


def test_one_source_too_large_fails_the_run_before_any_model_call(project, monkeypatch):  # noqa: F811
    root, db_path = project
    research_id = new_question(db_path)
    urls = list(URLS[:3])
    relative = write_list(root, research_id, urls)
    calls = recording_runner(monkeypatch, research_id)

    # Ranking decides the S-number, so the message is matched on the URL.
    with pytest.raises(ContextBudgetError, match=rf"context: .*source S\d: {urls[1]}"):
        dispatch_list(project, relative, SizedFetcher({urls[1]: 80}), research_id=research_id,
                      run_id="RUN-oversize")

    assert calls == []
    receipt = _receipt_payload(root)
    assert receipt["stage"] == "qwen_extract"
    assert receipt["error_type"] == "ContextBudgetError"
    assert question_state(db_path, research_id) == ("queued", None)


def test_the_merged_payload_must_pass_whole_bundle_validation(project, monkeypatch):  # noqa: F811
    # The runner stands in for the ladder and returns ungrounded evidence, so
    # only the final whole-bundle validation stands between it and a raw note.
    root, db_path = project
    research_id = new_question(db_path)
    relative = write_list(root, research_id, list(URLS[:3]))
    recording_runner(monkeypatch, research_id, ground=False)

    with pytest.raises(QwenValidationError, match="merge: quote:S1"):
        dispatch_list(project, relative, SizedFetcher({}), research_id=research_id,
                      run_id="RUN-merge")

    assert question_state(db_path, research_id) == ("queued", None)
    assert not list((root / "brain" / "00_Inbox" / "Raw_Research").glob("*.md"))


def test_merge_keeps_source_order_and_only_a_unanimous_recommendation():
    one = {"sources": [{"source_id": "S1"}], "open_questions": ["a", "b"],
           "curator_recommendation": "promote_source"}
    two = {"sources": [{"source_id": "S2"}], "open_questions": ["b", "c"],
           "curator_recommendation": "promote_source"}
    three = {"sources": [{"source_id": "S3"}], "open_questions": [],
             "curator_recommendation": "rejected"}

    agreed = _merge_extractions("RQ-x", [one, two])
    split = _merge_extractions("RQ-x", [one, two, three])

    assert [s["source_id"] for s in split["sources"]] == ["S1", "S2", "S3"]
    assert split["open_questions"] == ["a", "b", "c"]
    assert agreed["curator_recommendation"] == "promote_source"
    assert split["curator_recommendation"] == "needs_more_work"
    assert split["research_id"] == "RQ-x" and split["status"] == "raw_saved"

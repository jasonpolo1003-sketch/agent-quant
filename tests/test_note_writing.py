"""The raw note is written from the validated, normalized payload.

E5 (RUN-871299ea31) validated every extraction and then failed at write_note:
the model had legally omitted the optional ``possible_strategy_rule`` (schema
default ""), validation normalized it, but the note writer read the raw model
output. These tests run the whole validation-to-note path, first on synthetic
pages and then on the five snapshots E5 actually fetched (committed in
8265dca). Model responses are scripted; no model is called.
"""

import json
import re

import pytest
from test_candidate_list_lane import (  # noqa: F401  (fixtures used by name)
    clean_handlers,
    dispatch_list,
    new_question,
    project,
    write_list,
)
from test_windowing import URLS, WindowedFetcher

from quant_brain.config import PROJECT_ROOT
from quant_brain.curation.executor import extract_scout_json
from quant_brain.llm import ollama_client
from quant_brain.llm.ollama_client import OllamaResponse
from quant_brain.research.schema import validate_raw_research_note

_WINDOW_RE = re.compile(r"<<<BEGIN WINDOW (S\d+-W\d+)>>>\n(.*?)\n<<<END WINDOW \1>>>", re.S)
_SNAPSHOT_RE = re.compile(r"<<<BEGIN SNAPSHOT (S\d+)>>>\n(.*?)\n<<<END SNAPSHOT \1>>>", re.S)
_METADATA_RE = re.compile(r"Source metadata:\n(\{.*?\n\})\n", re.S)
OPTIONAL = ("possible_strategy_rule",)


def _sha(text):
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# The harness writes this front matter into every snapshot. It is not the
# source's content, so a well-behaved model never quotes it (and this test's
# assertions would reject a note that did).
_FRONT_MATTER = ("url:", "title:", "channel:", "backend:", "captured_at:", "content_hash:",
                 "url_hash:")


def _quote(text, needle):
    """A whole line of fetched content in `text` that contains `needle`, or None."""
    for line in text.splitlines():
        line = line.strip()
        if line.startswith(_FRONT_MATTER):
            continue
        if needle in line and 20 <= len(line) <= 300:
            return line
    return None


class OmittingModel:
    """Grounded answers that leave out every optional field, as E5's did."""

    def __init__(self, needle):
        self.needle = needle

    def __call__(self, prompt, model, **kwargs):
        research_id = re.search(r"Research ID: (\S+)", prompt).group(1)
        meta = json.loads(_METADATA_RE.search(prompt).group(1))
        window = _WINDOW_RE.search(prompt)
        text = window.group(2) if window else _SNAPSHOT_RE.search(prompt).group(2)
        quote = _quote(text, self.needle) or _quote(text, " ")
        source = {
            **meta, "source_type": "web", "main_claim": quote, "evidence": [quote],
            "risks": ["Single source."], "confidence": "low", "asset_classes": ["equity"],
            "data_required": ["daily close"], "data_access": "available-now",
            "mvp_testable": False,
        }
        for field in OPTIONAL:
            source.pop(field, None)
        if window is None:
            payload = {"research_id": research_id, "status": "raw_saved", "sources": [source],
                       "open_questions": [], "curator_recommendation": "needs_more_work"}
        elif _quote(text, self.needle):
            payload = {"research_id": research_id, "source_id": meta["source_id"],
                       "window_id": window.group(1), "outcome": "evidence", "source": source,
                       "open_questions": []}
        else:
            payload = {"research_id": research_id, "source_id": meta["source_id"],
                       "window_id": window.group(1), "outcome": "no_relevant_evidence",
                       "source": None, "open_questions": []}
        body = json.dumps(payload, ensure_ascii=False)
        return OllamaResponse(body, model, 0.01, _sha(prompt), _sha(body), prompt_eval_count=100)


def _note(root, result):
    return root / result.outputs[0]


def _assert_note_is_valid_and_normalized(path):
    validated = validate_raw_research_note(path)  # the curator's own contract
    assert extract_scout_json(path) == validated  # already normalized: nothing to fill in
    for source in validated["sources"]:
        assert source["possible_strategy_rule"] == ""
    return validated


def test_an_omitted_optional_field_is_written_as_its_validated_default(project, monkeypatch):  # noqa: F811
    root, db_path = project
    research_id = new_question(db_path)
    relative = write_list(root, research_id, list(URLS[:3]))
    monkeypatch.setattr(ollama_client, "generate", OmittingModel("Exact evidence passage."))

    result = dispatch_list(project, relative, WindowedFetcher(set()), research_id=research_id,
                           run_id="RUN-omit")

    assert result.status == "completed"
    payload = _assert_note_is_valid_and_normalized(_note(root, result))
    assert len(payload["sources"]) == 3
    note = _note(root, result).read_text(encoding="utf-8")
    assert "- Possible strategy rule: \n" in note


def test_a_windowed_source_with_omitted_fields_reaches_the_note(project, monkeypatch):  # noqa: F811
    root, db_path = project
    research_id = new_question(db_path)
    relative = write_list(root, research_id, list(URLS[:3]))
    monkeypatch.setattr(ollama_client, "generate", OmittingModel("Pagonidis exits"))

    result = dispatch_list(project, relative, WindowedFetcher({URLS[1]}), research_id=research_id,
                           run_id="RUN-omit-window")

    assert result.status == "completed"
    payload = _assert_note_is_valid_and_normalized(_note(root, result))
    assert "## Extraction Windows" in _note(root, result).read_text(encoding="utf-8")
    assert len(payload["sources"]) == 3


# --- the same path on the pages E5 actually fetched ---------------------------------

E5_RECEIPT = PROJECT_ROOT / "brain/00_Inbox/Failed_Runs/RUN-871299ea31.md"


def _e5_candidates():
    body = E5_RECEIPT.read_text(encoding="utf-8")
    return json.loads(body.split("```json")[1].split("```")[0])["accepted_candidates"]


def _snapshot_body(path):
    """The fetched content a snapshot recorded (text after its front matter)."""
    text = path.read_text(encoding="utf-8")
    return text.split("\n---\n", 1)[1].removeprefix("\n")


class SavedPages:
    """Serves E5's committed snapshot bodies instead of fetching."""

    def __init__(self, bodies):
        self.bodies = bodies

    def __call__(self, url):
        return {"url": url, "content": self.bodies[url], "channel": "web", "backend": "fixture"}


@pytest.mark.skipif(not E5_RECEIPT.is_file(), reason="E5 evidence not present")
def test_e5s_saved_pages_run_through_validation_to_a_valid_note(project, monkeypatch):  # noqa: F811
    from quant_brain.research.receipts import resolve_recorded_snapshot

    root, db_path = project
    candidates = _e5_candidates()
    bodies = {}
    for candidate in candidates:
        path = resolve_recorded_snapshot(PROJECT_ROOT, "RUN-871299ea31", candidate["snapshot_path"])
        body = _snapshot_body(path)
        assert _sha(body) == candidate["snapshot_sha256"]  # exactly what E5 fetched
        bodies[candidate["url"]] = body
    research_id = new_question(db_path)
    relative = write_list(root, research_id, [c["url"] for c in candidates])
    monkeypatch.setattr(ollama_client, "generate", OmittingModel("RSI"))

    result = dispatch_list(project, relative, SavedPages(bodies), research_id=research_id,
                           run_id="RUN-e5-saved")

    assert result.status == "completed"
    payload = _assert_note_is_valid_and_normalized(_note(root, result))
    assert sorted(s["url_or_citation"] for s in payload["sources"]) == sorted(bodies)
    for source in payload["sources"]:
        for quote in source["evidence"]:
            assert quote in bodies[source["url_or_citation"]].replace("\r\n", "\n")


class DisagreeingModel(OmittingModel):
    """S1 asks to promote and raises a question; the others do not."""

    def __call__(self, prompt, model, **kwargs):
        response = super().__call__(prompt, model, **kwargs)
        payload = json.loads(response.text)
        if payload.get("sources") and payload["sources"][0]["source_id"] == "S1":
            payload["open_questions"] = ["Which exit threshold does the page test?"]
            payload["curator_recommendation"] = "promote_source"
        body = json.dumps(payload, ensure_ascii=False)
        return OllamaResponse(body, model, 0.01, _sha(prompt), _sha(body), prompt_eval_count=100)


def test_the_note_json_is_exactly_the_validated_payload(project, monkeypatch):  # noqa: F811
    """Review finding: sources came from the validated payload, but the note's
    questions and recommendation were template constants -- a note could say
    promote_source when validation ran against needs_more_work."""
    from quant_brain.llm import validators

    captured = []
    real = validators.validate_research_output

    def spy(payload, evidence, **kwargs):
        verdict = real(payload, evidence, **kwargs)
        if len(evidence) > 1:  # the merged, whole-bundle validation
            captured.append(verdict.normalized)
        return verdict

    monkeypatch.setattr(validators, "validate_research_output", spy)
    root, db_path = project
    research_id = new_question(db_path)
    relative = write_list(root, research_id, list(URLS[:3]))
    monkeypatch.setattr(ollama_client, "generate", DisagreeingModel("Exact evidence passage."))

    result = dispatch_list(project, relative, WindowedFetcher(set()), research_id=research_id,
                           run_id="RUN-exact")

    assert result.status == "completed"
    [validated] = captured
    written = extract_scout_json(_note(root, result))
    assert written == validated
    assert written["curator_recommendation"] == "needs_more_work"
    assert written["open_questions"] == ["Which exit threshold does the page test?"]

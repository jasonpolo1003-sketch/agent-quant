"""Models and validators see the fetched content only, never the front matter.

Every snapshot begins with front matter the harness writes itself (url, title,
channel, backend, captured_at, content and URL hashes). It is not the source's
text, but the model was shown it and quotes were checked against it: a quote of
``backend: jina`` passed as exact evidence, and digits from the timestamp and
hashes made invented numbers look grounded. Model-independent: this is about
what any extraction model is given and what its output is checked against.
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
from test_failed_run_provenance import _receipt_payload
from test_windowing import NEEDLE, URLS, FakeOllama, WindowedFetcher

from quant_brain.config import PROJECT_ROOT
from quant_brain.discovery.live_discovery import save_source_snapshot, snapshot_content
from quant_brain.llm import ollama_client
from quant_brain.llm.qwen_call import QwenValidationError
from quant_brain.llm.validators import validate_research_output
from quant_brain.research.receipts import verify_receipt

CONNORS = PROJECT_ROOT / "brain/00_Inbox/Source_Snapshots/2026-09-28/f57de4fc3101-1bb9664e.md"


@pytest.mark.parametrize(
    "fetched",
    ["First line.\nSecond line with 42.\n", "No final newline", "Trailing spaces.   \n\n\n"],
    ids=["newline", "no-newline", "trailing-whitespace"],
)
def test_snapshot_content_is_exactly_what_was_fetched(tmp_path, fetched):
    """Stored verbatim, so its recorded content hash can always be re-verified."""
    import hashlib

    relative = save_source_snapshot(tmp_path, url="https://example.com/a", content=fetched)
    text = (tmp_path / relative).read_text(encoding="utf-8")
    content_hash = next(
        line.split(": ", 1)[1] for line in text.splitlines() if line.startswith("content_hash:")
    )

    assert snapshot_content(text) == fetched
    assert hashlib.sha256(snapshot_content(text).encode("utf-8")).hexdigest() == content_hash
    assert "captured_at" not in snapshot_content(text)


def test_snapshot_content_refuses_text_without_front_matter():
    with pytest.raises(ValueError):
        snapshot_content("no front matter here")


def _item(snapshot_text):
    return [{"source_id": "S1", "title": "Connors", "url_or_citation": "https://x.test",
             "source_quality": "discovery-only", "snapshot_text": snapshot_text}]


def _payload(**source):
    base = {
        "source_id": "S1", "title": "Connors", "source_type": "web",
        "url_or_citation": "https://x.test", "main_claim": "Mean reversion.",
        "evidence": "Mean reversion", "possible_strategy_rule": "", "risks": ["r"],
        "confidence": "low", "source_quality": "discovery-only", "asset_classes": ["equity"],
        "data_required": ["daily close"], "data_access": "available-now", "mvp_testable": False,
    }
    return {"research_id": "RQ-x", "status": "raw_saved", "sources": [{**base, **source}],
            "open_questions": [], "curator_recommendation": "needs_more_work"}


@pytest.mark.skipif(not CONNORS.is_file(), reason="preserved E4 snapshot not present")
@pytest.mark.parametrize("claim", ["Uses a 28-day lookback.", "Tested over 16 years."])
def test_on_the_preserved_snapshot_front_matter_digits_no_longer_ground_numbers(claim):
    """The reviewer's demonstration: grounded against the whole file, not the content."""
    full = CONNORS.read_text(encoding="utf-8")
    content = snapshot_content(full)
    number = re.search(r"\d+", claim).group()
    assert number in full.split("\n---\n", 1)[0] and number not in content

    whole_file = validate_research_output(_payload(main_claim=claim), _item(full))
    content_only = validate_research_output(_payload(main_claim=claim), _item(content))

    assert whole_file.ok  # the weakness, as it was
    assert not content_only.ok
    assert any(r.startswith("grounding:S1:main_claim") for r in content_only.reasons)


class QuotesFrontMatter(FakeOllama):
    """A model that 'quotes' the harness's own metadata for a normal source."""

    def __call__(self, prompt, model, **kwargs):
        response = super().__call__(prompt, model, **kwargs)
        payload = json.loads(response.text)
        if payload.get("sources") and payload["sources"][0]["source_id"] == "S1":
            payload["sources"][0]["evidence"] = "backend: fixture"
        body = json.dumps(payload)
        from test_windowing import _sha

        return type(response)(body, model, 0.01, _sha(prompt), _sha(body), prompt_eval_count=100)


def test_no_prompt_shows_the_front_matter_and_quoting_it_fails(project, monkeypatch):  # noqa: F811
    root, db_path = project
    research_id = new_question(db_path)
    relative = write_list(root, research_id, list(URLS[:3]))
    fake = QuotesFrontMatter()
    monkeypatch.setattr(ollama_client, "generate", fake)

    with pytest.raises(QwenValidationError, match="quote:S1"):
        dispatch_list(project, relative, WindowedFetcher({URLS[1]}), research_id=research_id,
                      run_id="RUN-meta")

    assert fake.prompts
    for prompt in fake.prompts:
        assert "captured_at:" not in prompt and "content_hash:" not in prompt


def test_a_new_windowed_run_records_and_verifies_content_offsets(project, monkeypatch):  # noqa: F811
    root, db_path = project
    research_id = new_question(db_path)
    relative = write_list(root, research_id, list(URLS[:3]))
    monkeypatch.setattr(ollama_client, "generate", FakeOllama(bad_window="-W02"))

    with pytest.raises(QwenValidationError):
        dispatch_list(project, relative, WindowedFetcher({URLS[1]}), research_id=research_id,
                      run_id="RUN-content")

    [manifest] = _receipt_payload(root)["extraction_windows"]
    assert "front matter excluded" in manifest["snapshot_text_derivation"]
    receipt = root / "brain/00_Inbox/Failed_Runs/RUN-content.md"
    assert verify_receipt(root, receipt).problems == []
    assert NEEDLE  # the windowed page's needle is in its content, not its metadata


def test_carriage_returns_are_canonicalised_once_and_the_hash_still_verifies(tmp_path):
    """Review finding: text-mode writing plus universal-newline reading changed
    content holding \r, so its recorded hash could not re-verify."""
    import hashlib

    from quant_brain.discovery.live_discovery import canonical_content

    cr = chr(13)
    fetched = f"line one{cr}\nline two{cr}three\n"
    relative = save_source_snapshot(tmp_path, url="https://example.com/cr", content=fetched)
    content = snapshot_content((tmp_path / relative).read_text(encoding="utf-8"))

    assert content == "line one\nline two\nthree\n" == canonical_content(fetched)
    assert hashlib.sha256(content.encode("utf-8")).hexdigest() == hashlib.sha256(
        canonical_content(fetched).encode("utf-8")
    ).hexdigest()


@pytest.mark.parametrize("field", ["title", "url"])
def test_a_newline_in_a_front_matter_value_cannot_leak_metadata_into_content(tmp_path, field):
    """Review finding: an unescaped title such as 'Evil\n---\nx' ended the front
    matter early and exposed captured_at and the hashes as 'content'."""
    injected = "Evil\n---\nx"
    kwargs = {"url": "https://example.com/a", "title": "T"}
    kwargs[field] = kwargs[field] + injected
    relative = save_source_snapshot(tmp_path, content="Real body.\n", **kwargs)

    content = snapshot_content((tmp_path / relative).read_text(encoding="utf-8"))

    assert content == "Real body.\n"

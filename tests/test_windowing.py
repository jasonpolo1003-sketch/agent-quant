"""A source too large for one prompt is read in deterministic windows.

The NAAIM snapshot (56,018 bytes, ~31k tokens) cannot fit the per-call budget,
and the committed candidate list may not be edited. These tests pin the
windowing path (PROP-006): windows are deterministic, ordered, overlapping and
hash-addressed; every window gets an explicit validated outcome, including an
honest "no relevant evidence"; quotations are checked against both the window
the model saw and the immutable full snapshot; the merge invents nothing; any
failed or unaccounted window fails the run; and sources that already fit take
the unchanged single-prompt path.
"""

import hashlib
import json
import re
import time
from itertools import pairwise
from types import SimpleNamespace

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
from test_context_guard import Client, big_body
from test_failed_run_provenance import _receipt_payload

from quant_brain.db.init_db import init_database
from quant_brain.llm import ollama_client
from quant_brain.llm.ollama_client import OllamaResponse
from quant_brain.llm.qwen_call import (
    ContextBudgetError,
    QwenValidationError,
    RunBudgetError,
    qwen_call,
)
from quant_brain.llm.validators import ValidationResult
from quant_brain.ops.events import list_events
from quant_brain.research import executor
from quant_brain.research.windowing import (
    MAX_WINDOWS_PER_SOURCE,
    WINDOW_MAX_BYTES,
    WINDOW_OVERLAP_BYTES,
    WindowMergeError,
    WindowOutcome,
    merge_window_outcomes,
    plan_windows,
    validate_window_outcome,
    window_prompt,
)

NEEDLE = "Pagonidis exits the position when the close crosses above the five-day average."


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _bytes(text):
    return len(text.encode("utf-8"))


def mojibake_text(target_bytes):
    """Deterministic PDF-like text: short lines, non-ASCII, irregular spacing."""
    parts, size, i = [], 0, 0
    while size < target_bytes:
        line = (
            f"Ã¢â¬â€œ p.{i} RSI(2) Ã©tude  "
            f"ligne {i % 97}\n"
            if i % 3
            else f"word{i} " * 7 + "\n"
        )
        parts.append(line)
        size += _bytes(line)
        i += 1
    return "".join(parts)


# --- deterministic windows -------------------------------------------------------


def test_windows_are_deterministic_ordered_overlapping_and_hash_addressed():
    text = mojibake_text(56_018)

    windows = plan_windows(text, "S4")

    assert windows == plan_windows(text, "S4")
    assert [w.window_id for w in windows] == [f"S4-W{i:02d}" for i in range(1, len(windows) + 1)]
    assert [w.index for w in windows] == list(range(1, len(windows) + 1))
    assert {w.count for w in windows} == {len(windows)}
    assert windows[0].start == 0 and windows[-1].end == len(text)
    for w in windows:
        assert w.source_id == "S4"
        assert w.text_sha256 == _sha(text[w.start : w.end])
        assert w.text_of(text) == text[w.start : w.end]
        assert _bytes(text[w.start : w.end]) <= WINDOW_MAX_BYTES
    for prev, nxt in pairwise(windows):
        assert prev.start < nxt.start < prev.end < nxt.end  # ordered and overlapping
        assert _bytes(text[nxt.start : prev.end]) <= WINDOW_OVERLAP_BYTES


def test_a_naaim_sized_source_needs_a_bounded_number_of_windows():
    windows = plan_windows(mojibake_text(56_018), "S4")

    assert 7 <= len(windows) <= MAX_WINDOWS_PER_SOURCE


def test_every_passage_no_longer_than_the_overlap_lies_inside_one_window():
    text = "".join(f"w{i} é " if i % 5 else f"line{i}\n" for i in range(400))
    windows = plan_windows(text, "S1", max_bytes=200, overlap_bytes=40)
    assert len(windows) > 3

    for a in range(len(text)):
        b = a
        while b < len(text) and _bytes(text[a : b + 1]) <= 40:
            b += 1
        assert any(w.start <= a and b <= w.end for w in windows), (a, b)


@pytest.mark.parametrize(
    "text", ["x" * 30_000, "é" * 20_000, "\U0001f600" * 5_000], ids=["ascii", "latin", "emoji"]
)
def test_windowing_needs_no_whitespace_and_never_splits_a_character(text):
    windows = plan_windows(text, "S2")

    assert windows[0].start == 0 and windows[-1].end == len(text)
    for w in windows:
        assert _bytes(text[w.start : w.end]) <= WINDOW_MAX_BYTES
        assert text[w.start : w.end].encode("utf-8").decode("utf-8") == text[w.start : w.end]


def test_a_text_that_fits_is_one_window():
    windows = plan_windows("short text", "S1")

    assert [(w.start, w.end, w.count) for w in windows] == [(0, 10, 1)]


def test_the_overlap_must_be_smaller_than_a_window():
    with pytest.raises(ValueError):
        plan_windows("x" * 1000, "S1", max_bytes=100, overlap_bytes=100)


# --- one window's outcome -----------------------------------------------------------


def _full():
    return "Filler one.\n" * 30 + NEEDLE + "\n" + "Filler two.\n" * 30 + "Tail only passage.\n"


def _item(full=None):
    return {
        "source_id": "S4", "title": "NAAIM paper", "url_or_citation": URLS[3],
        "source_quality": "discovery-only", "snapshot_text": full if full is not None else _full(),
    }


def _windows(full=None):
    return plan_windows(full if full is not None else _full(), "S4", max_bytes=300, overlap_bytes=40)


def _window_with(needle):
    full = _full()
    return next(w for w in _windows(full) if needle in w.text_of(full))


def _window_without(needle):
    full = _full()
    return next(w for w in _windows(full) if needle not in w.text_of(full))


def _source(quote, **overrides):
    return {
        "source_id": "S4", "title": "NAAIM paper", "source_type": "paper",
        "url_or_citation": URLS[3], "main_claim": quote, "evidence": quote,
        "possible_strategy_rule": "", "risks": ["Single paper."], "confidence": "low",
        "source_quality": "discovery-only", "asset_classes": ["equity"],
        "data_required": ["daily close"], "data_access": "available-now",
        "mvp_testable": False, **overrides,
    }


def evidence_outcome(window, quote, **overrides):
    return {
        "research_id": "RQ-w", "source_id": window.source_id, "window_id": window.window_id,
        "outcome": "evidence", "source": _source(quote), "open_questions": [],
        "curator_recommendation": "needs_more_work", **overrides,
    }


def none_outcome(window, **overrides):
    return {
        "research_id": "RQ-w", "source_id": window.source_id, "window_id": window.window_id,
        "outcome": "no_relevant_evidence", "source": None, "open_questions": [],
        "curator_recommendation": None, **overrides,
    }


def check(payload, window):
    return validate_window_outcome(payload, _item(), window, expected_research_id="RQ-w")


def test_evidence_quoted_from_the_window_shown_is_accepted():
    window = _window_with(NEEDLE)

    verdict = check(evidence_outcome(window, NEEDLE), window)

    assert verdict.ok, verdict.reasons
    assert verdict.normalized["source"]["evidence"] == NEEDLE


def test_no_relevant_evidence_is_an_explicit_accepted_outcome():
    window = _window_without(NEEDLE)

    verdict = check(none_outcome(window), window)

    assert verdict.ok, verdict.reasons
    assert verdict.normalized["outcome"] == "no_relevant_evidence"


@pytest.mark.parametrize(
    "overrides",
    [
        {"source": _source("Filler one.")},
        {"open_questions": ["Is this relevant?"]},
        {"curator_recommendation": "needs_more_work"},
    ],
)
def test_a_no_evidence_outcome_cannot_carry_a_claim(overrides):
    window = _window_without(NEEDLE)

    assert not check(none_outcome(window, **overrides), window).ok


def test_an_evidence_outcome_needs_a_source_and_a_recommendation():
    window = _window_with(NEEDLE)

    assert not check(evidence_outcome(window, NEEDLE, source=None), window).ok
    assert not check(evidence_outcome(window, NEEDLE, curator_recommendation=None), window).ok


def test_a_quote_from_elsewhere_in_the_snapshot_is_refused_for_this_window():
    """Real text, wrong window: the model was not shown it, so it cannot cite it."""
    window = _window_without("Tail only passage.")

    verdict = check(evidence_outcome(window, "Tail only passage."), window)

    assert not verdict.ok
    assert any(reason.startswith("quote:S4") for reason in verdict.reasons)


@pytest.mark.parametrize(
    "overrides", [{"window_id": "S4-W99"}, {"source_id": "S5"}, {"research_id": "RQ-other"}]
)
def test_a_window_outcome_must_name_the_window_it_was_given(overrides):
    window = _window_with(NEEDLE)

    assert not check(evidence_outcome(window, NEEDLE, **overrides), window).ok


def test_a_window_whose_text_no_longer_matches_its_hash_is_refused():
    window = _window_with(NEEDLE)
    tampered = SimpleNamespace(**{**window.__dict__, "text_sha256": "0" * 64})
    tampered.text_of = window.text_of

    verdict = check(evidence_outcome(window, NEEDLE), tampered)

    assert not verdict.ok
    assert any("hash" in reason for reason in verdict.reasons)


def test_quotes_are_also_checked_against_the_full_snapshot(monkeypatch):
    """Second, independent check: the window text is a slice of the full text,
    so this can only fail if the slice was not what the model saw."""
    window = _window_with(NEEDLE)
    item = _item()
    shown = window.text_of(item["snapshot_text"])
    item["snapshot_text"] = item["snapshot_text"].replace(NEEDLE, "x" * len(NEEDLE))
    monkeypatch.setattr(type(window), "text_of", lambda self, full: shown)
    object.__setattr__(window, "text_sha256", _sha(shown))

    verdict = validate_window_outcome(
        evidence_outcome(window, NEEDLE), item, window, expected_research_id="RQ-w"
    )

    assert not verdict.ok
    assert any(reason.startswith("quote-full:S4") for reason in verdict.reasons)


# --- the deterministic merge --------------------------------------------------------


def test_the_merge_builds_one_record_without_inventing_anything():
    full = _full()
    windows = _windows(full)
    outcomes = [none_outcome(w) for w in windows]
    first, second = 1, len(windows) - 1
    outcomes[first] = evidence_outcome(
        windows[first], "Filler one.", curator_recommendation="promote_source",
        open_questions=["Which average?"],
    )
    outcomes[first]["source"].update(
        confidence="medium", mvp_testable=True, risks=["Single paper.", "PDF text."],
        data_access="available-later",
    )
    outcomes[second] = evidence_outcome(
        windows[second], "Tail only passage.", open_questions=["Which average?", "Costs?"]
    )
    outcomes[second]["source"]["evidence"] = ["Tail only passage.", "Filler one."]

    merged = merge_window_outcomes("RQ-w", _item(full), windows, outcomes)

    assert merged["research_id"] == "RQ-w" and merged["status"] == "raw_saved"
    [source] = merged["sources"]
    assert source["evidence"] == ["Filler one.", "Tail only passage."]
    assert source["main_claim"] == "Filler one.; Tail only passage."
    assert source["confidence"] == "low"
    assert source["mvp_testable"] is False
    assert source["data_access"] == "available-later"
    assert source["risks"] == ["Single paper.", "PDF text."]
    assert (source["title"], source["url_or_citation"], source["source_quality"]) == (
        "NAAIM paper", URLS[3], "discovery-only",
    )
    assert merged["open_questions"] == ["Which average?", "Costs?"]
    assert merged["curator_recommendation"] == "needs_more_work"


def test_a_source_with_no_relevant_evidence_anywhere_cannot_be_merged():
    windows = _windows()

    with pytest.raises(WindowMergeError, match=r"window: S4 had no relevant evidence in any of"):
        merge_window_outcomes("RQ-w", _item(), windows, [none_outcome(w) for w in windows])


def test_windows_that_disagree_on_source_type_are_not_arbitrated():
    windows = _windows()
    outcomes = [evidence_outcome(w, "Filler one.") for w in windows[:2]] + [
        none_outcome(w) for w in windows[2:]
    ]
    outcomes[1]["source"]["source_type"] = "web"

    with pytest.raises(WindowMergeError, match="source_type"):
        merge_window_outcomes("RQ-w", _item(), windows, outcomes)


@pytest.mark.parametrize("mutate", ["missing", "reordered", "extra"])
def test_every_window_must_be_accounted_for_in_order(mutate):
    windows = _windows()
    outcomes = [evidence_outcome(windows[0], "Filler one.")] + [
        none_outcome(w) for w in windows[1:]
    ]
    if mutate == "missing":
        outcomes = outcomes[:-1]
    elif mutate == "reordered":
        outcomes[1], outcomes[2] = outcomes[2], outcomes[1]
    else:
        outcomes.append(none_outcome(windows[-1]))

    with pytest.raises(WindowMergeError, match="accounting"):
        merge_window_outcomes("RQ-w", _item(), windows, outcomes)


def test_the_merge_reads_ids_the_way_the_validator_accepted_them():
    """Review finding: the validator strips whitespace, so the merge must too,
    or a run whose every window validated fails at accounting."""
    windows = _windows()
    outcomes = [evidence_outcome(windows[0], "Filler one.")] + [
        none_outcome(w) for w in windows[1:]
    ]
    outcomes[0]["window_id"] = f" {windows[0].window_id} "
    assert check(outcomes[0], windows[0]).ok

    merged = merge_window_outcomes("RQ-w", _item(), windows, outcomes)

    assert merged["sources"][0]["evidence"] == ["Filler one."]


def test_the_manifest_says_which_text_the_offsets_index():
    """Review finding: offsets index the newline-normalised decoded text, not
    the file bytes, so the manifest must say how to derive it."""
    from quant_brain.research.windowing import window_manifest

    item = _item()
    manifest = window_manifest(item, _windows(), snapshot_path="p.md", snapshot_sha256="0" * 64)

    assert "universal newlines" in manifest["snapshot_text_derivation"]
    assert manifest["snapshot_text_sha256"] == _sha(item["snapshot_text"])


# --- the ladder accepts a window validator ------------------------------------------


def test_qwen_call_can_validate_and_record_a_window(tmp_path):
    db_path = tmp_path / "brain.sqlite"
    init_database(db_path)
    window = _window_with(NEEDLE)
    client = Client([evidence_outcome(window, NEEDLE)])
    seen = []

    def validator(parsed):
        seen.append(parsed)
        return ValidationResult(True, (), parsed)

    result = qwen_call(
        "prompt", [_item()], expected_research_id="RQ-w", client=client, db_path=db_path,
        run_id="RUN-w", validator=validator, output_schema={"type": "object"},
        attempt_context={"window_id": window.window_id},
    )

    assert result.output["window_id"] == window.window_id
    assert seen and client.calls[0][2]["format"] == {"type": "object"}
    [event] = list_events(db_path, run_id="RUN-w")
    assert event["payload"]["window_id"] == window.window_id
    assert event["payload"]["source_ids"] == ["S4"]


# --- the executor: windowing end to end, hermetic -------------------------------------


class WindowedFetcher:
    """Normal-sized bodies, except `big` URLs, which get a large body with an
    optional needle placed once in the middle."""

    def __init__(self, big, *, kilobytes=60, needle=True):
        self.big, self.kilobytes, self.needle = set(big), kilobytes, needle

    def __call__(self, url):
        if url not in self.big:
            content = big_body(url, 12)
        else:
            body = big_body(url, self.kilobytes).replace("Exact evidence passage. ", "")
            if self.needle:
                middle = body.index("\n", len(body) // 2)
                body = body[:middle] + "\n" + NEEDLE + body[middle:]
            content = body
        return {"url": url, "content": content, "channel": "web", "backend": "fixture"}


_WINDOW_RE = re.compile(r"<<<BEGIN WINDOW (S\d+-W\d+)>>>\n(.*?)\n<<<END WINDOW \1>>>", re.S)
_METADATA_RE = re.compile(r"Source metadata:\n(\{.*?\n\})\n", re.S)


class FakeOllama:
    """Answers like a well-behaved model: quotes the needle where it is shown,
    says "no relevant evidence" elsewhere, and grounds normal sources."""

    def __init__(self, *, bad_window=None, on_window=None):
        self.prompts, self.bad_window, self.on_window = [], bad_window, on_window

    def __call__(self, prompt, model, **kwargs):
        self.prompts.append(prompt)
        research_id = re.search(r"Research ID: (\S+)", prompt).group(1)
        meta = json.loads(_METADATA_RE.search(prompt).group(1))
        window = _WINDOW_RE.search(prompt)
        if window is None:
            payload = {
                "research_id": research_id, "status": "raw_saved",
                "sources": [_normal_source(meta)], "open_questions": [],
                "curator_recommendation": "needs_more_work",
            }
        else:
            window_id, text = window.groups()
            if self.on_window:
                self.on_window(window_id)
            base = {"research_id": research_id, "source_id": meta["source_id"],
                    "window_id": window_id}
            if self.bad_window and window_id.endswith(self.bad_window):
                payload = {**base, "outcome": "evidence", "open_questions": [],
                           "curator_recommendation": "needs_more_work",
                           "source": {**_normal_source(meta), "evidence": "Invented quote."}}
            elif NEEDLE in text:
                payload = {**base, "outcome": "evidence", "open_questions": [],
                           "curator_recommendation": "needs_more_work",
                           "source": {**_normal_source(meta), "main_claim": NEEDLE,
                                      "evidence": NEEDLE}}
            else:
                payload = {**base, "outcome": "no_relevant_evidence", "source": None,
                           "open_questions": [], "curator_recommendation": None}
        text = json.dumps(payload)
        return OllamaResponse(text, model, 0.01, _sha(prompt), _sha(text), prompt_eval_count=100)


def _normal_source(meta):
    return {
        **meta, "source_type": "web", "main_claim": "Exact evidence passage.",
        "evidence": "Exact evidence passage.", "possible_strategy_rule": "",
        "risks": ["Requires review."], "confidence": "low", "asset_classes": ["equity"],
        "data_required": ["daily close"], "data_access": "available-now", "mvp_testable": False,
    }


def _note_payload(root, result):
    note = (root / result.outputs[0]).read_text(encoding="utf-8")
    return note, json.loads(note.split("```json")[-1].split("```")[0])


def _window_prompts(fake):
    return [p for p in fake.prompts if "<<<BEGIN WINDOW" in p]


def test_an_oversize_source_is_read_in_windows_and_merged_into_one_record(project, monkeypatch):  # noqa: F811
    root, db_path = project
    research_id = new_question(db_path)
    urls = list(URLS[:3])
    relative = write_list(root, research_id, urls)
    fake = FakeOllama()
    monkeypatch.setattr(ollama_client, "generate", fake)

    result = dispatch_list(project, relative, WindowedFetcher({urls[1]}), research_id=research_id,
                           run_id="RUN-windows")

    assert result.status == "completed"
    note, payload = _note_payload(root, result)
    assert len(payload["sources"]) == 3
    [windowed] = [s for s in payload["sources"] if s["url_or_citation"] == urls[1]]
    assert windowed["evidence"] == [NEEDLE]

    events = list_events(db_path, run_id="RUN-windows")
    window_events = [e for e in events if e["event_type"] == "extraction_window"]
    manifest = window_events[0]["payload"]
    count = manifest["window_count"]
    assert 2 <= count <= MAX_WINDOWS_PER_SOURCE
    assert [e["payload"]["window_id"] for e in window_events] == [
        f"{windowed['source_id']}-W{i:02d}" for i in range(1, count + 1)
    ]
    assert sum(e["payload"]["outcome"] == "evidence" for e in window_events) >= 1
    assert all(e["payload"]["validator_ok"] for e in window_events)

    # One call per window, in document order, each carrying only its own window.
    prompts = _window_prompts(fake)
    assert [_WINDOW_RE.search(p).group(1) for p in prompts] == [
        e["payload"]["window_id"] for e in window_events
    ]
    snapshot = (root / window_events[0]["payload"]["snapshot_path"]).read_text(encoding="utf-8")
    for prompt, event in zip(prompts, window_events, strict=True):
        start, end = event["payload"]["start"], event["payload"]["end"]
        assert _WINDOW_RE.search(prompt).group(2) == snapshot[start:end]
        assert _sha(snapshot[start:end]) == event["payload"]["text_sha256"]
        assert snapshot not in prompt

    attempts = [e for e in events if e["event_type"] == "qwen_attempt"]
    assert {a["payload"].get("window_id") for a in attempts} >= {
        e["payload"]["window_id"] for e in window_events
    }

    # Reconstructable from the note alone, outside the curator's JSON block.
    assert "## Extraction Windows" in note.rsplit("```json", 1)[0]
    for event in window_events:
        assert event["payload"]["window_id"] in note
        assert event["payload"]["text_sha256"] in note


def test_sources_that_fit_take_the_unchanged_single_prompt_path(project, monkeypatch):  # noqa: F811
    root, db_path = project
    research_id = new_question(db_path)
    relative = write_list(root, research_id, list(URLS[:3]))
    fake = FakeOllama()
    monkeypatch.setattr(ollama_client, "generate", fake)
    built = []
    original = executor._source_extraction_prompt
    monkeypatch.setattr(
        executor, "_source_extraction_prompt",
        lambda task, item: built.append(original(task, item)) or built[-1],
    )

    result = dispatch_list(project, relative, WindowedFetcher(set()), research_id=research_id,
                           run_id="RUN-plain")

    assert result.status == "completed"
    assert fake.prompts == built
    events = list_events(db_path, run_id="RUN-plain")
    assert not [e for e in events if e["event_type"] == "extraction_window"]
    note, _ = _note_payload(root, result)
    assert "## Extraction Windows" not in note


def test_one_failing_window_fails_the_run_and_every_window_is_accounted_for(project, monkeypatch):  # noqa: F811
    root, db_path = project
    research_id = new_question(db_path)
    urls = list(URLS[:3])
    relative = write_list(root, research_id, urls)
    # Only one source is windowed, so its second window is the one ending -W02.
    monkeypatch.setattr(ollama_client, "generate", FakeOllama(bad_window="-W02"))

    with pytest.raises(QwenValidationError, match=r"quote:"):
        dispatch_list(project, relative, WindowedFetcher({urls[1]}), research_id=research_id,
                      run_id="RUN-badwindow")

    assert question_state(db_path, research_id) == ("queued", None)
    receipt = _receipt_payload(root)
    [manifest] = receipt["extraction_windows"]
    windows = manifest["windows"]
    assert manifest["window_count"] == len(windows) >= 3
    assert manifest["snapshot_sha256"] and manifest["snapshot_path"]
    assert windows[0]["outcome"] in {"evidence", "no_relevant_evidence"}
    assert windows[1]["window_id"].endswith("-W02")
    assert windows[1]["outcome"] == "failed"
    assert len(windows[1]["attempts"]) == 3
    assert not any(a["validator_ok"] for a in windows[1]["attempts"])
    assert all(w["outcome"] == "not_run" for w in windows[2:])
    for window in windows:
        assert {"start", "end", "text_sha256", "index"} <= window.keys()


def test_a_source_with_no_relevant_evidence_in_any_window_fails_the_run(project, monkeypatch):  # noqa: F811
    root, db_path = project
    research_id = new_question(db_path)
    urls = list(URLS[:3])
    relative = write_list(root, research_id, urls)
    monkeypatch.setattr(ollama_client, "generate", FakeOllama())

    with pytest.raises(QwenValidationError, match=r"window: S\d had no relevant evidence in any of"):
        dispatch_list(project, relative, WindowedFetcher({urls[1]}, needle=False),
                      research_id=research_id, run_id="RUN-nothing")

    assert question_state(db_path, research_id) == ("queued", None)
    assert not list((root / "brain" / "00_Inbox" / "Raw_Research").glob("*.md"))
    [manifest] = _receipt_payload(root)["extraction_windows"]
    assert {w["outcome"] for w in manifest["windows"]} == {"no_relevant_evidence"}


def test_the_shared_run_deadline_bounds_the_windows(project, monkeypatch):  # noqa: F811
    root, db_path = project
    research_id = new_question(db_path)
    urls = list(URLS[:3])
    relative = write_list(root, research_id, urls)
    real = time.monotonic
    expired = []

    def on_window(window_id):
        if window_id.endswith("-W02"):
            expired.append(True)

    monkeypatch.setattr(time, "monotonic", lambda: real() + (10**6 if expired else 0))
    monkeypatch.setattr(ollama_client, "generate", FakeOllama(on_window=on_window))

    with pytest.raises(RunBudgetError):
        dispatch_list(project, relative, WindowedFetcher({urls[1]}), research_id=research_id,
                      run_id="RUN-late")

    assert question_state(db_path, research_id) == ("queued", None)
    [manifest] = _receipt_payload(root)["extraction_windows"]
    outcomes = [w["outcome"] for w in manifest["windows"]]
    assert outcomes[1] == "failed"
    assert set(outcomes[2:]) <= {"not_run"}


def test_a_source_beyond_the_window_cap_fails_before_any_model_call(project, monkeypatch):  # noqa: F811
    root, db_path = project
    research_id = new_question(db_path)
    urls = list(URLS[:3])
    relative = write_list(root, research_id, urls)
    fake = FakeOllama()
    monkeypatch.setattr(ollama_client, "generate", fake)

    with pytest.raises(ContextBudgetError, match=rf"window cap .*source S\d: {urls[1]}"):
        dispatch_list(project, relative, WindowedFetcher({urls[1]}, kilobytes=200),
                      research_id=research_id, run_id="RUN-cap")

    assert fake.prompts == []
    assert question_state(db_path, research_id) == ("queued", None)


def test_every_window_prompt_is_screened_before_the_first_model_call(project, monkeypatch):  # noqa: F811
    root, db_path = project
    research_id = new_question(db_path)
    urls = list(URLS[:3])
    relative = write_list(root, research_id, urls)
    fake = FakeOllama()
    monkeypatch.setattr(ollama_client, "generate", fake)
    real_prompt = window_prompt

    def swollen(task, item, window):
        prompt = real_prompt(task, item, window)
        return prompt + "x" * 60_000 if window.window_id.endswith("-W02") else prompt

    monkeypatch.setattr("quant_brain.research.windowing.window_prompt", swollen)

    with pytest.raises(ContextBudgetError, match=rf"window S\d-W02 of source S\d: {urls[1]}"):
        dispatch_list(project, relative, WindowedFetcher({urls[1]}), research_id=research_id,
                      run_id="RUN-screen")

    assert fake.prompts == []


def test_the_window_prompt_carries_only_its_window_and_says_none_is_acceptable():
    full = _full()
    window = _window_with(NEEDLE)
    task = {"research_id": "RQ-w", "question": "What exit rules pair with RSI?"}

    prompt = window_prompt(task, _item(full), window)

    assert window.text_of(full) in prompt and full not in prompt
    assert window.window_id in prompt and "no_relevant_evidence" in prompt
    assert f"{window.index} of {window.count}" in prompt
    assert WindowOutcome.model_json_schema()["properties"]["outcome"]

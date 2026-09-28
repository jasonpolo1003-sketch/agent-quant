"""The E4 failure, replayed against its preserved evidence. No model is called.

Run RUN-d67b1d121b (2026-09-28) failed closed at NAAIM window S4-W02. Its
receipt and snapshots are committed byte-for-byte (c6d13d1). These tests
validate *saved* data only:

- the windows this code plans for the preserved snapshot are exactly the ones
  the run recorded;
- a saved qwen3:14b response to the real S4-W03 prompt (from a diagnostic
  replay under the original contract -- W03 never ran in the run, and the run
  kept only response hashes) is judged by the amended contract.

What a fresh model does under the amended contract is a separate question,
answered only by live inference (scripts/window_replay.py), never here.
"""

import hashlib
import json
from pathlib import Path

import pytest

from quant_brain.config import PROJECT_ROOT
from quant_brain.llm.validators import validate_research_output
from quant_brain.research.windowing import (
    merge_window_outcomes,
    plan_windows,
    validate_window_outcome,
)

RUN = "RUN-d67b1d121b"
RESEARCH_ID = "RQ-6d9c12f4"
SNAPSHOT = PROJECT_ROOT / "brain/00_Inbox/Source_Snapshots/2026-09-28/c5f9673f32a4-97d0dbd7.md"
RECEIPT = PROJECT_ROOT / f"brain/00_Inbox/Failed_Runs/{RUN}.md"
FIXTURE = Path(__file__).parent / "fixtures" / "e4_window_failure" / "w03_replay_response.json"
EXIT_RULE = (
    "• Go long at the close if RSI(3) < 10",
    "• Maintain the position while RSI(3) ≤ 40",
)

pytestmark = pytest.mark.skipif(
    not (SNAPSHOT.is_file() and RECEIPT.is_file()), reason="E4 evidence not present"
)


def _receipt():
    body = RECEIPT.read_text(encoding="utf-8")
    return json.loads(body.split("```json")[1].split("```")[0])


def _item():
    candidate = _receipt()["accepted_candidates"][3]
    return {
        "source_id": "S4",
        "title": candidate["title"],
        "url_or_citation": candidate["url"],
        "source_quality": candidate["tier"],
        "snapshot_text": SNAPSHOT.read_text(encoding="utf-8"),
    }


def _windows():
    return plan_windows(_item()["snapshot_text"], "S4")


def _saved_w03():
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    text = doc["response_text"]
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == doc["response_sha256"]
    return json.loads(text)


def _check(payload, window):
    return validate_window_outcome(payload, _item(), window, expected_research_id=RESEARCH_ID)


def test_the_planned_windows_are_exactly_the_ones_the_run_recorded():
    [manifest] = _receipt()["extraction_windows"]
    item = _item()

    assert hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest() == manifest["snapshot_sha256"]
    assert (
        hashlib.sha256(item["snapshot_text"].encode("utf-8")).hexdigest()
        == manifest["snapshot_text_sha256"]
    )
    assert [(w.window_id, w.start, w.end, w.text_sha256) for w in _windows()] == [
        (w["window_id"], w["start"], w["end"], w["text_sha256"]) for w in manifest["windows"]
    ]
    assert [w["outcome"] for w in manifest["windows"]][:2] == ["no_relevant_evidence", "failed"]


def test_the_naaim_exit_rule_lies_in_both_w02_and_w03():
    text = _item()["snapshot_text"]
    windows = {w.window_id: w for w in _windows()}

    for quote in EXIT_RULE:
        start = text.index(quote)
        holders = [w for w in windows.values() if w.start <= start and start + len(quote) <= w.end]
        assert [w.window_id for w in holders] == ["S4-W02", "S4-W03"]


def test_the_saved_response_is_refused_for_carrying_a_recommendation_the_contract_dropped():
    verdict = _check(_saved_w03(), _windows()[2])

    assert not verdict.ok
    assert any("curator_recommendation" in reason for reason in verdict.reasons)


def test_without_the_dropped_field_its_quotes_pass_and_only_genuine_defects_remain():
    """The E4 trap is gone; the evidence validators are exactly as strict."""
    saved = _saved_w03()
    del saved["curator_recommendation"]

    verdict = _check(saved, _windows()[2])

    assert sorted(reason.split(":")[0] for reason in verdict.reasons) == [
        "contradiction",  # high confidence on a discovery-only source
        "ungrounded-promotion",  # mvp_testable with a claim that is not a passage
    ]
    assert not any(reason.startswith(("quote", "schema", "window")) for reason in verdict.reasons)


def test_the_same_quotes_are_refused_in_a_window_that_does_not_contain_them():
    """The third quote starts exactly where W02 ends: real text, not shown in W02."""
    saved = _saved_w03()
    del saved["curator_recommendation"]
    saved["window_id"] = "S4-W02"

    verdict = _check(saved, _windows()[1])

    assert any(reason.startswith("quote:S4") for reason in verdict.reasons)
    assert not any(reason.startswith("quote-full:S4") for reason in verdict.reasons)


def test_a_saved_source_without_its_identity_is_refused():
    """E4 attempts 2-3 dropped source_id; reconstructed from the recorded reasons
    (the run kept no response text), applied to the saved W03 response."""
    saved = _saved_w03()
    del saved["curator_recommendation"]
    del saved["source"]["source_id"]

    verdict = _check(saved, _windows()[2])

    assert not verdict.ok
    assert any("source_id" in reason for reason in verdict.reasons)


def test_a_repaired_saved_response_merges_into_a_valid_conservative_record():
    """Edited fixture: the two genuine defects fixed the way a repair must fix
    them (lower confidence, drop the testability claim). Evidence is untouched."""
    saved = _saved_w03()
    del saved["curator_recommendation"]
    saved["source"].update(confidence="low", mvp_testable=False)
    windows = _windows()
    item = _item()
    assert _check(saved, windows[2]).ok
    outcomes = [
        {"research_id": RESEARCH_ID, "source_id": "S4", "window_id": w.window_id,
         "outcome": "no_relevant_evidence", "source": None, "open_questions": []}
        for w in windows
    ]
    outcomes[2] = saved

    merged = merge_window_outcomes(RESEARCH_ID, item, windows, outcomes)

    assert merged["curator_recommendation"] == "needs_more_work"
    [source] = merged["sources"]
    assert source["evidence"][:2] == list(EXIT_RULE)
    assert all(quote in item["snapshot_text"] for quote in source["evidence"])
    assert validate_research_output(merged, [item], expected_research_id=RESEARCH_ID).ok

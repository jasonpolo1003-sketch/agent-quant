"""Every hash a committed Failed_Runs receipt records must still verify.

Receipts are historical evidence and are never edited. When snapshot bytes
had to move (E5 rewrote two E4 snapshots in place; E4's bytes were restored to
the path E4 recorded and E5's moved to a new name), the move is recorded in
the reconciliation ledger, which the verifier follows -- and whose own file
hashes it checks, so a ledger entry cannot vouch for different bytes.
"""

import json
import shutil
from pathlib import Path

import pytest

from quant_brain.config import PROJECT_ROOT
from quant_brain.research.receipts import (
    RECONCILIATION_PATH,
    ReceiptVerificationError,
    resolve_recorded_snapshot,
    verify_all_receipts,
    verify_receipt,
)

FAILED_RUNS = PROJECT_ROOT / "brain" / "00_Inbox" / "Failed_Runs"
HASHED = ("RUN-9b0d5a6e12", "RUN-d67b1d121b", "RUN-871299ea31")
E5 = "RUN-871299ea31"
COLLIDED = (
    "brain/00_Inbox/Source_Snapshots/2026-09-28/c5f9673f32a4-97d0dbd7.md",
    "brain/00_Inbox/Source_Snapshots/2026-09-28/f57de4fc3101-1bb9664e.md",
)


def test_every_committed_receipt_verifies():
    results = verify_all_receipts(PROJECT_ROOT)

    by_run = {result.run_id: result for result in results}
    for run in HASHED:
        assert by_run[run].problems == [], (run, by_run[run].problems)
        assert by_run[run].checked > 0
    assert all(result.problems == [] for result in results)


@pytest.mark.parametrize("run", HASHED)
def test_each_hashed_receipt_checks_every_recorded_hash(run):
    payload = _payload(run)
    result = verify_receipt(PROJECT_ROOT, FAILED_RUNS / f"{run}.md")
    candidates = len(payload["accepted_candidates"])
    windows = sum(m["window_count"] for m in payload.get("extraction_windows") or [])
    manifests = len(payload.get("extraction_windows") or [])
    responses = 0
    if payload.get("diagnostic_responses_path"):
        doc = json.loads((PROJECT_ROOT / payload["diagnostic_responses_path"]).read_text("utf-8"))
        responses = len(doc["responses"])

    # one per candidate body, per manifest file + text, per window, per kept response
    assert result.checked == candidates + 2 * manifests + windows + responses


def test_both_versions_of_each_collided_snapshot_are_kept_and_attributed():
    for recorded in COLLIDED:
        e4 = resolve_recorded_snapshot(PROJECT_ROOT, "RUN-d67b1d121b", recorded)
        e5 = resolve_recorded_snapshot(PROJECT_ROOT, E5, recorded)
        assert e4 == PROJECT_ROOT / recorded  # the first writer keeps the recorded path
        assert e5 != e4 and e5.is_file()
        assert e4.read_bytes() != e5.read_bytes()
        body = lambda p: p.read_text(encoding="utf-8").split("\n---\n", 1)[1]  # noqa: E731
        assert body(e4) == body(e5)  # the same fetched content; only captured_at differs


def _payload(run):
    body = (FAILED_RUNS / f"{run}.md").read_text(encoding="utf-8")
    return json.loads(body.split("```json")[1].split("```")[0])


def _copy_run(tmp_path, run, *, ledger=True):
    """A minimal project holding one receipt, its snapshots and diagnostics."""
    payload = _payload(run)
    paths = {c["snapshot_path"] for c in payload["accepted_candidates"]}
    paths |= {m["snapshot_path"] for m in payload.get("extraction_windows") or []}
    if payload.get("diagnostic_responses_path"):
        paths.add(payload["diagnostic_responses_path"])
    receipt = f"brain/00_Inbox/Failed_Runs/{run}.md"
    for relative in paths | {receipt}:
        src = resolve_recorded_snapshot(PROJECT_ROOT, run, relative)
        dest = tmp_path / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)  # at the *recorded* path: as if never moved
    if ledger:
        dest = tmp_path / RECONCILIATION_PATH
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(PROJECT_ROOT / RECONCILIATION_PATH, dest)
    return tmp_path / receipt


def test_a_changed_snapshot_byte_is_detected(tmp_path):
    receipt = _copy_run(tmp_path, "RUN-d67b1d121b", ledger=False)
    target = tmp_path / COLLIDED[0]
    target.write_bytes(target.read_bytes().replace(b"captured_at: 2026", b"captured_at: 2027"))

    problems = verify_receipt(tmp_path, receipt).problems

    assert any("S4" in problem and "sha256" in problem for problem in problems)


def test_the_e4_overwrite_itself_is_what_the_verifier_would_have_caught(tmp_path):
    """Put E5's bytes at the path E4 recorded -- the state E5 left behind."""
    receipt = _copy_run(tmp_path, "RUN-d67b1d121b", ledger=False)
    for recorded in COLLIDED:
        e5 = resolve_recorded_snapshot(PROJECT_ROOT, E5, recorded)
        shutil.copyfile(e5, tmp_path / recorded)

    problems = verify_receipt(tmp_path, receipt).problems

    assert problems and all("S4" in p or "window" in p for p in problems)


def test_a_ledger_entry_cannot_vouch_for_different_bytes(tmp_path):
    receipt = _copy_run(tmp_path, E5)
    for recorded in COLLIDED:  # the ledger points E5 at its moved files; copy them too
        actual = resolve_recorded_snapshot(PROJECT_ROOT, E5, recorded)
        dest = tmp_path / actual.relative_to(PROJECT_ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(actual, dest)
    moved = resolve_recorded_snapshot(tmp_path, E5, COLLIDED[0])
    moved.write_bytes(moved.read_bytes() + b"\n")

    with pytest.raises(ReceiptVerificationError, match="ledger"):
        resolve_recorded_snapshot(tmp_path, E5, COLLIDED[0])
    assert any("ledger" in problem for problem in verify_receipt(tmp_path, receipt).problems)


def test_the_verifier_reads_but_never_writes(tmp_path):
    receipt = _copy_run(tmp_path, E5)
    for recorded in COLLIDED:
        actual = resolve_recorded_snapshot(PROJECT_ROOT, E5, recorded)
        dest = tmp_path / actual.relative_to(PROJECT_ROOT)
        shutil.copyfile(actual, dest)
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}

    verify_receipt(tmp_path, receipt)

    assert {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()} == before


def test_receipts_are_not_edited_by_reconciliation():
    """The ledger adds a pointer; each receipt still names the path it recorded."""
    for run in (E5, "RUN-d67b1d121b"):
        recorded = {c["snapshot_path"] for c in _payload(run)["accepted_candidates"]}
        assert set(COLLIDED) <= recorded
    assert Path(PROJECT_ROOT / RECONCILIATION_PATH).is_file()


def test_newline_normalisation_of_a_snapshot_is_detected(tmp_path):
    """Only the file-bytes hash sees this: the decoded text is identical. It is
    what git's autocrlf would do to a snapshot without its -text rule."""
    receipt = _copy_run(tmp_path, "RUN-d67b1d121b", ledger=False)
    target = tmp_path / COLLIDED[0]
    assert b"\r\n" in target.read_bytes()
    target.write_bytes(target.read_bytes().replace(b"\r\n", b"\n"))

    problems = verify_receipt(tmp_path, receipt).problems

    assert problems == [f"windows S4: file sha256 of {COLLIDED[0]} differs"]


def test_a_changed_body_of_an_unwindowed_source_is_detected(tmp_path):
    receipt = _copy_run(tmp_path, "RUN-9b0d5a6e12", ledger=False)
    candidate = _payload("RUN-9b0d5a6e12")["accepted_candidates"][1]
    target = tmp_path / candidate["snapshot_path"]
    target.write_bytes(target.read_bytes() + b"Appended later.\r\n")

    problems = verify_receipt(tmp_path, receipt).problems

    assert problems == [
        f"candidate {candidate['url']}: content sha256 of {candidate['snapshot_path']} "
        f"is not {candidate['snapshot_sha256']}"
    ]


def test_an_edited_window_offset_in_a_receipt_is_detected(tmp_path):
    receipt = _copy_run(tmp_path, "RUN-d67b1d121b", ledger=False)
    body = receipt.read_text(encoding="utf-8")
    window = _payload("RUN-d67b1d121b")["extraction_windows"][0]["windows"][2]
    edited = body.replace(f'"start": {window["start"]},', f'"start": {window["start"] + 1},', 1)
    assert edited != body
    receipt.write_text(edited, encoding="utf-8")

    problems = verify_receipt(tmp_path, receipt).problems

    assert problems == [f"windows S4: window {window['window_id']} sha256 differs"]


def test_the_ledger_proves_the_first_writers_bytes_are_back(tmp_path):
    """Review finding: E4 recorded only a content hash for the Connors page,
    which E5's bytes share, so without the ledger's own file hash the verifier
    could not tell whether E4's restored bytes -- or E5's -- sit at E4's path."""
    for run in (E5, "RUN-d67b1d121b"):  # E4 last: its bytes own the recorded paths
        _copy_run(tmp_path, run)
    for recorded in COLLIDED:
        actual = resolve_recorded_snapshot(PROJECT_ROOT, E5, recorded)
        shutil.copyfile(actual, tmp_path / actual.relative_to(PROJECT_ROOT))
    assert all(not r.problems for r in verify_all_receipts(tmp_path))
    connors = COLLIDED[1]
    shutil.copyfile(resolve_recorded_snapshot(PROJECT_ROOT, E5, connors), tmp_path / connors)

    problems = [p for r in verify_all_receipts(tmp_path) for p in r.problems]

    assert problems == [
        f"reconciliation ledger: {connors} is not RUN-d67b1d121b's original bytes"
    ]

"""Verify that a Failed_Runs receipt's recorded evidence still hashes as recorded.

Receipts are historical evidence and are never edited. If snapshot bytes ever
have to move, the move goes in a reconciliation ledger that names the run, the
path its receipt recorded, where the bytes now are, and their sha256; the
resolver follows the ledger and re-checks that hash, so an entry cannot vouch
for different bytes. Read-only throughout.

What each recorded hash means (all established against the committed E3-E5
receipts):

- ``accepted_candidates[].snapshot_sha256``: sha256 of the fetched content,
  i.e. the snapshot text after its front matter (UTF-8, universal newlines).
- ``extraction_windows[].snapshot_sha256``: sha256 of the snapshot file bytes;
  ``snapshot_text_sha256`` of its decoded text; each window's ``text_sha256``
  of ``text[start:end]``.
- diagnostic ``response_hash``: sha256 of the kept ``response_text``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

FAILED_RUNS_DIR = "brain/00_Inbox/Failed_Runs"
RECONCILIATION_PATH = "brain/00_Inbox/Source_Snapshots/reconciliation.json"


class ReceiptVerificationError(ValueError):
    """Recorded evidence cannot be located or does not hash as recorded."""


@dataclass
class ReceiptResult:
    run_id: str
    checked: int = 0
    problems: list[str] = field(default_factory=list)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _decode(path: Path) -> str:
    # Universal newlines, exactly as the executor read snapshots (Path.read_text).
    return path.read_text(encoding="utf-8")


def receipt_payload(receipt: Path) -> dict[str, Any]:
    body = receipt.read_text(encoding="utf-8")
    if "```json" not in body:
        raise ReceiptVerificationError(f"{receipt.name}: no JSON block")
    return json.loads(body.split("```json")[1].split("```")[0])


def _ledger(project_root: Path) -> list[dict[str, Any]]:
    path = project_root / RECONCILIATION_PATH
    if not path.is_file():
        return []
    return list(json.loads(path.read_text(encoding="utf-8"))["entries"])


def resolve_recorded_snapshot(project_root: str | Path, run_id: str, recorded_path: str) -> Path:
    """Where the bytes a run recorded at ``recorded_path`` are now.

    The recorded path itself unless the ledger moved them for this run; a
    ledger target must exist and hash to the ledger's recorded sha256.
    """
    root = Path(project_root)
    for entry in _ledger(root):
        if entry["run_id"] == run_id and entry["recorded_path"] == recorded_path:
            actual = root / entry["actual_path"]
            if not actual.is_file() or _sha256(actual.read_bytes()) != entry["file_sha256"]:
                raise ReceiptVerificationError(
                    f"reconciliation ledger: {entry['actual_path']} for {run_id} is missing "
                    f"or no longer hashes to {entry['file_sha256']}"
                )
            return actual
    return root / recorded_path


def _content_of(snapshot_text: str) -> str:
    return snapshot_text.split("\n---\n", 1)[1].removeprefix("\n")


def verify_receipt(project_root: str | Path, receipt: str | Path) -> ReceiptResult:
    """Check every hash ``receipt`` records against the evidence on disk."""
    root = Path(project_root)
    receipt = Path(receipt)
    payload = receipt_payload(receipt)
    run_id = receipt.stem
    result = ReceiptResult(run_id)

    def locate(recorded: str, label: str) -> Path | None:
        try:
            path = resolve_recorded_snapshot(root, run_id, recorded)
        except ReceiptVerificationError as exc:
            result.problems.append(f"{label}: {exc}")
            return None
        if not path.is_file():
            result.problems.append(f"{label}: {recorded} is missing")
            return None
        return path

    for candidate in payload.get("accepted_candidates") or []:
        recorded, expected = candidate.get("snapshot_path"), candidate.get("snapshot_sha256")
        if not recorded or not expected:
            continue
        path = locate(recorded, f"candidate {candidate.get('url')}")
        if path is None:
            continue
        result.checked += 1
        if _sha256(_content_of(_decode(path)).encode("utf-8")) != expected:
            result.problems.append(
                f"candidate {candidate.get('url')}: content sha256 of {recorded} is not {expected}"
            )

    for manifest in payload.get("extraction_windows") or []:
        label = f"windows {manifest['source_id']}"
        path = locate(manifest["snapshot_path"], label)
        if path is None:
            continue
        result.checked += 2
        if _sha256(path.read_bytes()) != manifest["snapshot_sha256"]:
            result.problems.append(f"{label}: file sha256 of {manifest['snapshot_path']} differs")
        text = _decode(path)
        if _sha256(text.encode("utf-8")) != manifest["snapshot_text_sha256"]:
            result.problems.append(f"{label}: text sha256 differs")
        for window in manifest["windows"]:
            result.checked += 1
            actual = _sha256(text[window["start"] : window["end"]].encode("utf-8"))
            if actual != window["text_sha256"]:
                result.problems.append(f"{label}: window {window['window_id']} sha256 differs")

    diagnostics = payload.get("diagnostic_responses_path")
    if diagnostics:
        path = root / diagnostics
        if not path.is_file():
            result.problems.append(f"diagnostics: {diagnostics} is missing")
        else:
            for index, response in enumerate(json.loads(path.read_text("utf-8"))["responses"]):
                result.checked += 1
                text = response.get("response_text")
                if text is None or _sha256(text.encode("utf-8")) != response["response_hash"]:
                    result.problems.append(f"diagnostics: response {index} does not match its hash")
    return result


def verify_ledger(project_root: str | Path) -> ReceiptResult:
    """Check that each reconciled path again holds its original owner's bytes.

    A receipt may record only a content hash for a path (E4 did for the
    Connors page), which a displacing run's bytes can share, so only the
    ledger's own file hash can show the first writer's bytes are back.
    """
    root = Path(project_root)
    result = ReceiptResult("reconciliation-ledger")
    for entry in _ledger(root):
        owner = entry.get("original_owner")
        if not owner:
            continue
        result.checked += 1
        path = root / owner["path"]
        if not path.is_file() or _sha256(path.read_bytes()) != owner["file_sha256"]:
            result.problems.append(
                f"reconciliation ledger: {owner['path']} is not {owner['run_id']}'s original bytes"
            )
    return result


def verify_all_receipts(project_root: str | Path) -> list[ReceiptResult]:
    """Verify every receipt with a JSON block under ``Failed_Runs``, and the ledger."""
    root = Path(project_root)
    results = [verify_ledger(root)]
    for receipt in sorted((root / FAILED_RUNS_DIR).glob("*.md")):
        try:
            results.append(verify_receipt(root, receipt))
        except ReceiptVerificationError:
            continue  # no JSON block: nothing machine-checkable recorded
    return results

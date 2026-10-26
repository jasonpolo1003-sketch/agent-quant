"""Guard the frozen SC-FUT-0001 spec against silent edits."""

from __future__ import annotations

import hashlib
import json

from quant_brain.config import BRAIN_DIR

FUTURES = BRAIN_DIR / "_system" / "futures"


def _sha(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_frozen_spec_matches_recorded_hash():
    recorded = (FUTURES / "sc-fut-0001-spec.v1.sha256").read_text(encoding="utf-8").split()[0]
    assert _sha(FUTURES / "sc-fut-0001-spec.v1.json") == recorded


def test_frozen_spec_is_complete_and_not_executable():
    spec = json.loads((FUTURES / "sc-fut-0001-spec.v1.json").read_text(encoding="utf-8"))
    assert spec["frozen"] is True and spec["freeze_blockers"] == []
    assert spec["execution_allowed"] is False

    def nulls(node, path=""):
        if isinstance(node, dict):
            for key, value in node.items():
                yield from nulls(value, f"{path}.{key}")
        elif node is None:
            yield path

    assert list(nulls(spec)) == []


def test_pinned_repo_files_match_frozen_hashes():
    spec = json.loads((FUTURES / "sc-fut-0001-spec.v1.json").read_text(encoding="utf-8"))
    root = BRAIN_DIR.parent
    pinned = [
        (
            spec["data_partitions"]["session_calendar"],
            spec["data_partitions"]["session_calendar_manifest_sha256"],
        ),
        (spec["costs"]["cost_levels_source"], spec["costs"]["cost_levels_manifest_sha256"]),
        (
            spec["inference"]["selection"]["local_prior_looks_ledger"],
            spec["inference"]["selection"]["local_prior_looks_ledger_sha256"],
        ),
        *[(r["file"], r["sha256"]) for r in spec["decision_records"].values()],
        (
            spec["data_partitions"]["coverage_audit"]["file"],
            spec["data_partitions"]["coverage_audit"]["sha256"],
        ),
    ]
    for relative, digest in pinned:
        assert _sha(root / relative) == digest, relative

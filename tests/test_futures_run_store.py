"""Crash-safe futures run publication: only a verified manifest means complete."""

import hashlib
import json
import os
import subprocess

import pytest

from quant_brain.futures import run_store
from quant_brain.futures.run_store import RunState, RunStore, RunStoreError


def test_completed_run_atomically_publishes_a_hashed_artifact_manifest(tmp_path):
    store = RunStore(tmp_path)
    events = b'{"event":"one"}\n'

    assert store.create("run-001") is RunState.CREATED
    assert store.begin("run-001") is RunState.RUNNING
    store.stage("run-001", "events.jsonl", events)
    manifest = store.complete("run-001")

    assert manifest == {
        "schema_version": 1,
        "run_id": "run-001",
        "state": "COMPLETED",
        "artifacts": {
            "events.jsonl": {
                "bytes": len(events),
                "sha256": hashlib.sha256(events).hexdigest(),
            }
        },
    }
    manifest_path = tmp_path / "run-001" / "manifest.json"
    assert json.loads(manifest_path.read_text(encoding="utf-8")) == manifest
    assert store.completed_manifest("run-001") == manifest


def test_run_state_machine_requires_created_then_running_before_staging(tmp_path):
    store = RunStore(tmp_path)

    with pytest.raises(RunStoreError, match="not created"):
        store.begin("run-002")
    assert store.create("run-002") is RunState.CREATED
    assert store.state("run-002") is RunState.CREATED
    store.begin("run-002")
    assert store.state("run-002") is RunState.RUNNING


def test_failed_run_cannot_be_completed(tmp_path):
    store = RunStore(tmp_path)
    store.create("run-003")
    store.begin("run-003")

    assert store.fail("run-003", "synthetic failure") is RunState.FAILED
    assert store.state("run-003") is RunState.FAILED
    with pytest.raises(RunStoreError, match="not running"):
        store.complete("run-003")
    assert store.completed_manifest("run-003") is None


def test_interrupted_manifest_publish_leaves_no_completion_or_temporary_debris(
    tmp_path, monkeypatch
):
    store = RunStore(tmp_path)
    store.create("run-004")
    store.begin("run-004")
    store.stage("run-004", "events.jsonl", b"event\n")
    real_replace = run_store.os.replace

    def interrupt_manifest(source, destination):
        if destination.name == "manifest.json":
            raise OSError("synthetic interruption")
        return real_replace(source, destination)

    monkeypatch.setattr(run_store.os, "replace", interrupt_manifest)
    with pytest.raises(OSError, match="synthetic interruption"):
        store.complete("run-004")

    run_dir = tmp_path / "run-004"
    assert not (run_dir / "manifest.json").exists()
    assert not (run_dir / "manifest.json.tmp").exists()
    assert not list(run_dir.glob(".manifest.json.*.tmp"))
    assert store.state("run-004") is RunState.RUNNING


@pytest.mark.parametrize("relative", ["../outside", "..\\outside", "/absolute"])
def test_artifact_paths_cannot_escape_the_run(tmp_path, relative):
    store = RunStore(tmp_path)
    store.create("run-005")
    store.begin("run-005")

    with pytest.raises(RunStoreError, match="stay within"):
        store.stage("run-005", relative, b"unsafe")
    assert not (tmp_path / "outside").exists()


def test_completed_manifest_rejects_artifact_path_traversal(tmp_path):
    store = RunStore(tmp_path)
    store.create("run-006")
    store.begin("run-006")
    store.stage("run-006", "events.jsonl", b"event\n")
    store.complete("run-006")
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"outside")
    manifest_path = tmp_path / "run-006" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifacts"] = {
        "../../outside.txt": {
            "bytes": len(b"outside"),
            "sha256": hashlib.sha256(b"outside").hexdigest(),
        }
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(RunStoreError, match="artifact path"):
        store.completed_manifest("run-006")


@pytest.mark.parametrize(
    "manifest",
    [
        {"run_id": "run-007", "state": "COMPLETED", "artifacts": {}},
        {"schema_version": 1, "run_id": "run-007", "state": "COMPLETED"},
        {"schema_version": 99, "run_id": "run-007", "state": "COMPLETED", "artifacts": {}},
    ],
)
def test_completed_manifest_requires_the_exact_supported_top_level_schema(tmp_path, manifest):
    run_dir = tmp_path / "run-007"
    (run_dir / ".staging").mkdir(parents=True)
    (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(RunStoreError, match="invalid completion manifest"):
        RunStore(tmp_path).completed_manifest("run-007")


def test_completed_manifest_must_describe_the_exact_staged_inventory(tmp_path):
    store = RunStore(tmp_path)
    store.create("run-008")
    store.begin("run-008")
    store.stage("run-008", "events.jsonl", b"event\n")
    store.complete("run-008")
    staging = tmp_path / "run-008" / ".staging"
    (staging / "unlisted.json").write_bytes(b"unlisted")

    with pytest.raises(RunStoreError, match="artifact inventory"):
        store.completed_manifest("run-008")


def test_completion_excludes_concurrent_staging(tmp_path, monkeypatch):
    store = RunStore(tmp_path)
    store.create("run-009")
    store.begin("run-009")
    store.stage("run-009", "events.jsonl", b"event\n")
    real_replace = run_store.os.replace
    attempted = False

    def interleave_stage(source, destination):
        nonlocal attempted
        if destination.name == "manifest.json" and not attempted:
            attempted = True
            with pytest.raises(RunStoreError, match="operation is already in progress"):
                store.stage("run-009", "late.json", b"late")
        return real_replace(source, destination)

    monkeypatch.setattr(run_store.os, "replace", interleave_stage)
    manifest = store.complete("run-009")

    assert attempted
    assert set(manifest["artifacts"]) == {"events.jsonl"}
    assert store.completed_manifest("run-009") == manifest


def test_manifest_contents_are_fsynced_before_atomic_publication(tmp_path, monkeypatch):
    store = RunStore(tmp_path)
    store.create("run-010")
    store.begin("run-010")
    store.stage("run-010", "events.jsonl", b"event\n")
    real_replace = run_store.os.replace
    real_fsync = run_store.os.fsync
    synced = False

    def observe_fsync(descriptor):
        nonlocal synced
        synced = True
        return real_fsync(descriptor)

    def require_sync_before_manifest(source, destination):
        if destination.name == "manifest.json":
            assert synced, "manifest bytes must be flushed before publication"
        return real_replace(source, destination)

    monkeypatch.setattr(run_store.os, "fsync", observe_fsync)
    monkeypatch.setattr(run_store.os, "replace", require_sync_before_manifest)
    store.complete("run-010")

    assert synced


def test_completion_rejects_a_preexisting_symlink_artifact(tmp_path):
    store = RunStore(tmp_path)
    store.create("run-011")
    store.begin("run-011")
    outside = tmp_path / "outside.bin"
    outside.write_bytes(b"outside")
    link = tmp_path / "run-011" / ".staging" / "linked.bin"
    try:
        link.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"symlinks unavailable on this host: {exc}")

    with pytest.raises(RunStoreError, match="symlink"):
        store.complete("run-011")


def test_atomic_write_does_not_follow_a_planted_predictable_temporary_hardlink(tmp_path):
    store = RunStore(tmp_path)
    store.create("run-012")
    store.begin("run-012")
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"outside")
    planted = tmp_path / "run-012" / ".staging" / "events.jsonl.tmp"
    os.link(outside, planted)

    store.stage("run-012", "events.jsonl", b"event\n")

    assert outside.read_bytes() == b"outside"


def test_staging_root_cannot_be_replaced_by_an_external_link_or_junction(tmp_path):
    store = RunStore(tmp_path)
    store.create("run-013")
    store.begin("run-013")
    run_dir = tmp_path / "run-013"
    staging = run_dir / ".staging"
    staging.rmdir()
    outside = tmp_path / "external-staging"
    outside.mkdir()
    if os.name == "nt":
        created = subprocess.run(
            ["cmd.exe", "/c", "mklink", "/J", str(staging), str(outside)],
            capture_output=True,
            text=True,
        )
        if created.returncode:
            pytest.skip(f"junctions unavailable on this host: {created.stderr}")
    else:
        staging.symlink_to(outside, target_is_directory=True)

    with pytest.raises(RunStoreError, match="staging"):
        store.stage("run-013", "escaped.bin", b"unsafe")
    assert not (outside / "escaped.bin").exists()


def test_failure_transition_cannot_interleave_with_completion(tmp_path, monkeypatch):
    store = RunStore(tmp_path)
    store.create("run-014")
    store.begin("run-014")
    store.stage("run-014", "events.jsonl", b"event\n")
    real_replace = run_store.os.replace
    attempted = False

    def interleave_failure(source, destination):
        nonlocal attempted
        if destination.name == "manifest.json" and not attempted:
            attempted = True
            with pytest.raises(RunStoreError, match="operation is already in progress"):
                store.fail("run-014", "too late")
        return real_replace(source, destination)

    monkeypatch.setattr(run_store.os, "replace", interleave_failure)
    store.complete("run-014")

    assert attempted
    assert store.state("run-014") is RunState.COMPLETED

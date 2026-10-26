"""Crash-safe, hash-verified publication of futures research runs."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Any


class RunStoreError(RuntimeError):
    """A run cannot be safely created, staged, completed, or loaded."""


class RunState(StrEnum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"


class RunStore:
    """Filesystem run store where only a final verified manifest means complete."""

    def __init__(self, root: str | Path):
        self.root = Path(root)

    def _run_dir(self, run_id: str) -> Path:
        if not run_id or run_id in {".", ".."} or any(c in run_id for c in "/\\"):
            raise RunStoreError("run_id must be one non-empty path segment")
        return self.root / run_id

    @staticmethod
    def _is_link_or_reparse(path: Path) -> bool:
        if path.is_symlink():
            return True
        try:
            attributes = getattr(path.lstat(), "st_file_attributes", 0)
        except OSError:
            return False
        return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))

    def _staging_dir(self, run_dir: Path) -> Path:
        staging = run_dir / ".staging"
        root_resolved = self.root.resolve()
        run_resolved = run_dir.resolve()
        if (
            self._is_link_or_reparse(run_dir)
            or run_resolved.parent != root_resolved
            or self._is_link_or_reparse(staging)
            or not staging.is_dir()
            or staging.resolve() != run_resolved / ".staging"
        ):
            raise RunStoreError("staging directory must be a real directory inside the run")
        return staging

    def _write_state(self, run_id: str, state: RunState) -> None:
        self._write_json_atomic(
            self._run_dir(run_id) / "state.json",
            {"schema_version": 1, "run_id": run_id, "state": state.value},
        )

    @staticmethod
    def _artifact_path(staging: Path, relative: object) -> Path:
        if type(relative) is not str:
            raise RunStoreError("artifact path must be a string")
        path_part = PurePosixPath(relative)
        if (
            "\\" in relative
            or path_part.is_absolute()
            or not path_part.parts
            or ".." in path_part.parts
        ):
            raise RunStoreError("artifact path must stay within the run")
        target = staging / Path(*path_part.parts)
        staging_resolved = staging.resolve()
        target_resolved = target.resolve(strict=False)
        if not target_resolved.is_relative_to(staging_resolved):
            raise RunStoreError("artifact path escapes the run")
        current = staging
        for part in path_part.parts:
            current /= part
            if current.is_symlink():
                raise RunStoreError("artifact path cannot contain a symlink")
        return target

    @staticmethod
    @contextmanager
    def _exclusive(run_dir: Path) -> Iterator[None]:
        lock = run_dir / ".operation.lock"
        try:
            descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise RunStoreError("another run operation is already in progress") from exc
        try:
            yield
        finally:
            os.close(descriptor)
            lock.unlink(missing_ok=True)

    @staticmethod
    def _fsync_directory(path: Path) -> None:
        try:
            descriptor = os.open(path, os.O_RDONLY)
        except OSError:
            return  # Windows may not allow directory handles through os.open.
        try:
            os.fsync(descriptor)
        except OSError:
            pass  # The file itself was synced; directory fsync is platform-dependent.
        finally:
            os.close(descriptor)

    @staticmethod
    def _write_bytes_atomic(path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
            RunStore._fsync_directory(path.parent)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise

    @staticmethod
    def _write_json_atomic(path: Path, value: dict[str, Any]) -> None:
        data = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
        RunStore._write_bytes_atomic(path, data)

    def create(self, run_id: str) -> RunState:
        run_dir = self._run_dir(run_id)
        try:
            run_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError as exc:
            raise RunStoreError(f"{run_id} already exists") from exc
        self._write_state(run_id, RunState.CREATED)
        return RunState.CREATED

    def state(self, run_id: str) -> RunState | None:
        run_dir = self._run_dir(run_id)
        if (run_dir / "manifest.json").is_file():
            self.completed_manifest(run_id)
            return RunState.COMPLETED
        path = run_dir / "state.json"
        if not path.is_file():
            return None
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            if value.get("run_id") != run_id:
                raise ValueError("run id differs")
            return RunState(value["state"])
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, ValueError) as exc:
            raise RunStoreError(f"{run_id} has an invalid state file") from exc

    def begin(self, run_id: str) -> RunState:
        run_dir = self._run_dir(run_id)
        if self.state(run_id) is None:
            raise RunStoreError(f"{run_id} is not created")
        with self._exclusive(run_dir):
            return self._begin_locked(run_id)

    def _begin_locked(self, run_id: str) -> RunState:
        run_dir = self._run_dir(run_id)
        if self.state(run_id) is not RunState.CREATED:
            raise RunStoreError(f"{run_id} is not created")
        (run_dir / ".staging").mkdir(parents=True, exist_ok=True)
        self._staging_dir(run_dir)
        self._write_state(run_id, RunState.RUNNING)
        return RunState.RUNNING

    def fail(self, run_id: str, reason: str) -> RunState:
        run_dir = self._run_dir(run_id)
        with self._exclusive(run_dir):
            return self._fail_locked(run_id, reason)

    def _fail_locked(self, run_id: str, reason: str) -> RunState:
        if self.state(run_id) is not RunState.RUNNING:
            raise RunStoreError(f"{run_id} is not running")
        if not reason:
            raise RunStoreError("failure reason cannot be empty")
        self._write_json_atomic(
            self._run_dir(run_id) / "state.json",
            {
                "schema_version": 1,
                "run_id": run_id,
                "state": RunState.FAILED.value,
                "reason": reason,
            },
        )
        return RunState.FAILED

    def stage(self, run_id: str, relative: str, data: bytes) -> Path:
        run_dir = self._run_dir(run_id)
        with self._exclusive(run_dir):
            return self._stage_locked(run_id, relative, data)

    def _stage_locked(self, run_id: str, relative: str, data: bytes) -> Path:
        run_dir = self._run_dir(run_id)
        if self.state(run_id) is not RunState.RUNNING:
            raise RunStoreError(f"{run_id} is not running")
        target = self._artifact_path(self._staging_dir(run_dir), relative)
        self._write_bytes_atomic(target, data)
        return target

    def complete(self, run_id: str) -> dict[str, Any]:
        run_dir = self._run_dir(run_id)
        with self._exclusive(run_dir):
            return self._complete_locked(run_id)

    def _complete_locked(self, run_id: str) -> dict[str, Any]:
        run_dir = self._run_dir(run_id)
        final = run_dir / "manifest.json"
        if final.exists():
            manifest = self.completed_manifest(run_id)
            if manifest is None:  # pragma: no cover - defensive; exists was just checked
                raise RunStoreError(f"{run_id} manifest disappeared")
            return manifest
        if self.state(run_id) is not RunState.RUNNING:
            raise RunStoreError(f"{run_id} is not running")
        staging = self._staging_dir(run_dir)
        artifacts: dict[str, dict[str, int | str]] = {}
        staged_paths = sorted(staging.rglob("*"))
        if any(path.is_symlink() for path in staged_paths):
            raise RunStoreError("staged artifacts cannot contain a symlink")
        for path in (item for item in staged_paths if item.is_file()):
            if path.name.endswith(".tmp"):
                raise RunStoreError(f"temporary artifact remains: {path.name}")
            relative = path.relative_to(staging).as_posix()
            safe_path = self._artifact_path(staging, relative)
            data = safe_path.read_bytes()
            artifacts[relative] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        manifest: dict[str, Any] = {
            "schema_version": 1,
            "run_id": run_id,
            "state": "COMPLETED",
            "artifacts": artifacts,
        }
        self._write_json_atomic(final, manifest)
        return manifest

    def completed_manifest(self, run_id: str) -> dict[str, Any] | None:
        run_dir = self._run_dir(run_id)
        path = run_dir / "manifest.json"
        if not path.is_file():
            return None
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RunStoreError(f"{run_id} has an unreadable manifest") from exc
        expected_keys = {"schema_version", "run_id", "state", "artifacts"}
        if (
            type(manifest) is not dict
            or set(manifest) != expected_keys
            or manifest.get("schema_version") != 1
            or manifest.get("run_id") != run_id
            or manifest.get("state") != "COMPLETED"
            or type(manifest.get("artifacts")) is not dict
        ):
            raise RunStoreError(f"{run_id} has an invalid completion manifest")
        staging = self._staging_dir(run_dir)
        for relative, expected in manifest["artifacts"].items():
            if (
                type(expected) is not dict
                or set(expected) != {"bytes", "sha256"}
                or type(expected.get("bytes")) is not int
                or expected["bytes"] < 0
                or type(expected.get("sha256")) is not str
                or len(expected["sha256"]) != 64
                or any(character not in "0123456789abcdef" for character in expected["sha256"])
            ):
                raise RunStoreError(f"invalid artifact metadata: {relative}")
            self._artifact_path(staging, relative)
        actual = {
            path.relative_to(staging).as_posix()
            for path in staging.rglob("*")
            if path.is_file() or path.is_symlink()
        }
        if actual != set(manifest["artifacts"]):
            raise RunStoreError(f"{run_id} artifact inventory differs from manifest")
        for relative, expected in manifest["artifacts"].items():
            artifact = self._artifact_path(staging, relative)
            if not artifact.is_file():
                raise RunStoreError(f"completed artifact is missing: {relative}")
            data = artifact.read_bytes()
            if len(data) != expected.get("bytes") or hashlib.sha256(
                data
            ).hexdigest() != expected.get("sha256"):
                raise RunStoreError(f"completed artifact differs from manifest: {relative}")
        return manifest

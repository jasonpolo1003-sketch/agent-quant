"""A snapshot, once written, is never overwritten or deleted by a later run.

E5 (RUN-871299ea31) re-fetched unchanged pages on the same UTC day as E4, landed
on the same content-and-URL-hashed paths, and rewrote two E4 snapshots in place
(only ``captured_at`` changed), so E4's recorded file hashes stopped matching
the files on disk. A later run must instead get its own file. And because a
failed discovery discards the snapshots it wrote, it must never be able to
claim -- and so delete -- a file an earlier run wrote.
"""

import hashlib
from datetime import UTC, datetime

import pytest
from test_candidate_list_lane import (  # noqa: F401  (fixtures used by name)
    clean_handlers,
    dispatch_list,
    new_question,
    project,
    write_list,
)
from test_live_discovery import SUBSTANTIVE_BODY
from test_windowing import URLS, FakeOllama, WindowedFetcher

from quant_brain.discovery.live_discovery import (
    SNAPSHOT_DIR,
    LiveDiscoveryBackend,
    LiveDiscoveryError,
    save_source_snapshot,
    snapshot_relative_path,
)
from quant_brain.llm import ollama_client

URL = "https://example.com/page"
EARLY = datetime(2026, 9, 28, 2, 16, tzinfo=UTC)
LATER = datetime(2026, 9, 28, 4, 11, tzinfo=UTC)


def _hashes(root):
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (root / SNAPSHOT_DIR).rglob("*.md")
    }


def test_a_same_day_refetch_gets_its_own_file_and_leaves_the_first_untouched(tmp_path):
    first = save_source_snapshot(tmp_path, url=URL, content="Body.", captured_at=EARLY)
    before = (tmp_path / first).read_bytes()

    second = save_source_snapshot(tmp_path, url=URL, content="Body.", captured_at=LATER)

    assert first == snapshot_relative_path("Body.", URL, EARLY)
    assert second == first.removesuffix(".md") + ".2.md"
    assert (tmp_path / first).read_bytes() == before
    assert "captured_at: 2026-09-28T04:11:00+00:00" in (tmp_path / second).read_text(
        encoding="utf-8"
    )


def test_even_byte_identical_snapshots_never_share_a_file(tmp_path):
    """Reusing a path would let one run's cleanup delete another run's evidence."""
    first = save_source_snapshot(tmp_path, url=URL, content="Body.", captured_at=EARLY)
    second = save_source_snapshot(tmp_path, url=URL, content="Body.", captured_at=EARLY)
    third = save_source_snapshot(tmp_path, url=URL, content="Body.", captured_at=EARLY)

    assert len({first, second, third}) == 3
    assert third == first.removesuffix(".md") + ".3.md"
    assert (tmp_path / first).read_bytes() == (tmp_path / second).read_bytes()


def test_a_failed_discovery_cannot_delete_an_earlier_runs_snapshot(tmp_path):
    earlier = save_source_snapshot(
        tmp_path, url="https://arxiv.org/abs/2301.04567", content=SUBSTANTIVE_BODY,
        channel="web", backend="jina", title="One",
    )
    before = _hashes(tmp_path)
    calls = {"n": 0}

    def search_fn(question, method_family, *, limit):
        return [
            {"title": "One", "url": "https://arxiv.org/abs/2301.04567"},
            {"title": "Two", "url": "https://arxiv.org/abs/2301.09999"},
        ]

    def fetch_fn(url):
        calls["n"] += 1
        if calls["n"] > 1:
            raise LiveDiscoveryError("upstream timed out")
        return {"url": url, "content": SUBSTANTIVE_BODY, "channel": "web", "title": "One"}

    backend = LiveDiscoveryBackend(search_fn=search_fn, fetch_fn=fetch_fn)
    with pytest.raises(LiveDiscoveryError, match="timed out"):
        backend.discover("exit rules", None, project_root=tmp_path, limit=5)

    assert _hashes(tmp_path) == before  # its own snapshot discarded, the earlier one intact
    assert (tmp_path / earlier).is_file()


def test_repeat_dispatches_on_the_same_day_cannot_overwrite_existing_evidence(
    project, monkeypatch  # noqa: F811
):
    root, db_path = project
    monkeypatch.setattr(ollama_client, "generate", FakeOllama())

    first_id = new_question(db_path)
    first_list = write_list(root, first_id, list(URLS[:3]))
    assert dispatch_list(project, first_list, WindowedFetcher({URLS[1]}),
                         research_id=first_id, run_id="RUN-first").status == "completed"
    first_run = _hashes(root)

    second_id = new_question(db_path)
    second_list = write_list(root, second_id, list(URLS[:3]), name="second")
    assert dispatch_list(project, second_list, WindowedFetcher({URLS[1]}),
                         research_id=second_id, run_id="RUN-second").status == "completed"

    after = _hashes(root)
    assert {path: after[path] for path in first_run} == first_run  # byte-for-byte
    assert len(after) == 2 * len(first_run)  # the second run got its own files
    assert all(path.endswith(".2.md") for path in set(after) - set(first_run))


def test_the_writer_never_opens_an_existing_snapshot_for_writing(tmp_path, monkeypatch):
    first = save_source_snapshot(tmp_path, url=URL, content="Body.", captured_at=EARLY)
    target = (tmp_path / first).resolve()
    import pathlib

    real_open = pathlib.Path.open

    def guarded(self, mode="r", *args, **kwargs):
        if self.resolve() == target and any(flag in mode for flag in "wa+"):
            raise AssertionError(f"{first} was opened with mode {mode!r}")
        return real_open(self, mode, *args, **kwargs)

    monkeypatch.setattr(pathlib.Path, "open", guarded)
    monkeypatch.setattr(pathlib.Path, "write_text", lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("snapshots must be created exclusively, not with write_text")))

    save_source_snapshot(tmp_path, url=URL, content="Body.", captured_at=LATER)

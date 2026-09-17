from datetime import UTC, datetime
from pathlib import Path

import pytest

from quant_brain.discovery.live_discovery import (
    SNAPSHOT_DIR,
    LiveDiscoveryBackend,
    LiveDiscoveryError,
    SeededDiscoveryBackend,
    get_discovery_backend,
    save_source_snapshot,
    snapshot_relative_path,
)

FIXTURES = Path(__file__).parent / "fixtures"

# Long enough to clear the acquisition content floor, so these tests exercise
# snapshotting and path enforcement rather than thin-content rejection.
SUBSTANTIVE_BODY = " ".join(
    [
        "Wilder's relative strength index compares the magnitude of recent gains",
        "to recent losses over a lookback window of fourteen periods by default.",
        "The index is bounded between zero and one hundred, and readings below",
        "thirty are conventionally described as oversold while readings above",
        "seventy are described as overbought. The documentation notes that these",
        "thresholds are conventions rather than tested decision rules, and that",
        "the appropriate lookback and threshold depend on the instrument and the",
        "horizon being studied. Practitioners should confirm the exact smoothing",
        "method before relying on any particular implementation, because Wilder's",
        "original smoothing differs from a simple moving average of gains and",
        "losses and will produce different values on the same price series.",
    ]
    * 2
)


def test_save_source_snapshot_writes_canonical_source_snapshots_folder(tmp_path):
    relative = save_source_snapshot(
        tmp_path,
        url="https://example.com/rsi",
        content="Wilder RSI uses a 14-period default.",
        title="RSI",
        channel="web",
        backend="fixture",
    )

    assert relative.startswith(f"{SNAPSHOT_DIR}/")
    assert "00_Inbox/Snapshots/" not in relative
    written = tmp_path / relative
    assert written.exists()
    text = written.read_text(encoding="utf-8")
    assert "https://example.com/rsi" in text
    assert "Wilder RSI uses a 14-period default." in text
    name = written.name
    assert name.endswith(".md")
    stem = name[: -len(".md")]
    content_part, url_part = stem.split("-")
    assert len(content_part) == 12
    assert len(url_part) == 8


def test_identical_content_from_two_urls_keeps_both_identities(tmp_path):
    captured = datetime(2026, 9, 7, tzinfo=UTC)
    body = "Identical fetched body"
    first = save_source_snapshot(
        tmp_path,
        url="https://example.com/a",
        content=body,
        captured_at=captured,
    )
    second = save_source_snapshot(
        tmp_path,
        url="https://example.com/b",
        content=body,
        captured_at=captured,
    )

    assert first != second
    first_text = (tmp_path / first).read_text(encoding="utf-8")
    second_text = (tmp_path / second).read_text(encoding="utf-8")
    assert "https://example.com/a" in first_text
    assert "https://example.com/b" in second_text
    assert "https://example.com/b" not in first_text
    assert snapshot_relative_path(body, "https://example.com/a", captured) in first
    assert snapshot_relative_path(body, "https://example.com/b", captured) in second


def test_seeded_backend_is_the_test_double_not_a_second_agent():
    backend = get_discovery_backend("seeded")

    assert isinstance(backend, SeededDiscoveryBackend)
    assert backend.name == "seeded"
    result = backend.discover("ETF RSI mean reversion", "mean_reversion", limit=5)
    assert result.backend == "seeded"
    assert result.snapshots == ()
    assert len(result.sources) >= 3
    assert all("data_access" in source for source in result.sources)


def test_live_backend_without_search_fn_fails_closed_when_network_disabled():
    backend = LiveDiscoveryBackend()

    with pytest.raises(LiveDiscoveryError, match="network is disabled"):
        backend.discover("ETF RSI", "mean_reversion")


def test_live_backend_snapshots_fetched_pages(tmp_path):
    def search_fn(question, method_family, *, limit):
        assert limit == 5
        return [
            {
                "title": "RSI docs",
                "url": "https://example.com/rsi",
                "source_type": "docs",
            }
        ]

    def fetch_fn(url):
        assert url == "https://example.com/rsi"
        return {
            "url": url,
            "title": "RSI",
            "content": SUBSTANTIVE_BODY,
            "channel": "web",
            "backend": "fixture",
        }

    backend = LiveDiscoveryBackend(search_fn=search_fn, fetch_fn=fetch_fn)
    result = backend.discover(
        "exit rules for RSI",
        "mean_reversion",
        project_root=tmp_path,
        limit=5,
    )

    assert result.backend == "live"
    assert len(result.snapshots) == 1
    assert result.snapshots[0].startswith(f"{SNAPSHOT_DIR}/")
    assert (tmp_path / result.snapshots[0]).exists()
    assert result.sources[0]["data_access"] == "available-now"
    assert result.sources[0]["source_quality"] == "discovery-only"


def test_live_backend_honors_path_enforcement(tmp_path):
    from quant_brain.harness.paths import PathViolation, resolve_write_target

    allowed = ("brain/00_Inbox/Raw_Research/",)

    def resolve_write(target):
        return resolve_write_target(tmp_path, target, allowed)

    def search_fn(question, method_family, *, limit):
        return [{"title": "RSI", "url": "https://example.com/rsi", "source_type": "docs"}]

    def fetch_fn(url):
        return {
            "url": url,
            "content": SUBSTANTIVE_BODY,
            "channel": "web",
            "backend": "fixture",
        }

    backend = LiveDiscoveryBackend(search_fn=search_fn, fetch_fn=fetch_fn)
    with pytest.raises(PathViolation):
        backend.discover("RSI", None, project_root=tmp_path, resolve_write=resolve_write)


def test_forbidden_agent_reach_subcommands_are_rejected():
    """The live guard is the adapter's, not a second unused copy of it."""
    from quant_brain.discovery.agent_reach import AgentReachAdapter, AgentReachError

    adapter = AgentReachAdapter(exe="agent-reach", skip_exe_check=True)
    with pytest.raises(AgentReachError, match="install"):
        adapter._run(["agent-reach", "install", "web"])


def test_live_backend_assigns_the_classified_tier_instead_of_discovery_only(tmp_path):
    """The Gate C unlock: before this, every live source was discovery-only,
    so the curator could never promote anything the Scout found."""

    def search_fn(question, method_family, *, limit):
        return [
            {
                "title": "Mean Reversion Exit Rules in ETF Markets",
                "url": "https://arxiv.org/abs/2301.04567",
                "source_type": "paper",
            }
        ]

    def fetch_fn(url):
        return {"url": url, "content": SUBSTANTIVE_BODY, "channel": "web", "backend": "fixture"}

    backend = LiveDiscoveryBackend(search_fn=search_fn, fetch_fn=fetch_fn)
    result = backend.discover("exit rules", "mean_reversion", project_root=tmp_path)

    assert result.sources[0]["source_quality"] == "primary"


def test_a_search_hit_cannot_supply_its_own_source_quality(tmp_path):
    """Upstream results are untrusted input.

    If a hit could carry its own tier, any search result could claim `primary`
    and walk straight past the classifier into the curator's promotable set.
    """

    def search_fn(question, method_family, *, limit):
        return [
            {
                "title": "Totally legitimate",
                "url": "https://scam-blog.example/x",
                "source_quality": "primary",
            }
        ]

    def fetch_fn(url):
        return {"url": url, "content": SUBSTANTIVE_BODY, "channel": "web"}

    backend = LiveDiscoveryBackend(search_fn=search_fn, fetch_fn=fetch_fn)
    result = backend.discover("exit rules", None, project_root=tmp_path)

    assert result.sources[0]["source_quality"] == "discovery-only"


def test_a_page_rejected_after_fetch_is_backfilled_from_the_next_candidate(tmp_path):
    """A thin page must not quietly cost a source slot."""
    hits = [
        {"title": f"h{i}", "url": f"https://site{i}.example/page", "rank": i}
        for i in range(1, 6)
    ]

    def search_fn(question, method_family, *, limit):
        return hits

    def fetch_fn(url):
        # The first two fetched pages are thin; later ones are substantive.
        thin = url.startswith(("https://site1.", "https://site2."))
        return {"url": url, "content": "We use cookies." if thin else SUBSTANTIVE_BODY,
                "channel": "web"}

    backend = LiveDiscoveryBackend(search_fn=search_fn, fetch_fn=fetch_fn)
    result = backend.discover("exit rules", None, project_root=tmp_path, limit=3)

    assert len(result.sources) == 3, "rejected pages should be replaced, not deducted"
    assert len(result.snapshots) == 3


def test_live_backend_yields_at_least_one_promotable_candidate_from_a_mixed_search(tmp_path):
    """Gate C exit condition, at the backend boundary."""
    import json

    hits = json.loads(
        (FIXTURES / "acquisition_search_mixed.json").read_text(encoding="utf-8")
    )["results"]
    bodies = json.loads(
        (FIXTURES / "acquisition_fetch_bodies.json").read_text(encoding="utf-8")
    )

    def search_fn(question, method_family, *, limit):
        return hits

    def fetch_fn(url):
        return {
            "url": url,
            "content": bodies.get(url, SUBSTANTIVE_BODY),
            "channel": "web",
            "backend": "fixture",
        }

    backend = LiveDiscoveryBackend(search_fn=search_fn, fetch_fn=fetch_fn)
    result = backend.discover(
        "source supported exit rules for RSI mean reversion on ETFs",
        "mean_reversion",
        project_root=tmp_path,
        limit=5,
    )

    tiers = [source["source_quality"] for source in result.sources]
    assert any(tier in {"primary", "practitioner"} for tier in tiers)
    assert len(result.sources) <= 5
    assert len(result.snapshots) == len(result.sources)
    assert result.rejected


def test_a_rejected_page_is_never_snapshotted(tmp_path):
    """Snapshots exist for what reaches the model, not for what was discarded."""

    def search_fn(question, method_family, *, limit):
        return [
            {"title": "Good", "url": "https://arxiv.org/abs/2301.04567"},
            {"title": "Thin", "url": "https://seo-farm.example/rsi-guide"},
        ]

    def fetch_fn(url):
        if "seo-farm" in url:
            return {"url": url, "content": "We use cookies.", "channel": "web"}
        return {"url": url, "content": SUBSTANTIVE_BODY, "channel": "web"}

    backend = LiveDiscoveryBackend(search_fn=search_fn, fetch_fn=fetch_fn)
    result = backend.discover("exit rules", None, project_root=tmp_path, limit=5)

    assert len(result.sources) == 1
    assert len(result.snapshots) == 1
    snapshot_dir = tmp_path / SNAPSHOT_DIR
    written = list(snapshot_dir.rglob("*.md"))
    assert len(written) == 1, "the rejected page must leave no snapshot behind"
    assert any("seo-farm" in record["url"] for record in result.rejected)


def test_live_backend_removes_its_snapshots_when_a_later_fetch_fails(tmp_path):
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
        return {"url": url, "content": SUBSTANTIVE_BODY, "channel": "web"}

    backend = LiveDiscoveryBackend(search_fn=search_fn, fetch_fn=fetch_fn)
    with pytest.raises(LiveDiscoveryError, match="timed out"):
        backend.discover("exit rules", None, project_root=tmp_path, limit=5)

    leftovers = list((tmp_path / SNAPSHOT_DIR).rglob("*.md"))
    assert leftovers == [], "a failed run must not leave orphan snapshots"


def test_when_every_page_is_rejected_the_run_fails_rather_than_fabricating_evidence(tmp_path):
    def search_fn(question, method_family, *, limit):
        return [{"title": "Thin", "url": "https://seo-farm.example/rsi-guide"}]

    def fetch_fn(url):
        return {"url": url, "content": "We use cookies.", "channel": "web"}

    backend = LiveDiscoveryBackend(search_fn=search_fn, fetch_fn=fetch_fn)
    with pytest.raises(LiveDiscoveryError, match="rejected before extraction"):
        backend.discover("exit rules", None, project_root=tmp_path, limit=5)

    assert list((tmp_path / SNAPSHOT_DIR).rglob("*.md")) == []


def test_a_search_returning_only_promotional_material_fails_closed(tmp_path):
    def search_fn(question, method_family, *, limit):
        return [
            {"title": "Guaranteed returns", "url": "https://scam.example/go/x?ref=1"},
            {"title": "Enroll now masterclass", "url": "https://scam.example/course"},
        ]

    def fetch_fn(url):  # pragma: no cover - must never be reached
        raise AssertionError("rejected candidates must not be fetched")

    backend = LiveDiscoveryBackend(search_fn=search_fn, fetch_fn=fetch_fn)
    with pytest.raises(LiveDiscoveryError, match="no credible candidate"):
        backend.discover("exit rules", None, project_root=tmp_path, limit=5)


def test_jina_fetch_caps_the_number_of_bytes_it_reads(monkeypatch):
    """An unbounded read lets one oversized response blow up a capped run."""
    from contextlib import contextmanager

    from quant_brain.discovery import live_discovery

    seen: dict[str, int | None] = {}

    class _Response:
        def read(self, size=None):
            seen["size"] = size
            return b"body"

    @contextmanager
    def fake_urlopen(request, timeout=None):
        yield _Response()

    monkeypatch.setattr(live_discovery, "urlopen", fake_urlopen)
    live_discovery.jina_fetch("https://example.com/x")

    assert seen["size"] == live_discovery.MAX_FETCH_BYTES


def test_unknown_backend_name_is_rejected():
    with pytest.raises(ValueError, match="unknown discovery backend"):
        get_discovery_backend("web_crawler")

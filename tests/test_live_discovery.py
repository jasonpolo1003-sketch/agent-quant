import pytest

from quant_brain.discovery.live_discovery import (
    SNAPSHOT_DIR,
    LiveDiscoveryBackend,
    LiveDiscoveryError,
    SeededDiscoveryBackend,
    assert_not_forbidden_subcommand,
    get_discovery_backend,
    save_source_snapshot,
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


def test_seeded_backend_is_the_test_double_not_a_second_agent():
    backend = get_discovery_backend("seeded")

    assert isinstance(backend, SeededDiscoveryBackend)
    assert backend.name == "seeded"
    result = backend.discover("ETF RSI mean reversion", "mean_reversion", limit=5)
    assert result.backend == "seeded"
    assert result.snapshots == ()
    assert len(result.sources) >= 3
    assert all("data_access" in source for source in result.sources)


def test_live_backend_without_search_fn_fails_closed():
    backend = LiveDiscoveryBackend()

    with pytest.raises(LiveDiscoveryError, match="search function"):
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
            "content": "Wilder RSI uses relative strength.",
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
        return {"url": url, "content": "body", "channel": "web", "backend": "fixture"}

    backend = LiveDiscoveryBackend(search_fn=search_fn, fetch_fn=fetch_fn)
    with pytest.raises(PathViolation):
        backend.discover("RSI", None, project_root=tmp_path, resolve_write=resolve_write)


def test_forbidden_agent_reach_subcommands_are_rejected():
    with pytest.raises(LiveDiscoveryError, match="install"):
        assert_not_forbidden_subcommand("install")


def test_unknown_backend_name_is_rejected():
    with pytest.raises(ValueError, match="unknown discovery backend"):
        get_discovery_backend("web_crawler")

"""Discovery backends and source-snapshot provenance for the Research Scout.

Production discovery is the live Agent Reach / Jina path. The seeded starter
catalog is a test double behind the same interface, not a second assigned
agent. Pytest must inject search/fetch callables or select the seeded backend;
the default live fetch is never invoked from unit tests.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Protocol
from urllib.request import Request, urlopen

from quant_brain.config import PROJECT_ROOT

SNAPSHOT_DIR = "brain/00_Inbox/Source_Snapshots"
JINA_READER_PREFIX = "https://r.jina.ai/"
FORBIDDEN_SUBCOMMANDS = frozenset({"install", "uninstall", "configure"})

SearchFn = Callable[..., list[dict[str, Any]]]
FetchFn = Callable[[str], dict[str, Any]]
ResolveWriteFn = Callable[[str | Path], Path]


class LiveDiscoveryError(RuntimeError):
    """Raised when live discovery cannot proceed without inventing a scraper."""


@dataclass(frozen=True)
class DiscoverResult:
    sources: list[dict[str, Any]]
    snapshots: tuple[str, ...] = ()
    backend: str = "live"


class DiscoveryBackend(Protocol):
    name: str

    def discover(
        self,
        question: str,
        method_family: str | None,
        *,
        limit: int = 5,
        project_root: str | Path = PROJECT_ROOT,
        resolve_write: ResolveWriteFn | None = None,
    ) -> DiscoverResult: ...


def snapshot_relative_path(content: str, captured_at: datetime | None = None) -> str:
    """Return the canonical relative path for a source snapshot."""
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    day = (captured_at or datetime.now(timezone.utc)).strftime("%Y-%m-%d")
    return f"{SNAPSHOT_DIR}/{day}/{digest[:16]}.md"


def save_source_snapshot(
    project_root: str | Path,
    *,
    url: str,
    content: str,
    channel: str = "web",
    backend: str = "jina",
    title: str | None = None,
    captured_at: datetime | None = None,
    resolve_write: ResolveWriteFn | None = None,
) -> str:
    """Write a provenance snapshot under ``brain/00_Inbox/Source_Snapshots/``.

    ``resolve_write`` should be the scout handler's path-enforced resolver when
    called from dispatch. Direct callers (tests, CLIs) write relative to
    ``project_root``.
    """
    if not url.strip():
        raise ValueError("snapshot url cannot be empty")
    if not content:
        raise ValueError("snapshot content cannot be empty")

    captured = captured_at or datetime.now(timezone.utc)
    relative = snapshot_relative_path(content, captured)
    dest = resolve_write(relative) if resolve_write else Path(project_root) / relative
    dest.parent.mkdir(parents=True, exist_ok=True)

    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    text = (
        "---\n"
        f"url: {url}\n"
        f"title: {title or ''}\n"
        f"channel: {channel}\n"
        f"backend: {backend}\n"
        f"captured_at: {captured.isoformat()}\n"
        f"content_hash: {content_hash}\n"
        "---\n\n"
        f"{content.rstrip()}\n"
    )
    dest.write_text(text, encoding="utf-8")
    root = Path(project_root).resolve()
    try:
        return dest.resolve().relative_to(root).as_posix()
    except ValueError:
        return dest.as_posix()


def jina_fetch(url: str, *, timeout: int = 30) -> dict[str, Any]:
    """Fetch one URL through Jina Reader. Not used by pytest."""
    if not url.strip():
        raise LiveDiscoveryError("cannot fetch an empty url")
    request = Request(
        f"{JINA_READER_PREFIX}{url}",
        headers={"User-Agent": "quant-agent-brain/research-scout"},
        method="GET",
    )
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - caller supplied URL
        body = response.read().decode("utf-8", errors="replace")
    return {
        "url": url,
        "title": None,
        "content": body,
        "channel": "web",
        "backend": "jina",
    }


def _source_from_fetch(
    candidate: dict[str, Any],
    fetched: dict[str, Any],
    snapshot_path: str,
) -> dict[str, Any]:
    """Map a fetched page onto the raw-research source contract.

    Extraction quality is intentionally conservative: live wiring must produce
    a schema-valid source, not a durable claim. The curator quality gate still
    decides promotion.
    """
    content = fetched.get("content") or ""
    excerpt = " ".join(content.split())[:500] or "Fetched page contained no extractable text."
    return {
        "title": candidate.get("title") or fetched.get("title") or candidate["url"],
        "source_type": candidate.get("source_type") or "web",
        "url_or_citation": candidate["url"],
        "main_claim": candidate.get("main_claim") or excerpt,
        "evidence": candidate.get("evidence") or f"Snapshot: {snapshot_path}. {excerpt}",
        "possible_strategy_rule": candidate.get("possible_strategy_rule") or "",
        "risks": list(candidate.get("risks") or ["Live fetch is provenance, not proof of edge."]),
        "confidence": candidate.get("confidence") or "low",
        "source_quality": candidate.get("source_quality") or "discovery-only",
        "asset_classes": list(candidate.get("asset_classes") or []),
        "data_required": list(candidate.get("data_required") or []),
        "data_access": candidate.get("data_access") or "available-now",
        "mvp_testable": bool(candidate.get("mvp_testable", False)),
    }


class SeededDiscoveryBackend:
    """Deterministic starter-source catalog. Test double / offline stub."""

    name = "seeded"

    def discover(
        self,
        question: str,
        method_family: str | None,
        *,
        limit: int = 5,
        project_root: str | Path = PROJECT_ROOT,
        resolve_write: ResolveWriteFn | None = None,
    ) -> DiscoverResult:
        from quant_brain.research.executor import select_candidate_sources

        del project_root, resolve_write
        sources = select_candidate_sources(method_family, question, limit=limit)
        return DiscoverResult(sources=sources, snapshots=(), backend=self.name)


class LiveDiscoveryBackend:
    """Agent Reach / Jina live path with injectable I/O for hermetic tests."""

    name = "live"

    def __init__(
        self,
        *,
        search_fn: SearchFn | None = None,
        fetch_fn: FetchFn | None = None,
        allow_network: bool = False,
    ) -> None:
        self.search_fn = search_fn
        self.fetch_fn = fetch_fn
        self.allow_network = allow_network

    def discover(
        self,
        question: str,
        method_family: str | None,
        *,
        limit: int = 5,
        project_root: str | Path = PROJECT_ROOT,
        resolve_write: ResolveWriteFn | None = None,
    ) -> DiscoverResult:
        if self.search_fn is None:
            raise LiveDiscoveryError(
                "live discovery has no search function; Agent Reach is not available. "
                "Inject search_fn/fetch_fn or use the seeded backend in tests. "
                "Refusing to invent a scraper."
            )
        fetch_fn = self.fetch_fn
        if fetch_fn is None:
            if not self.allow_network:
                raise LiveDiscoveryError(
                    "live discovery has no fetch_fn and network is disabled; "
                    "inject a fetch fixture or pass allow_network=True"
                )
            fetch_fn = jina_fetch

        raw_candidates = self.search_fn(question, method_family, limit=limit)
        candidates = list(raw_candidates)[:limit]
        sources: list[dict[str, Any]] = []
        snapshots: list[str] = []
        for candidate in candidates:
            url = str(candidate.get("url") or candidate.get("url_or_citation") or "")
            if not url:
                raise LiveDiscoveryError(f"live candidate is missing a url: {candidate!r}")
            fetched = fetch_fn(url)
            snapshot_path = save_source_snapshot(
                project_root,
                url=url,
                content=str(fetched.get("content") or ""),
                channel=str(fetched.get("channel") or "web"),
                backend=str(fetched.get("backend") or "jina"),
                title=fetched.get("title") or candidate.get("title"),
                resolve_write=resolve_write,
            )
            snapshots.append(snapshot_path)
            mapped = dict(candidate)
            mapped["url"] = url
            sources.append(_source_from_fetch(mapped, fetched, snapshot_path))
        return DiscoverResult(sources=sources, snapshots=tuple(snapshots), backend=self.name)


def get_discovery_backend(
    name: str | None = None,
    **kwargs: Any,
) -> DiscoveryBackend:
    """Return the named discovery backend. Default is live; seeded is the stub."""
    key = (name or os.environ.get("QUANT_BRAIN_DISCOVERY") or "live").strip().lower()
    if key in {"seeded", "stub", "starter"}:
        return SeededDiscoveryBackend()
    if key in {"live", "agent-reach", "jina"}:
        return LiveDiscoveryBackend(**kwargs)
    raise ValueError(f"unknown discovery backend {key!r}; expected 'live' or 'seeded'")


def assert_not_forbidden_subcommand(subcommand: str) -> None:
    if subcommand in FORBIDDEN_SUBCOMMANDS:
        raise LiveDiscoveryError(
            f"refusing Agent Reach subcommand {subcommand!r}; "
            f"forbidden: {sorted(FORBIDDEN_SUBCOMMANDS)}"
        )

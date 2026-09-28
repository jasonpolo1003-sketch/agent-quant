"""Discovery backends and source-snapshot provenance for the Research Scout.

Production discovery is the live Agent Reach / Jina path. The seeded starter
catalog is a test double behind the same interface, not a second assigned
agent. Pytest never calls the default live fetch: tests inject an adapter
runner or select the seeded backend.
"""

from __future__ import annotations

import hashlib
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

from quant_brain.config import PROJECT_ROOT
from quant_brain.discovery.candidate_list import CandidateList

SNAPSHOT_DIR = "brain/00_Inbox/Source_Snapshots"
JINA_READER_PREFIX = "https://r.jina.ai/"
FORBIDDEN_SUBCOMMANDS = frozenset({"install", "uninstall", "configure"})
MAX_FETCH_BYTES = 2_000_000

SearchFn = Callable[..., list[dict[str, Any]]]
FetchFn = Callable[[str], dict[str, Any]]
ResolveWriteFn = Callable[[str | Path], Path]


class LiveDiscoveryError(RuntimeError):
    """Raised when live discovery cannot proceed without inventing a scraper."""


class DiscoveryDeadlineExceeded(LiveDiscoveryError):
    """The Scout's shared whole-run wall-clock deadline was exhausted."""


def _check_run_deadline(deadline: float | None) -> None:
    if deadline is not None and time.monotonic() >= deadline:
        raise DiscoveryDeadlineExceeded(
            "budget: Scout run exceeded its whole-run wall-clock deadline"
        )


@dataclass(frozen=True)
class DiscoverResult:
    sources: list[dict[str, Any]]
    snapshots: tuple[str, ...] = ()
    backend: str = "live"
    # Candidates considered and deliberately not used, as JSON-safe records.
    # Honest rejection is a valid outcome, so it travels with the result rather
    # than being dropped.
    rejected: tuple[dict[str, Any], ...] = ()


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
        deadline: float | None = None,
    ) -> DiscoverResult: ...


def normalize_snapshot_url(url: str) -> str:
    """Canonicalize a URL so equivalent forms share one identity hash."""
    parts = urlsplit(url.strip())
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, parts.query, ""))


def snapshot_relative_path(
    content: str,
    url: str,
    captured_at: datetime | None = None,
) -> str:
    """Return a provenance path unique to both content and upstream URL."""
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    url_hash = hashlib.sha256(normalize_snapshot_url(url).encode("utf-8")).hexdigest()
    day = (captured_at or datetime.now(UTC)).strftime("%Y-%m-%d")
    return f"{SNAPSHOT_DIR}/{day}/{content_hash[:12]}-{url_hash[:8]}.md"


MAX_SNAPSHOT_VERSIONS = 1000


def _create_snapshot_file(
    project_root: str | Path,
    relative: str,
    text: str,
    resolve_write: ResolveWriteFn | None,
) -> Path:
    """Create ``relative`` (or the next free ``.<n>.md`` sibling) exclusively.

    Mode ``"x"`` makes the existence check and the creation one atomic step, so
    no existing file is ever opened for writing, even by a concurrent writer.
    """
    stem = relative.removesuffix(".md")
    for version in range(1, MAX_SNAPSHOT_VERSIONS + 1):
        candidate = relative if version == 1 else f"{stem}.{version}.md"
        dest = resolve_write(candidate) if resolve_write else Path(project_root) / candidate
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            with dest.open("x", encoding="utf-8") as handle:
                handle.write(text)
        except FileExistsError:
            continue
        return dest
    raise LiveDiscoveryError(
        f"{MAX_SNAPSHOT_VERSIONS} snapshots already exist for {relative}; refusing to overwrite"
    )


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

    Filenames include both a content hash and a URL hash so two different
    upstreams that happen to return identical body text cannot overwrite each
    other's identity metadata.

    A snapshot is immutable once written. The same page fetched again on the
    same UTC day maps to the same name, so the new snapshot is created
    exclusively at the next free ``<name>.<n>.md`` instead. Never reused, even
    when byte-identical: a failed discovery deletes the snapshots it wrote, so
    sharing a file would let one run delete another run's evidence. (E5,
    RUN-871299ea31, rewrote two E4 snapshots in place before this.)
    """
    if not url.strip():
        raise ValueError("snapshot url cannot be empty")
    if not content:
        raise ValueError("snapshot content cannot be empty")

    captured = captured_at or datetime.now(UTC)
    relative = snapshot_relative_path(content, url, captured)

    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    url_hash = hashlib.sha256(normalize_snapshot_url(url).encode("utf-8")).hexdigest()
    text = (
        "---\n"
        f"url: {url}\n"
        f"title: {title or ''}\n"
        f"channel: {channel}\n"
        f"backend: {backend}\n"
        f"captured_at: {captured.isoformat()}\n"
        f"content_hash: {content_hash}\n"
        f"url_hash: {url_hash}\n"
        "---\n\n"
        f"{content.rstrip()}\n"
    )
    dest = _create_snapshot_file(project_root, relative, text, resolve_write)
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
    with urlopen(request, timeout=timeout) as response:
        # Bounded read: an unbounded one lets a single oversized or streaming
        # response exhaust memory on a run that is otherwise capped at 5 pages.
        body = response.read(MAX_FETCH_BYTES).decode("utf-8", errors="replace")
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
    tier: str = "discovery-only",
    snapshot_sha256: str | None = None,
) -> dict[str, Any]:
    """Map a fetched page onto the raw-research source contract.

    Extraction quality is intentionally conservative: live wiring must produce
    a schema-valid source, not a durable claim. The curator quality gate still
    decides promotion.

    ``tier`` comes from ``source_quality.classify_source`` and is assigned here,
    on the discovery side, because ``llm.validators`` treats ``source_quality``
    as a protected field the model may not alter. Classifying later would be
    rejected; classifying here is the only correct placement.

    Thin and empty pages never reach this function -- ``assess_fetched_content``
    rejects them first -- so there is no placeholder-excerpt path that would
    turn a blank page into a ``main_claim``.
    """
    content = fetched.get("content") or ""
    excerpt = " ".join(content.split())[:500]
    if not excerpt:
        raise LiveDiscoveryError(
            f"refusing to build a source from empty content: {candidate['url']}"
        )
    # ``confidence`` stays low and ``mvp_testable`` stays false regardless of
    # tier: a credible publisher is provenance, not a tested claim. Only the
    # model, under validation, may raise those.
    #
    # ``source_quality`` is NOT read from the candidate. Upstream search results
    # are untrusted input, and letting a hit carry its own tier would let any
    # result claim `primary` and bypass the classifier entirely.
    # ``snapshot_path``/``snapshot_sha256`` are carried as real keys, not merely
    # interpolated into ``evidence``. A failure after this point has to be able
    # to say *which file* holds the bytes the model was shown, and the failure
    # path reads exactly these keys. They were previously read but never set, so
    # every receipt recorded ``null`` for both.
    return {
        "title": candidate.get("title") or fetched.get("title") or candidate["url"],
        "source_type": candidate.get("source_type") or "web",
        "url_or_citation": candidate["url"],
        "main_claim": candidate.get("main_claim") or excerpt,
        "evidence": candidate.get("evidence") or f"Snapshot: {snapshot_path}. {excerpt}",
        "possible_strategy_rule": candidate.get("possible_strategy_rule") or "",
        "risks": list(candidate.get("risks") or ["Live fetch is provenance, not proof of edge."]),
        "confidence": candidate.get("confidence") or "low",
        "source_quality": tier,
        "asset_classes": list(candidate.get("asset_classes") or []),
        "data_required": list(candidate.get("data_required") or []),
        "data_access": candidate.get("data_access") or "available-now",
        "mvp_testable": bool(candidate.get("mvp_testable", False)),
        "snapshot_path": snapshot_path,
        "snapshot_sha256": snapshot_sha256,
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
        deadline: float | None = None,
    ) -> DiscoverResult:
        from quant_brain.research.executor import select_candidate_sources

        del project_root, resolve_write
        _check_run_deadline(deadline)
        sources = select_candidate_sources(method_family, question, limit=limit)
        return DiscoverResult(sources=sources, snapshots=(), backend=self.name)


class LiveDiscoveryBackend:
    """Agent Reach / Jina live path.

    Production CLI constructs this with ``allow_network=True`` and no injected
    callables; search/fetch then go through ``AgentReachAdapter``. Tests may
    still inject ``search_fn``/``fetch_fn`` or a fake adapter runner.
    """

    name = "live"

    def __init__(
        self,
        *,
        search_fn: SearchFn | None = None,
        fetch_fn: FetchFn | None = None,
        allow_network: bool = False,
        adapter: Any | None = None,
        candidate_list: CandidateList | None = None,
    ) -> None:
        self.search_fn = search_fn
        self.fetch_fn = fetch_fn
        self.allow_network = allow_network
        self.adapter = adapter
        # A pre-registered list (PROP-004) replaces search for this run; it
        # does not change anything after the candidate pool is formed.
        self.candidate_list = candidate_list
        self._last_question: str | None = None
        self._last_method_family: str | None = None

    def _adapter(self) -> Any:
        if self.adapter is None:
            from quant_brain.discovery.agent_reach import AgentReachAdapter

            self.adapter = AgentReachAdapter()
        return self.adapter

    @property
    def discovery_provenance(self) -> dict[str, Any] | None:
        """Identity of a pre-registered candidate list, or ``None`` for search."""
        if self.candidate_list is None:
            return None
        return self.candidate_list.as_provenance()

    @property
    def last_query_expression(self) -> str | None:
        """The generated search expression, when a lane recorded one.

        Surfaced so a sparse-result receipt can state exactly what was asked --
        without it a reader cannot tell a thin literature from a bad query. An
        adapter records the real expression; when a caller injects its own
        ``search_fn`` there is no adapter, so the deterministic expression the
        arXiv lane *would* have generated is reported instead, marked as such.
        Reads the adapter only if one already exists: asking for the query must
        never construct an adapter or touch the network. A run driven by a
        pre-registered candidate list asked no query, so it reports none.
        """
        if self.candidate_list is not None:
            return None
        recorded = getattr(self.adapter, "last_arxiv_query", None)
        if recorded:
            return recorded
        if self._last_question is None:
            return None
        from quant_brain.discovery.arxiv_search import build_arxiv_query

        generated = build_arxiv_query(self._last_question, self._last_method_family)
        return f"{generated} (derived; discovery used an injected search function)"

    def _resolve_search_fn(self) -> SearchFn:
        if self.search_fn is not None:
            return self.search_fn
        if not self.allow_network:
            raise LiveDiscoveryError(
                "live discovery has no search function and network is disabled; "
                "inject search_fn/adapter or pass allow_network=True"
            )
        return self._adapter().search_for_question

    def _resolve_fetch_fn(self) -> FetchFn:
        if self.fetch_fn is not None:
            return self.fetch_fn
        if not self.allow_network:
            raise LiveDiscoveryError(
                "live discovery has no fetch_fn and network is disabled; "
                "inject a fetch fixture or pass allow_network=True"
            )
        return self._adapter().fetch_web

    def discover(
        self,
        question: str,
        method_family: str | None,
        *,
        limit: int = 5,
        project_root: str | Path = PROJECT_ROOT,
        resolve_write: ResolveWriteFn | None = None,
        deadline: float | None = None,
    ) -> DiscoverResult:
        """Acquire at most ``limit`` credible sources, with snapshots.

        Pipeline order: search, normalize, dedupe, classify, rank, budget,
        fetch, assess, snapshot. Everything cheap happens before anything
        expensive, so promotional and duplicate URLs never cost a fetch.

        On the budget: ``limit`` caps *accepted sources*, not fetch attempts. A
        page rejected after fetch is replaced by the next non-rejected
        over-budget candidate, which costs another fetch, so attempts are
        bounded by the size of the deduplicated, non-rejected pool (at most the
        list length, when a pre-registered list drives the run).

        On snapshot ordering: the invariant is that nothing reaches the model
        unpersisted -- not that everything fetched is persisted. A page rejected
        for thin or promotional content never reaches the model, so it is
        deliberately *not* snapshotted; its audit trail is the rejection record.
        Do not reorder this to snapshot before assessing.
        """
        from quant_brain.discovery.acquisition import (
            assess_fetched_content,
            dedupe_candidates,
            rank_candidates,
        )

        _check_run_deadline(deadline)
        # Production search and fetch both use the adapter. Give every one of
        # its subprocess/HTTP calls the same absolute deadline, not a fresh
        # timeout budget. Injected test functions are checked before and after.
        if deadline is not None and (self.search_fn is None or self.fetch_fn is None):
            setattr(self._adapter(), "deadline", deadline)

        # Remembered so a sparse-result receipt can report what was searched
        # even when the caller injected its own search function.
        self._last_question = question
        self._last_method_family = method_family
        fetch_fn = self._resolve_fetch_fn()
        if self.candidate_list is not None:
            # The pool is exactly the pre-registered, relevance-screened list:
            # search is not consulted, so an off-topic hit cannot displace a
            # listed source. Each hit is the URL alone -- nothing an entry says
            # may reach the source record, and the tier comes from the
            # classifier like any other candidate.
            hits = [{"url": url, "source_type": "web"} for url in self.candidate_list.urls]
        else:
            search_fn = self._resolve_search_fn()
            raw_candidates = search_fn(question, method_family, limit=limit)
            _check_run_deadline(deadline)
            hits = [dict(hit) for hit in raw_candidates]
        if not hits:
            raise LiveDiscoveryError("live discovery search returned no candidates")

        deduped = dedupe_candidates(hits)
        if not deduped:
            raise LiveDiscoveryError("live discovery search returned no usable urls")
        accepted, rejected = rank_candidates(deduped, question, limit=limit)
        rejected_records = [candidate.as_record() for candidate in rejected]
        if not accepted:
            reasons = "; ".join(
                f"{record['url']}: {record['reason']}" for record in rejected_records[:5]
            )
            raise LiveDiscoveryError(
                f"no credible candidate survived acquisition for this question. {reasons}"
            )

        sources: list[dict[str, Any]] = []
        snapshots: list[str] = []
        # Key on the same fields the candidate builder reads, so a hit using
        # ``url_or_citation`` still finds its own record instead of collapsing
        # onto the empty-string key and losing its claim/evidence fields.
        by_url = {str(hit.get("url") or hit.get("url_or_citation") or ""): hit for hit in hits}
        # Candidates that lost the budget but were not rejected on quality, kept
        # in rank order so a post-fetch rejection can be backfilled rather than
        # silently shrinking the yield.
        backfill = [c for c in rejected if c.tier != "reject"]
        queue = list(accepted)
        try:
            while queue and len(sources) < limit:
                _check_run_deadline(deadline)
                candidate = queue.pop(0)
                url = candidate.url
                fetched = fetch_fn(url)
                _check_run_deadline(deadline)
                content = str(fetched.get("content") or "")
                title = str(fetched.get("title") or candidate.title or "")

                # Assess before snapshotting: a rejected page leaves no file.
                content_verdict = assess_fetched_content(url, content, title=title)
                if content_verdict is not None:
                    record = candidate.as_record()
                    record.update(
                        tier=content_verdict.tier,
                        reason=content_verdict.reason,
                        signals=list(content_verdict.signals),
                    )
                    rejected_records.append(record)
                    # Replace it from the next-best candidate rather than
                    # letting a thin page quietly cost a slot.
                    if backfill:
                        promoted = backfill.pop(0)
                        rejected_records = [r for r in rejected_records if r["url"] != promoted.url]
                        queue.append(promoted)
                    continue

                snapshot_path = save_source_snapshot(
                    project_root,
                    url=url,
                    content=content,
                    channel=str(fetched.get("channel") or "web"),
                    backend=str(fetched.get("backend") or "jina"),
                    title=fetched.get("title") or candidate.title,
                    resolve_write=resolve_write,
                )
                snapshots.append(snapshot_path)
                mapped = dict(by_url.get(url) or {})
                mapped["url"] = url
                mapped.setdefault("title", candidate.title)
                mapped.setdefault("source_type", candidate.source_type)
                # Same input ``save_source_snapshot`` hashes for the frontmatter
                # and the filename prefix, so this value is identical by
                # construction and the 12-char prefix stays a cross-check.
                sources.append(
                    _source_from_fetch(
                        mapped,
                        fetched,
                        snapshot_path,
                        tier=candidate.tier,
                        snapshot_sha256=hashlib.sha256(content.encode("utf-8")).hexdigest(),
                    )
                )
        except Exception:
            # This attempt owns exactly these files, and resolve_write may have
            # redirected them, so cleanup belongs here rather than in the
            # executor's fail-closed path.
            self._discard_snapshots(snapshots, project_root, resolve_write)
            raise

        if not sources:
            self._discard_snapshots(snapshots, project_root, resolve_write)
            reasons = "; ".join(
                f"{record['url']}: {record['reason']}" for record in rejected_records[:5]
            )
            raise LiveDiscoveryError(
                f"every fetched page was rejected before extraction. {reasons}"
            )

        return DiscoverResult(
            sources=sources,
            snapshots=tuple(snapshots),
            backend=self.name,
            rejected=tuple(rejected_records),
        )

    @staticmethod
    def _discard_snapshots(
        snapshots: list[str],
        project_root: str | Path,
        resolve_write: ResolveWriteFn | None,
    ) -> None:
        """Remove snapshots this attempt wrote, so a failure leaves no orphans."""
        root = Path(project_root)
        for relative in snapshots:
            try:
                path = resolve_write(relative) if resolve_write else root / relative
                Path(path).unlink(missing_ok=True)
            except OSError:
                # Cleanup is best effort; the original failure is what matters.
                continue


def get_discovery_backend(
    name: str | None = None,
    **kwargs: Any,
) -> DiscoveryBackend:
    """Return the named discovery backend. Default is live; seeded is the stub."""
    key = (name or os.environ.get("QUANT_BRAIN_DISCOVERY") or "live").strip().lower()
    if key in {"seeded", "stub", "starter"}:
        if kwargs.get("candidate_list") is not None:
            # The stub never fetches or runs the model, so a pre-registered list
            # handed to it would look like a run that validated nothing.
            raise ValueError("a pre-registered candidate list requires the live backend")
        return SeededDiscoveryBackend()
    if key in {"live", "agent-reach", "jina"}:
        return LiveDiscoveryBackend(**kwargs)
    raise ValueError(f"unknown discovery backend {key!r}; expected 'live' or 'seeded'")

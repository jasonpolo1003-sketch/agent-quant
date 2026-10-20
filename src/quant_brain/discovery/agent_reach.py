"""Thin Agent Reach adapter: doctor, then call the named upstream tools.

Agent Reach is a router + doctor, not a content wrapper. After ``doctor --json``
names an active backend, this module calls that upstream tool directly (Exa via
mcporter, GitHub via ``gh``, web pages via Jina Reader). It never invents a
scraper, never runs ``install``/``uninstall``/``configure``, and never reads
``~/.agent-reach/config.yaml``.
"""

from __future__ import annotations

import inspect
import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from quant_brain.discovery.arxiv_search import (
    ArxivSearchError,
    build_arxiv_query,
    search_arxiv,
)
from quant_brain.discovery.live_discovery import (
    FORBIDDEN_SUBCOMMANDS,
    LiveDiscoveryError,
    jina_fetch,
)
from quant_brain.discovery.source_quality import normalize_candidate_url

# Channel keys are exactly as `agent-reach doctor --json` emits them. Verified
# 2026-09-17 against a real doctor run: the search channel key is "exa_search".
# There is no "search" channel and no "exa" channel -- those were guesses, and
# because the recorded fixture repeated the same guesses, the Exa lane could
# never be selected while the suite stayed green. Do not invent these names;
# re-capture tests/fixtures/agent_reach_doctor_live.json instead.
ENABLED_CHANNELS = frozenset({"web", "github", "youtube", "rss", "exa_search"})
SEARCH_CHANNELS = ("exa_search",)
LOGIN_BACKED_CHANNELS = frozenset(
    {"reddit", "twitter", "facebook", "instagram", "xiaohongshu", "linkedin"}
)
URL_RE = re.compile(r"https?://[^\s\"'<>]+")
DEFAULT_WINDOWS_EXE = r"C:\Users\jason\.agent-reach-venv\Scripts\agent-reach.exe"

# Search returns a candidate pool this many times the source cap, so the ranker
# has something to choose between and post-fetch rejections can be backfilled.
# The cap on *fetched* sources is unchanged and still enforced downstream.
CANDIDATE_POOL_FACTOR = 3

# GitHub's search API rejects long queries with "Invalid search query". The
# documented cap is 256 characters, but the effective limit is lower and varies
# with content because GitHub also counts operators and terms -- one real
# research question was rejected at 252 and accepted at 230. We trim well below
# the documented cap rather than trying to reproduce GitHub's parser; a query
# this long is already a poor fit for a code-repository search.
GITHUB_QUERY_MAX_CHARS = 200


@dataclass(frozen=True)
class SearchLane:
    """One declared acquisition lane and how real it currently is.

    ``operational`` lanes are dispatched by ``search_for_question``.
    ``fixture-only`` lanes are exercised by recorded tests but not dispatched
    live. ``deferred`` lanes are declared so doctor output maps cleanly, and are
    never dispatched. Login-backed channels appear nowhere here by design.

    ``channel`` is ``None`` for a lane that Agent Reach does not route. Such a
    lane needs no account and no router, so its availability is independent of
    any doctor status -- reporting it under a channel would make an unrelated
    channel's health look like the reason it did or did not answer.
    """

    name: str
    channel: str | None
    status: str


SEARCH_LANES: tuple[SearchLane, ...] = (
    # ``name`` is our lane label; ``channel`` must be the real doctor key, or
    # ``None`` when the lane is not routed through Agent Reach at all.
    SearchLane("exa", "exa_search", "operational"),
    SearchLane("github", "github", "operational"),
    SearchLane("arxiv", None, "operational"),
    SearchLane("youtube", "youtube", "deferred"),
    SearchLane("rss", "rss", "deferred"),
)


def operational_lanes() -> tuple[SearchLane, ...]:
    return tuple(lane for lane in SEARCH_LANES if lane.status == "operational")


class AgentReachError(LiveDiscoveryError):
    """Raised when Agent Reach or an upstream backend cannot be used."""


class AgentReachUnavailable(AgentReachError):
    """Raised when the Agent Reach executable or doctor health check is unusable."""


@dataclass(frozen=True)
class ChannelHealth:
    channel: str
    status: str
    active_backend: str | None
    message: str


def resolve_agent_reach_exe(explicit: str | None = None) -> str:
    """Return the Agent Reach executable path, or raise if it is missing."""
    candidates = [
        explicit,
        os.environ.get("AGENT_REACH_EXE"),
        shutil.which("agent-reach"),
        DEFAULT_WINDOWS_EXE if Path(DEFAULT_WINDOWS_EXE).exists() else None,
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(candidate)
        if candidate and shutil.which(candidate):
            return candidate
    raise AgentReachUnavailable(
        "agent-reach executable not found; set AGENT_REACH_EXE or install Agent Reach. "
        "Refusing to invent a scraper."
    )


def _accepts_timeout(fn: Any) -> bool:
    """Whether ``fn`` declares a ``timeout`` parameter (or accepts **kwargs)."""
    try:
        parameters = inspect.signature(fn).parameters
    except (TypeError, ValueError):
        return False
    if "timeout" in parameters:
        return True
    return any(p.kind is inspect.Parameter.VAR_KEYWORD for p in parameters.values())


def _is_agent_reach_exe(argv0: str) -> bool:
    """Whether this command invokes agent-reach itself rather than an upstream tool."""
    stem = Path(str(argv0)).name.lower()
    for suffix in (".exe", ".cmd", ".bat"):
        stem = stem.removesuffix(suffix)
    return stem == "agent-reach"


def default_runner(
    argv: list[str],
    *,
    timeout: int = 60,
    **_kwargs: Any,
) -> subprocess.CompletedProcess[str]:
    """Run an argument list. Never uses shell=True.

    ``encoding``/``errors`` are not optional. ``text=True`` alone decodes with
    ``locale.getpreferredencoding(False)``, which is ``cp1252`` on this machine,
    while ``agent-reach doctor --json`` emits UTF-8 channel names such as
    "全网语义搜索". The locale decode then raises ``UnicodeDecodeError`` inside
    subprocess's reader thread -- where no caller can catch it -- leaving
    ``stdout`` as ``None`` so the caller sees a misleading ``TypeError`` from
    ``json.loads``. ``errors="replace"`` guarantees the caller always receives a
    ``str``: a genuinely undecodable byte becomes U+FFFD inside the payload
    rather than destroying the whole run.
    """
    return subprocess.run(
        argv,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
        shell=False,
    )


def plan_queries(
    question: str,
    method_family: str | None,
    *,
    max_queries: int = 3,
) -> list[str]:
    """Build a bounded, deterministic query list from one research question."""
    cleaned = " ".join((question or "").split())
    if not cleaned:
        raise AgentReachError("cannot plan search queries from an empty research question")
    queries = [cleaned]
    family = (method_family or "").strip()
    if family and family not in {"unclassified", "none"}:
        tagged = f"{family} {cleaned}"
        if tagged not in queries:
            queries.append(tagged)
    return queries[:max_queries]


def bound_github_query(query: str) -> str:
    """Trim a query to GitHub's search-API length limit, on a word boundary.

    GitHub rejects queries at or above 256 characters with "Invalid search
    query". A research question is routinely longer than that, so an unbounded
    query turns every GitHub search into a *malformed-query error* rather than
    an honest empty result -- which misreports why a lane found nothing.

    Trimming does not make a long question answerable by GitHub; it makes the
    answer truthful.
    """
    cleaned = " ".join((query or "").split())
    if len(cleaned) < GITHUB_QUERY_MAX_CHARS:
        return cleaned
    trimmed = cleaned[: GITHUB_QUERY_MAX_CHARS - 1]
    head, _, _tail = trimmed.rpartition(" ")
    return head or trimmed


def _as_completed(argv: list[str], result: Any) -> subprocess.CompletedProcess[str]:
    """Accept CompletedProcess or ``(returncode, stdout, stderr)`` from injected runners."""
    if isinstance(result, subprocess.CompletedProcess):
        return result
    if isinstance(result, tuple) and len(result) >= 2:
        code, stdout = result[0], result[1]
        stderr = result[2] if len(result) > 2 else ""
        return subprocess.CompletedProcess(argv, int(code), str(stdout or ""), str(stderr or ""))
    raise AgentReachError(f"runner returned unsupported result type {type(result).__name__}")


def parse_channel_health(raw: Any) -> dict[str, ChannelHealth]:
    """Parse ``agent-reach doctor --json`` into per-channel health records."""
    payload = raw
    if isinstance(raw, str):
        payload = json.loads(raw)
    if isinstance(payload, list):
        payload = {"channels": payload}
    if not isinstance(payload, dict):
        raise AgentReachError("doctor JSON must be an object keyed by channel")
    channels_blob = payload.get("channels", payload)
    if isinstance(channels_blob, list):
        mapping = {}
        for item in channels_blob:
            if isinstance(item, dict) and item.get("channel"):
                mapping[str(item["channel"])] = item
        channels_blob = mapping
    if not isinstance(channels_blob, dict):
        raise AgentReachError("doctor JSON has no channel map")
    health: dict[str, ChannelHealth] = {}
    for name, info in channels_blob.items():
        if not isinstance(info, dict):
            continue
        health[str(name)] = ChannelHealth(
            channel=str(name),
            status=str(info.get("status") or "unknown"),
            active_backend=info.get("active_backend"),
            message=str(info.get("message") or ""),
        )
    return health


def is_channel_usable(health: dict[str, ChannelHealth], channel: str) -> bool:
    """Report whether a zero-config channel may be used.

    Login-backed social channels stay off. ``status=ok`` is usable. ``warn`` on
    a zero-config channel is usable because doctor often skips live probes
    (``active_backend`` may be null even when the tool is present).
    """
    if channel in LOGIN_BACKED_CHANNELS:
        return False
    if channel not in ENABLED_CHANNELS:
        return False
    info = health.get(channel)
    if info is None:
        return False
    if info.status == "off":
        # Not configured upstream (e.g. exa_search before `mcporter config add`).
        # Rejected by statement rather than by falling through the warn branch,
        # so a future status value cannot become usable by accident.
        return False
    if info.status == "ok":
        return True
    # Anything not ok/warn stays unusable: the default is deny.
    return info.status == "warn"


def extract_search_hits(raw: str, *, source_type: str) -> list[dict[str, Any]]:
    """Parse upstream search JSON/text into ``{title, url, source_type}`` hits."""
    text = (raw or "").strip()
    if not text:
        return []
    parsed: Any = None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = None
    hits: list[dict[str, Any]] = []
    if isinstance(parsed, list):
        rows = parsed
    elif isinstance(parsed, dict):
        rows = parsed.get("results") or parsed.get("data") or parsed.get("items") or []
        if isinstance(rows, dict):
            rows = rows.get("results") or []
    else:
        rows = []
    if isinstance(rows, list):
        for item in rows:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url") or item.get("link") or item.get("href") or "").strip()
            if not url:
                continue
            url = prefer_arxiv_abstract(url)
            title = str(item.get("title") or item.get("name") or url)
            hit = {"title": title, "url": url, "source_type": source_type}
            if item.get("snippet") or item.get("description") or item.get("text"):
                hit["snippet"] = str(
                    item.get("snippet") or item.get("description") or item.get("text")
                )
            hits.append(hit)
    if hits:
        return _dedupe_hits(hits)
    for url in URL_RE.findall(text):
        hits.append({"title": url, "url": url.rstrip(").,]"), "source_type": source_type})
    return _dedupe_hits(hits)


_ARXIV_PDF_RE = re.compile(
    r"^(https?://(?:www\.)?arxiv\.org)/pdf/([\w.\-/]+?)(?:v\d+)?(?:\.pdf)?$", re.I
)


def prefer_arxiv_abstract(url: str) -> str:
    """Rewrite an arXiv PDF link to its abstract page.

    The abstract page carries title, authors, abstract, date and DOI as text --
    everything classification and traceability need -- while the PDF would need
    a binary parser and would break the UTF-8 snapshot contract. This is the
    whole arXiv lane: it promotes hits already found, rather than adding a
    second network dependency.
    """
    match = _ARXIV_PDF_RE.match(url.strip())
    if not match:
        return url
    return f"{match.group(1)}/abs/{match.group(2)}"


def _dedupe_hits(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse hits pointing at the same upstream page.

    Compares normalized URLs, so the same page arriving from two channels --
    or from one channel with and without a trailing slash -- consumes one
    budget slot rather than two.
    """
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for hit in hits:
        key = normalize_candidate_url(hit["url"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(hit)
    return unique


class AgentReachAdapter:
    """Doctor + upstream search/fetch, with an injectable subprocess runner."""

    def __init__(
        self,
        *,
        exe: str | None = None,
        runner: Any | None = None,
        fetch_impl: Any | None = None,
        timeout: int = 60,
        deadline: float | None = None,
        skip_exe_check: bool = False,
        arxiv_search_impl: Any | None = None,
    ) -> None:
        self.exe = exe if skip_exe_check and exe else (exe or os.environ.get("AGENT_REACH_EXE"))
        self._skip_exe_check = skip_exe_check
        self.runner = runner or default_runner
        self.fetch_impl = fetch_impl or jina_fetch
        self.timeout = timeout
        self.deadline = deadline
        # arXiv does not go through ``runner`` (it is HTTP, not a subprocess),
        # so an injected runner would not contain it. A caller that supplies its
        # own runner is running hermetically and must opt in explicitly, or the
        # lane would silently reach the network from inside a test.
        if arxiv_search_impl is not None:
            self.arxiv_search_impl: Any | None = arxiv_search_impl
        else:
            self.arxiv_search_impl = None if runner is not None else search_arxiv
        # The last arXiv expression generated, for run records and receipts,
        # and the last arXiv failure, so a lane fault is never reported as an
        # empty literature.
        self.last_arxiv_query: str | None = None
        self.last_arxiv_error: str | None = None

    def _executable(self) -> str:
        if self._skip_exe_check:
            return self.exe or "agent-reach"
        if self.exe:
            return resolve_agent_reach_exe(self.exe)
        return resolve_agent_reach_exe()

    def _remaining_timeout(self) -> float:
        if self.deadline is None:
            return float(self.timeout)
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise AgentReachError(
                "budget: Scout run exceeded its whole-run wall-clock deadline"
            )
        return min(float(self.timeout), remaining)

    def _run(self, argv: list[str]) -> subprocess.CompletedProcess[str]:
        if not argv:
            raise AgentReachError("refusing to run an empty command")
        # Guard the subcommand *position*, not every token. Scanning all tokens
        # refused any research question containing the word "install", which is
        # a false positive on a legitimate query. mcporter and gh are separate
        # executables that never take these subcommands, so the guard applies
        # only when we are invoking agent-reach itself.
        if _is_agent_reach_exe(argv[0]) and len(argv) > 1:
            subcommand = argv[1]
            if subcommand in FORBIDDEN_SUBCOMMANDS:
                raise AgentReachError(
                    f"refusing Agent Reach subcommand {subcommand!r}; "
                    f"forbidden: {sorted(FORBIDDEN_SUBCOMMANDS)}"
                )
        timeout = self._remaining_timeout()
        try:
            completed = _as_completed(argv, self.runner(argv, timeout=timeout))
        except subprocess.TimeoutExpired as exc:
            raise AgentReachError(f"command timed out after {timeout:.3f}s: {argv[0]}") from exc
        return completed

    def check_health(self) -> dict[str, ChannelHealth]:
        completed = self._run([self._executable(), "doctor", "--json"])
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "").strip()[:400]
            raise AgentReachUnavailable(
                f"agent-reach doctor failed (exit {completed.returncode}): {detail}"
            )
        if completed.stdout is None:
            # A decode failure on subprocess's reader thread nulls stdout while
            # still reporting exit 0. Say that plainly instead of letting
            # json.loads(None) raise a TypeError that points at the wrong line.
            raise AgentReachUnavailable(
                "agent-reach doctor exited 0 but produced no decodable stdout; "
                "check the runner's output encoding"
            )
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise AgentReachError("agent-reach doctor returned malformed JSON") from exc
        if isinstance(payload, dict) and payload.get("ok") is False:
            issues = (
                payload.get("issues")
                or payload.get("errors")
                or payload.get("message")
                or "unhealthy"
            )
            raise AgentReachUnavailable(f"agent-reach doctor reported unhealthy: {issues}")
        health = parse_channel_health(payload)
        if not health:
            raise AgentReachUnavailable("agent-reach doctor returned no channel records")
        return health

    def search_exa(self, query: str, *, limit: int) -> list[dict[str, Any]]:
        completed = self._run(
            [
                "mcporter",
                "call",
                "exa.web_search_exa",
                f"query={query}",
                f"numResults={limit}",
            ]
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "").strip()[:400]
            raise AgentReachError(f"mcporter Exa search failed: {detail}")
        return extract_search_hits(completed.stdout, source_type="web")

    def search_github(self, query: str, *, limit: int) -> list[dict[str, Any]]:
        completed = self._run(
            [
                "gh",
                "search",
                "repos",
                bound_github_query(query),
                "--json",
                "url,name,description",
                "--limit",
                str(limit),
            ]
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "").strip()[:400]
            raise AgentReachError(f"gh search failed: {detail}")
        hits = extract_search_hits(completed.stdout, source_type="repo")
        for hit in hits:
            if not hit.get("title") or hit["title"] == hit["url"]:
                parsed = urlparse(hit["url"])
                hit["title"] = parsed.path.strip("/") or hit["url"]
        return hits

    def search_arxiv(
        self, question: str, method_family: str | None, *, limit: int
    ) -> list[dict[str, Any]]:
        """Search arXiv with the one deterministic query transformation.

        The generated expression is stashed on the adapter so a caller can
        record exactly what was asked -- essential when the honest outcome is
        "the literature is thin" rather than "the lane failed".
        """
        expression = build_arxiv_query(question, method_family)
        self.last_arxiv_query = expression
        if self.arxiv_search_impl is None:
            raise ArxivSearchError("arXiv lane disabled for this adapter")
        return self.arxiv_search_impl(
            expression, limit=limit, timeout=self._remaining_timeout()
        )

    def fetch_web(self, url: str) -> dict[str, Any]:
        # Pass the timeout only when the implementation accepts one. Catching
        # TypeError instead would swallow a genuine TypeError raised inside the
        # fetch and silently retry it.
        if _accepts_timeout(self.fetch_impl):
            fetched = self.fetch_impl(url, timeout=self._remaining_timeout())
        else:
            self._remaining_timeout()
            fetched = self.fetch_impl(url)
        if isinstance(fetched, dict):
            return fetched
        return {
            "url": url,
            "title": None,
            "content": str(fetched),
            "channel": "web",
            "backend": "jina",
        }

    def search_for_question(
        self,
        question: str,
        method_family: str | None,
        *,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Health-check, then search usable zero-config channels. No injection required.

        Returns a bounded *candidate pool*, not the final source set. Truncating
        to ``limit`` here would make downstream ranking a no-op -- the caller
        could only ever reorder the hits the router happened to return first,
        which is exactly the SEO-favouring behaviour Gate C exists to fix. The
        pool is capped at ``CANDIDATE_POOL_FACTOR * limit`` so the run stays
        bounded while leaving the ranker something to choose between.
        """
        health = self.check_health()
        queries = plan_queries(question, method_family)
        hits: list[dict[str, Any]] = []
        search_usable = any(is_channel_usable(health, name) for name in SEARCH_CHANNELS)
        github_usable = is_channel_usable(health, "github")
        if not search_usable and not github_usable:
            raise AgentReachError(
                "no usable Agent Reach search channel (exa_search or github); "
                "run `uv run python scripts/agent_reach_check.py` to see which "
                "lanes are usable and why the others are not"
            )
        pool_target = max(1, limit) * CANDIDATE_POOL_FACTOR
        per_query = max(1, limit)
        if search_usable:
            for query in queries:
                hits.extend(self.search_exa(query, limit=per_query))
                if len(_dedupe_hits(hits)) >= pool_target:
                    break
        if github_usable and len(_dedupe_hits(hits)) < pool_target:
            hits.extend(self.search_github(queries[0], limit=per_query))
        if len(_dedupe_hits(hits)) < pool_target:
            # arXiv is a zero-account lane, so its availability is independent
            # of any Agent Reach channel's doctor status and it is not gated on
            # one. A lane failure here must not discard hits the other lanes
            # already found, so the error is swallowed deliberately; the caller
            # still sees an empty result if nothing at all was found.
            try:
                hits.extend(self.search_arxiv(question, method_family, limit=per_query))
            except ArxivSearchError as exc:
                # Keep the reason. "arXiv answered with nothing" and "arXiv did
                # not answer" are different findings, and reporting the second
                # as the first would misattribute a transport fault to the
                # literature.
                self.last_arxiv_error = str(exc)
        unique = _dedupe_hits(hits)[:pool_target]
        if not unique:
            detail = ""
            if self.last_arxiv_error:
                detail = f"; arXiv lane also failed: {self.last_arxiv_error}"
            raise AgentReachError(f"Agent Reach search returned no URLs{detail}")
        return unique

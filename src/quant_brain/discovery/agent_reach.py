"""Thin Agent Reach adapter: doctor, then call the named upstream tools.

Agent Reach is a router + doctor, not a content wrapper. After ``doctor --json``
names an active backend, this module calls that upstream tool directly (Exa via
mcporter, GitHub via ``gh``, web pages via Jina Reader). It never invents a
scraper, never runs ``install``/``uninstall``/``configure``, and never reads
``~/.agent-reach/config.yaml``.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from quant_brain.discovery.live_discovery import (
    FORBIDDEN_SUBCOMMANDS,
    LiveDiscoveryError,
    jina_fetch,
)

ENABLED_CHANNELS = frozenset({"web", "github", "youtube", "rss", "search", "exa"})
SEARCH_CHANNELS = ("search", "exa")
LOGIN_BACKED_CHANNELS = frozenset(
    {"reddit", "twitter", "facebook", "instagram", "xiaohongshu", "linkedin"}
)
URL_RE = re.compile(r"https?://[^\s\"'<>]+")
DEFAULT_WINDOWS_EXE = r"C:\Users\jason\.agent-reach-venv\Scripts\agent-reach.exe"


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


def default_runner(
    argv: list[str],
    *,
    timeout: int = 60,
    **_kwargs: Any,
) -> subprocess.CompletedProcess[str]:
    """Run an argument list. Never uses shell=True."""
    return subprocess.run(
        argv,
        capture_output=True,
        text=True,
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
    if info.status == "ok":
        return True
    return info.status == "warn" and channel in ENABLED_CHANNELS


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
            title = str(item.get("title") or item.get("name") or url)
            hits.append({"title": title, "url": url, "source_type": source_type})
    if hits:
        return _dedupe_hits(hits)
    for url in URL_RE.findall(text):
        hits.append({"title": url, "url": url.rstrip(").,]"), "source_type": source_type})
    return _dedupe_hits(hits)


def _dedupe_hits(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for hit in hits:
        url = hit["url"]
        if url in seen:
            continue
        seen.add(url)
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
        skip_exe_check: bool = False,
    ) -> None:
        self.exe = exe if skip_exe_check and exe else (exe or os.environ.get("AGENT_REACH_EXE"))
        self._skip_exe_check = skip_exe_check
        self.runner = runner or default_runner
        self.fetch_impl = fetch_impl or jina_fetch
        self.timeout = timeout

    def _executable(self) -> str:
        if self._skip_exe_check:
            return self.exe or "agent-reach"
        if self.exe:
            return resolve_agent_reach_exe(self.exe)
        return resolve_agent_reach_exe()

    def _run(self, argv: list[str]) -> subprocess.CompletedProcess[str]:
        if not argv:
            raise AgentReachError("refusing to run an empty command")
        for part in argv:
            if part in FORBIDDEN_SUBCOMMANDS:
                raise AgentReachError(
                    f"refusing Agent Reach subcommand {part!r}; "
                    f"forbidden: {sorted(FORBIDDEN_SUBCOMMANDS)}"
                )
        try:
            completed = _as_completed(argv, self.runner(argv, timeout=self.timeout))
        except subprocess.TimeoutExpired as exc:
            raise AgentReachError(f"command timed out after {self.timeout}s: {argv[0]}") from exc
        return completed

    def check_health(self) -> dict[str, ChannelHealth]:
        completed = self._run([self._executable(), "doctor", "--json"])
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "").strip()[:400]
            raise AgentReachUnavailable(
                f"agent-reach doctor failed (exit {completed.returncode}): {detail}"
            )
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise AgentReachError("agent-reach doctor returned malformed JSON") from exc
        if isinstance(payload, dict) and payload.get("ok") is False:
            issues = payload.get("issues") or payload.get("errors") or payload.get("message") or "unhealthy"
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
                query,
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

    def fetch_web(self, url: str) -> dict[str, Any]:
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
        """Health-check, then search usable zero-config channels. No injection required."""
        health = self.check_health()
        queries = plan_queries(question, method_family)
        hits: list[dict[str, Any]] = []
        search_usable = any(is_channel_usable(health, name) for name in SEARCH_CHANNELS)
        github_usable = is_channel_usable(health, "github")
        if not search_usable and not github_usable:
            raise AgentReachError(
                "no usable Agent Reach search channel (Exa/mcporter or GitHub); "
                "run `agent-reach doctor --json` and install a zero-config backend"
            )
        per_query = max(1, limit)
        if search_usable:
            for query in queries:
                hits.extend(self.search_exa(query, limit=per_query))
                if len(_dedupe_hits(hits)) >= limit:
                    break
        if github_usable and len(_dedupe_hits(hits)) < limit:
            hits.extend(self.search_github(queries[0], limit=per_query))
        unique = _dedupe_hits(hits)[:limit]
        if not unique:
            raise AgentReachError("Agent Reach search returned no URLs")
        return unique

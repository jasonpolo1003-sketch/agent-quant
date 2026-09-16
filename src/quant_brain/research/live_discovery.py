from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

PRIMARY_DOMAINS = {
    "aqr.com",
    "arxiv.org",
    "blackrock.com",
    "cftc.gov",
    "cmegroup.com",
    "janestreet.com",
    "man.com",
    "quantconnect.com",
    "sec.gov",
    "ssrn.com",
    "stockcharts.com",
    "twosigma.com",
}
PRACTITIONER_DOMAINS = {
    "alphaarchitect.com",
    "hudsonthames.org",
    "qoppac.blogspot.com",
    "quantstart.com",
    "robotwealth.com",
}
STOP_WORDS = {
    "a",
    "an",
    "and",
    "for",
    "from",
    "in",
    "of",
    "on",
    "or",
    "the",
    "that",
    "to",
    "with",
}
SEARCH_NOISE_WORDS = STOP_WORDS | {
    "backtest",
    "compare",
    "could",
    "do",
    "explain",
    "find",
    "fixed",
    "future",
    "high",
    "most",
    "not",
    "optimize",
    "optimized",
    "pair",
    "propose",
    "quality",
    "simple",
    "source",
    "sources",
    "supported",
    "two",
}


@dataclass
class DiscoveryCandidate:
    title: str
    url: str
    snippet: str = ""
    source_quality: str = "discovery-only"
    score: float = 0.0
    search_rank: int | None = None


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    host = (parts.hostname or "").lower()
    netloc = host
    if parts.port:
        netloc = f"{host}:{parts.port}"
    path = parts.path.rstrip("/") or ""
    return urlunsplit((parts.scheme.lower() or "https", netloc, path, parts.query, ""))


def classify_source_quality(url: str) -> str:
    host = (urlsplit(url).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if any(host == domain or host.endswith(f".{domain}") for domain in PRIMARY_DOMAINS):
        return "primary"
    if any(
        host == domain or host.endswith(f".{domain}") for domain in PRACTITIONER_DOMAINS
    ):
        return "practitioner"
    return "discovery-only"


def parse_search_results(raw: str, query: str = "") -> list[DiscoveryCandidate]:
    payload = json.loads(raw)
    if not isinstance(payload, list):
        raise ValueError("search output must be a JSON list")
    candidates = []
    for item in payload:
        if not isinstance(item, dict) or not item.get("url"):
            continue
        url = normalize_url(str(item["url"]))
        candidates.append(
            DiscoveryCandidate(
                title=str(item.get("title") or url),
                url=url,
                snippet=str(item.get("snippet") or ""),
                source_quality=classify_source_quality(url),
                search_rank=int(item["rank"]) if item.get("rank") is not None else None,
            )
        )
    return candidates


def _query_terms(query: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", query.lower())
        if len(token) > 2 and token not in STOP_WORDS
    }


def _candidate_score(candidate: DiscoveryCandidate, query: str) -> float:
    terms = _query_terms(query)
    text_terms = set(
        re.findall(r"[a-z0-9]+", f"{candidate.title} {candidate.snippet}".lower())
    )
    overlap = len(terms.intersection(text_terms))
    quality_bonus = {
        "primary": 4.0,
        "practitioner": 2.0,
        "discovery-only": 0.0,
        "reject": -5.0,
    }.get(candidate.source_quality, 0.0)
    rank_bonus = 1.0 / candidate.search_rank if candidate.search_rank else 0.0
    return overlap + quality_bonus + rank_bonus


def dedupe_and_rank(
    candidates: list[DiscoveryCandidate], query: str, limit: int = 15
) -> list[DiscoveryCandidate]:
    if limit < 1:
        return []
    unique: dict[str, DiscoveryCandidate] = {}
    for candidate in candidates:
        normalized = normalize_url(candidate.url)
        scored = replace(
            candidate,
            url=normalized,
            source_quality=classify_source_quality(normalized),
        )
        scored.score = _candidate_score(scored, query)
        existing = unique.get(normalized)
        if existing is None or scored.score > existing.score:
            unique[normalized] = scored
    return sorted(unique.values(), key=lambda item: (-item.score, item.url))[:limit]


def save_source_snapshot(
    project_root: str | Path,
    *,
    research_id: str,
    source_id: str,
    candidate: DiscoveryCandidate,
    fetched_text: str,
) -> dict[str, Any]:
    root = Path(project_root)
    out_dir = root / "brain" / "00_Inbox" / "Source_Snapshots" / research_id
    out_dir.mkdir(parents=True, exist_ok=True)
    content_hash = hashlib.sha256(fetched_text.encode("utf-8")).hexdigest()
    path = out_dir / f"{source_id}.md"
    text = f"""---
source_id: {source_id}
research_id: {research_id}
source_quality: {candidate.source_quality}
url: {candidate.url}
content_hash: {content_hash}
---

# {candidate.title}

## Discovery Snippet

{candidate.snippet or 'None'}

## Fetched Content

{fetched_text.strip()}
"""
    path.write_text(text, encoding="utf-8")
    return {
        "source_id": source_id,
        "title": candidate.title,
        "url": candidate.url,
        "source_quality": candidate.source_quality,
        "snapshot_path": str(path),
        "content_hash": content_hash,
        "text": fetched_text,
    }


def build_opencli_search_command(
    query: str,
    *,
    executable: str | None = None,
    windows: bool | None = None,
    comspec: str | None = None,
    node_executable: str | None = None,
    opencli_script: str | None = None,
) -> list[str]:
    windows = os.name == "nt" if windows is None else windows
    executable = executable or shutil.which("opencli.cmd") or shutil.which("opencli") or "opencli"
    args = [executable, "yahoo", "search", query, "-f", "json"]
    if windows and executable.lower().endswith((".cmd", ".bat")):
        inferred_script = (
            Path(executable).parent
            / "node_modules"
            / "@jackwener"
            / "opencli"
            / "dist"
            / "src"
            / "main.js"
        )
        script = Path(opencli_script) if opencli_script else inferred_script
        node = node_executable or shutil.which("node.exe") or shutil.which("node")
        if node and (opencli_script is not None or script.exists()):
            return [node, str(script), "yahoo", "search", query, "-f", "json"]
        command_line = subprocess.list2cmdline(args)
        return [
            comspec or os.environ.get("COMSPEC", "cmd.exe"),
            "/d",
            "/s",
            "/c",
            command_line,
        ]
    return args


def condense_search_query(question: str, max_chars: int = 160) -> str:
    tokens = re.findall(r"[A-Za-z0-9]+", question)
    selected: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        lower = token.lower()
        if lower in SEARCH_NOISE_WORDS or len(lower) < 3 or lower in seen:
            continue
        candidate = " ".join([*selected, token])
        if len(candidate) > max_chars:
            break
        selected.append(token)
        seen.add(lower)
    return " ".join(selected) or question[:max_chars].strip()


def run_yahoo_search(query: str, timeout: int = 180) -> list[DiscoveryCandidate]:
    search_query = condense_search_query(query)
    completed = subprocess.run(
        build_opencli_search_command(search_query),
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return parse_search_results(completed.stdout, query=query)


def fetch_with_jina(url: str, timeout: int = 60) -> str:
    request = Request(
        f"https://r.jina.ai/{url}",
        headers={"User-Agent": "quant-agent-brain/0.1"},
    )
    with urlopen(request, timeout=timeout) as response:
        text = response.read(2_000_000).decode("utf-8", errors="ignore")
    if not text.strip():
        raise ValueError(f"empty source response: {url}")
    return text

"""Bounded candidate acquisition: dedupe, rank, budget, and reject.

Sits between search and fetch. Search returns whatever the upstream router
found, in whatever order; this module decides which few of those are worth
spending a fetch, a snapshot and a model call on.

The pipeline is deliberately ordered so that the cheapest rejections happen
first:

    normalize -> dedupe -> classify -> rank -> budget -> fetch -> assess

Everything here is pure and deterministic: no network, no disk, no database.
The backend in ``live_discovery`` owns the IO and calls into these functions.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, replace
from typing import Any

from quant_brain.discovery.source_quality import (
    SourceVerdict,
    classify_source,
    normalize_candidate_url,
)

# A page shorter than this is boilerplate, an error shell, or a paywall stub --
# not evidence. Calibrated against the recorded arXiv abstract fixture, which
# is a genuine short page and must survive.
MIN_CONTENT_CHARS = 600
MIN_CONTENT_WORDS = 120

_STOP_WORDS = frozenset(
    {
        "and",
        "are",
        "can",
        "for",
        "from",
        "has",
        "how",
        "its",
        "not",
        "que",
        "that",
        "the",
        "them",
        "this",
        "was",
        "were",
        "what",
        "when",
        "which",
        "with",
        "you",
    }
)

_WORD_RE = re.compile(r"[a-z0-9]+")

# Shells that return HTTP 200 with no usable content.
_BOILERPLATE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "cookie-banner",
        re.compile(
            r"^\W*(?:we use cookies|this (?:site|website) uses cookies|"
            r"accept (?:all )?cookies|cookie (?:policy|consent))",
            re.IGNORECASE,
        ),
    ),
    (
        "javascript-required",
        re.compile(
            r"enable javascript|javascript is (?:required|disabled)|"
            r"please turn on javascript",
            re.IGNORECASE,
        ),
    ),
    (
        "access-denied",
        re.compile(
            r"^\W*(?:403 forbidden|404 not found|access denied|"
            r"are you a robot|verify you are human|attention required)",
            re.IGNORECASE,
        ),
    ),
    (
        "paywall",
        re.compile(
            r"subscribe to (?:continue|read)|this article is for subscribers|"
            r"create a free account to (?:read|continue)",
            re.IGNORECASE,
        ),
    ),
)

_TIER_BONUS = {
    "primary": 4.0,
    "practitioner": 2.0,
    "discovery-only": 0.0,
}

# Topical overlap can never outweigh the practitioner tier bonus on its own.
# Keyword density is the one signal an SEO page fully controls; credibility is
# not. A discovery-only page can still win a slot on rank when nothing better
# is available -- it just cannot outrank real evidence by stuffing terms.
_MAX_OVERLAP_CONTRIBUTION = 1.9


@dataclass(frozen=True)
class Candidate:
    """One search hit, with its tier decided but not yet fetched."""

    url: str
    title: str = ""
    snippet: str = ""
    source_type: str = "web"
    rank: int | None = None
    verdict: SourceVerdict | None = None
    score: float = 0.0

    @property
    def tier(self) -> str:
        return self.verdict.tier if self.verdict else "discovery-only"

    def as_record(self) -> dict[str, Any]:
        """Flat, JSON-safe form for events and reports."""
        return {
            "url": self.url,
            "title": self.title,
            "source_type": self.source_type,
            "rank": self.rank,
            "tier": self.tier,
            "reason": self.verdict.reason if self.verdict else "",
            "signals": list(self.verdict.signals) if self.verdict else [],
            "score": self.score,
        }


def _candidate_from_hit(hit: dict[str, Any], rank: int | None) -> Candidate:
    url = str(hit.get("url") or hit.get("url_or_citation") or "").strip()
    title = str(hit.get("title") or "")
    snippet = str(hit.get("snippet") or hit.get("description") or "")
    return Candidate(
        url=url,
        title=title,
        snippet=snippet,
        source_type=str(hit.get("source_type") or "web"),
        rank=hit.get("rank") if hit.get("rank") is not None else rank,
        verdict=classify_source(url, title=title, snippet=snippet) if url else None,
    )


def dedupe_candidates(hits: list[dict[str, Any]]) -> list[Candidate]:
    """Collapse hits that are the same upstream page.

    Keyed on the normalized URL, so ``.../rsi.asp`` and ``.../rsi.asp/`` from
    two different channels consume one budget slot rather than two. First seen
    wins, but a better (lower) search rank is kept, since rank feeds scoring.
    """
    seen: dict[str, Candidate] = {}
    for position, hit in enumerate(hits, start=1):
        candidate = _candidate_from_hit(hit, position)
        if not candidate.url:
            continue
        key = normalize_candidate_url(candidate.url)
        existing = seen.get(key)
        if existing is None:
            seen[key] = candidate
            continue
        if candidate.rank is not None and (existing.rank is None or candidate.rank < existing.rank):
            seen[key] = replace(existing, rank=candidate.rank)
    return list(seen.values())


def _query_terms(query: str) -> set[str]:
    return {
        token
        for token in _WORD_RE.findall(query.lower())
        if len(token) > 2 and token not in _STOP_WORDS
    }


def score_candidate(candidate: Candidate, query: str) -> float:
    """Rank by tier first, then topical overlap, then upstream rank.

    A rejected candidate scores ``-inf`` rather than a finite penalty. With a
    finite penalty a rejected page with high term overlap can out-score a clean
    discovery-only one and climb back into the budget, which is exactly the
    failure this ordering exists to prevent.
    """
    if candidate.tier == "reject":
        return -math.inf
    terms = _query_terms(query)
    text_terms = set(_WORD_RE.findall(f"{candidate.title} {candidate.snippet}".lower()))
    overlap = float(len(terms & text_terms))
    rank_bonus = 1.0 / candidate.rank if candidate.rank else 0.0
    # Term overlap alone is what SEO pages optimize for, so cap its contribution
    # below the practitioner bonus. Otherwise a keyword-stuffed page outranks a
    # credible source and costs a fetch before the content floor catches it.
    overlap = min(overlap, _MAX_OVERLAP_CONTRIBUTION)
    return overlap + _TIER_BONUS.get(candidate.tier, 0.0) + rank_bonus


def rank_candidates(
    candidates: list[Candidate],
    query: str,
    *,
    limit: int,
) -> tuple[list[Candidate], list[Candidate]]:
    """Order by credibility and relevance, then cut to the budget.

    Returns ``(accepted, rejected)``. Rejected carries both Tier-D candidates
    and those that simply lost the budget, so the caller can record honestly
    why each URL did not become a source.
    """
    if limit < 1:
        return [], list(candidates)

    scored = [replace(c, score=score_candidate(c, query)) for c in candidates]
    tier_d = [c for c in scored if c.tier == "reject"]
    eligible = [c for c in scored if c.tier != "reject"]
    eligible.sort(key=lambda c: (-c.score, c.url))

    accepted = eligible[:limit]
    # Losing the budget is not a quality judgment. Keep the candidate's real
    # tier but say plainly why it was not used, so the ledger does not imply
    # a credible source was found wanting.
    over_budget = [
        replace(
            c,
            verdict=SourceVerdict(
                c.tier,
                f"not used: ranked below the {limit}-source budget for this run",
                (c.verdict.signals if c.verdict else ()) + ("over-budget",),
            ),
        )
        for c in eligible[limit:]
    ]
    return accepted, tier_d + over_budget


def assess_fetched_content(url: str, content: str, *, title: str = "") -> SourceVerdict | None:
    """Judge fetched page text. ``None`` means the page may become a source.

    Runs after fetch but *before* any snapshot is written, so a cookie banner
    never reaches the model and never leaves a file behind. Body evidence is
    downgrade-only: it can reject, never promote.
    """
    text = (content or "").strip()
    if not text:
        return SourceVerdict("reject", f"fetched page was empty: {url}", ("empty-content",))

    collapsed = " ".join(text.split())
    for name, pattern in _BOILERPLATE_PATTERNS:
        if pattern.search(collapsed[:400]):
            return SourceVerdict(
                "reject",
                f"page body is {name.replace('-', ' ')} rather than content",
                (name,),
            )

    word_count = len(collapsed.split())
    if len(collapsed) < MIN_CONTENT_CHARS or word_count < MIN_CONTENT_WORDS:
        return SourceVerdict(
            "reject",
            (
                f"page body is too thin to be evidence "
                f"({len(collapsed)} chars, {word_count} words; "
                f"floor {MIN_CONTENT_CHARS} chars / {MIN_CONTENT_WORDS} words)"
            ),
            ("thin-content",),
        )

    body_verdict = classify_source(url, title=title, body=collapsed)
    if body_verdict.is_rejected:
        return body_verdict
    return None


def rejection_ledger_markdown(rejected: list[Candidate]) -> str:
    """Human-readable record of what was not used, and why.

    Honest rejection is a valid outcome, so it is reported rather than
    silently dropped. The machine-readable form is the ops event.
    """
    if not rejected:
        return ""
    lines = [
        "## Rejected Candidates",
        "",
        "Considered during bounded acquisition and deliberately not used as evidence.",
        "",
        "| URL | Tier | Reason |",
        "| --- | --- | --- |",
    ]
    for candidate in rejected:
        reason = (candidate.verdict.reason if candidate.verdict else "not selected").replace(
            "|", "\\|"
        )
        lines.append(f"| {candidate.url} | {candidate.tier} | {reason} |")
    return "\n".join(lines) + "\n"

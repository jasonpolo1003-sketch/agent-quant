"""Independent zero-account discovery over arXiv's public Atom API.

This lane is deliberately *not* an Agent Reach channel. arXiv needs no account,
no API key and no router: it is reachable whenever the network is, so tying its
availability to the Jina/`web` channel's doctor status would misreport why
discovery failed -- a healthy Jina fetcher says nothing about whether arXiv
answered, and vice versa.

It exists because the only two lanes that could turn a question into candidate
URLs were Exa (unconfigured by the project owner's decision) and GitHub (which
searches code repositories, so it returns nothing for documentation or academic
questions). arXiv abstracts are already a recognised primary source downstream:
``source_quality.classify_source`` gives ``arxiv.org/abs/<id>`` a structural
``primary`` tier, and the existing content floor is calibrated so a real
abstract page survives it. So this module adds a *search* step only; fetching,
ranking, tiering and every cap stay exactly where they were.

Everything crossing the network boundary is treated as hostile: a fixed host,
a bounded read, no DOCTYPE, and host validation on every identifier the feed
claims.
"""

from __future__ import annotations

import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ElementTree
from typing import Any

# Scheme and host are constants, never taken from input or from a redirect.
ARXIV_API_HOST = "export.arxiv.org"
ARXIV_API_URL = f"https://{ARXIV_API_HOST}/api/query"
# Only identifiers served by arXiv itself may become candidates.
ARXIV_CANONICAL_HOSTS = frozenset({"arxiv.org", "www.arxiv.org"})

DEFAULT_TIMEOUT = 30
# A single Atom page of <= max_results entries is a few tens of KB. The cap is
# generous but finite, so an oversized or endless response fails loudly instead
# of being read into memory.
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
USER_AGENT = "quant-agent-brain/0.1 (research harness; contact via repository)"

_ATOM_ENTRY = "{http://www.w3.org/2005/Atom}entry"
_ATOM_ID = "{http://www.w3.org/2005/Atom}id"
_ATOM_TITLE = "{http://www.w3.org/2005/Atom}title"
_ATOM_SUMMARY = "{http://www.w3.org/2005/Atom}summary"

# Strip a trailing version marker so arXiv's own "1909.04327v1" and a bare
# "1909.04327" are one work rather than two. Without this the distinct-source
# minimum could be satisfied by the same paper counted twice.
_VERSION_SUFFIX = re.compile(r"v\d*$")
# ``/pdf/`` and ``/abs/`` are two renderings of one paper, and a PDF link may
# carry a ``.pdf`` extension. Both must reduce to the same identity or a single
# work could satisfy the upstream minimum several times over.
_ABS_PATH = re.compile(r"^/(?:abs|pdf)/(?P<identifier>[A-Za-z0-9.\-/]+?)(?:\.pdf)?$")
_DOCTYPE_OR_ENTITY = re.compile(r"<!(?:DOCTYPE|ENTITY)", re.IGNORECASE)


class ArxivSearchError(RuntimeError):
    """The arXiv lane could not produce a trustworthy answer.

    Raised for a transport failure, an oversized body, a malformed feed or a
    feed carrying a DOCTYPE. Deliberately *not* raised for a well-formed feed
    with no entries: "arXiv has nothing on this" is an answer, and the caller
    must be able to tell it apart from "arXiv did not respond".
    """


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Refuse every redirect instead of following it.

    geturl() reports only the final hop, so a chain that leaves the pinned host
    and comes back would pass an end-of-chain check. Refusing outright keeps the
    host pin meaning "never left the host".
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        del req, fp, msg, headers
        raise ArxivSearchError(f"arXiv request was redirected ({code}) to {newurl!r}; refusing")


_NO_REDIRECT_OPENER = urllib.request.build_opener(_NoRedirect)


# Phrases worth quoting against an academic index, checked in this fixed order.
# This vocabulary is the whole transformation: it is applied identically to
# every question, so no question can be given a hand-tuned query to lift its
# candidate count over a gate threshold.
QUERY_PHRASES: tuple[str, ...] = (
    "mean reversion",
    "transaction costs",
    "holding period",
    "slippage",
    "exit",
    "stop-loss",
    "trading strategy",
    "backtest",
)
# Two phrases, not three. A three-way conjunction returned zero results for all
# three Phase 6 questions; two is the widest conjunction that still constrains
# the topic. Measured, not guessed.
MAX_QUERY_PHRASES = 2
FALLBACK_QUERY = 'all:"trading strategy"'


def build_arxiv_query(question: str, method_family: str | None = None) -> str:
    """Turn a research question into one arXiv search expression.

    One rule for every question. The expression is returned so callers can
    record it verbatim alongside the run, which is what makes a sparse result
    auditable: a reader can see exactly what was asked before concluding the
    literature is thin.
    """
    text = (question or "").lower()
    picked = [phrase for phrase in QUERY_PHRASES if phrase in text]
    if method_family:
        family = method_family.replace("_", " ").strip().lower()
        if family in QUERY_PHRASES and family not in picked:
            picked.insert(0, family)
    if not picked:
        return FALLBACK_QUERY
    return " AND ".join(f'all:"{phrase}"' for phrase in picked[:MAX_QUERY_PHRASES])


def canonical_abs_url(raw: str) -> str | None:
    """Return ``https://arxiv.org/abs/<id>`` for an arXiv id, else ``None``.

    Rejects any host but arXiv's, so a feed that names some other site cannot
    inject a candidate. Forces https and drops the version suffix so one work
    has exactly one identity downstream.
    """
    try:
        parts = urllib.parse.urlsplit((raw or "").strip())
    except ValueError:
        return None
    if (parts.hostname or "").lower() not in ARXIV_CANONICAL_HOSTS:
        return None
    match = _ABS_PATH.match(parts.path)
    if not match:
        return None
    identifier = _VERSION_SUFFIX.sub("", match.group("identifier"))
    if not identifier:
        return None
    return f"https://arxiv.org/abs/{identifier}"


def _read_feed(query: str, *, limit: int, timeout: int, opener: Any | None) -> str:
    params = urllib.parse.urlencode(
        {
            "search_query": query,
            "max_results": max(1, limit),
            "sortBy": "relevance",
        }
    )
    request = urllib.request.Request(
        f"{ARXIV_API_URL}?{params}",
        headers={"User-Agent": USER_AGENT, "Accept": "application/atom+xml"},
    )
    # Redirects are refused outright rather than followed and checked at the
    # end: geturl() reports only the final hop, so a chain that leaves the host
    # and returns would pass a final-hop check. The endpoint is a fixed HTTPS
    # API that has no legitimate reason to bounce us elsewhere.
    open_url = opener or _NO_REDIRECT_OPENER.open
    try:
        with open_url(request, timeout=timeout) as response:
            final_host = (urllib.parse.urlsplit(response.geturl()).hostname or "").lower()
            if final_host != ARXIV_API_HOST:
                raise ArxivSearchError(
                    f"arXiv request redirected off-host to {final_host!r}; refusing the response"
                )
            # Read one byte past the cap: a full buffer means the body was
            # larger than we are willing to trust, not merely exactly at it.
            body = response.read(MAX_RESPONSE_BYTES + 1)
    except ArxivSearchError:
        raise
    except Exception as exc:  # transport, timeout, DNS, HTTP error
        raise ArxivSearchError(f"arXiv request failed: {type(exc).__name__}: {exc}") from exc
    if len(body) > MAX_RESPONSE_BYTES:
        raise ArxivSearchError(
            f"arXiv response exceeded {MAX_RESPONSE_BYTES} bytes; refusing to parse it"
        )
    return body.decode("utf-8", "replace")


def parse_arxiv_feed(xml_text: str) -> list[dict[str, Any]]:
    """Parse an Atom feed into candidate hits.

    A well-formed feed with no entries returns ``[]``. Anything malformed, or
    carrying a document type or entity declaration, raises -- silence and
    corruption must not look alike to the caller.
    """
    if _DOCTYPE_OR_ENTITY.search(xml_text):
        # ElementTree already refuses to expand external entities; rejecting the
        # declaration outright keeps a hostile feed from reaching the parser.
        raise ArxivSearchError("arXiv response contained a DOCTYPE or entity declaration")
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError as exc:
        raise ArxivSearchError(f"arXiv response was not well-formed XML: {exc}") from exc

    hits: list[dict[str, Any]] = []
    for entry in root.iter(_ATOM_ENTRY):
        identifier = entry.findtext(_ATOM_ID, default="")
        url = canonical_abs_url(identifier)
        if not url:
            # An entry we cannot attribute to arXiv is dropped, not guessed at.
            continue
        title = " ".join((entry.findtext(_ATOM_TITLE, default="") or "").split())
        summary = " ".join((entry.findtext(_ATOM_SUMMARY, default="") or "").split())
        hits.append(
            {
                "url": url,
                "title": title or url,
                "snippet": summary[:600],
                "source_type": "paper",
            }
        )
    return hits


def search_arxiv(
    query: str,
    *,
    limit: int,
    timeout: int = DEFAULT_TIMEOUT,
    opener: Any | None = None,
) -> list[dict[str, Any]]:
    """Run one arXiv query and return canonical, deduplicated candidate hits."""
    hits = parse_arxiv_feed(_read_feed(query, limit=limit, timeout=timeout, opener=opener))
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for hit in hits:
        if hit["url"] in seen:
            continue
        seen.add(hit["url"])
        unique.append(hit)
    return unique

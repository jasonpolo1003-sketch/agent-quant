"""Identity of the upstream *work* behind a URL, for counting and dedupe.

One paper routinely has several URLs: a DOI resolver link, the publisher's
landing page, an SSRN abstract page, an arXiv abs page. Counting URLs lets one
work satisfy the Phase 6 minimum more than once, so both the source minimum and
candidate dedupe key on the work instead.

Recognition is an explicit, host-anchored table and nothing else. A generic
"the path ends with a DOI" rule cannot be made safe: DOI suffixes may contain
``/``, so ``/10.1000/abc/figures`` is syntactically indistinguishable from a
DOI. Each publisher row therefore matches the *full* path with a slash-free
suffix, and anything unrecognized keeps its own URL key.

That makes the failure mode under-merging, never over-merging: an alias on a
publisher not listed here still counts separately. Two distinct works must
never share a key, so an unrecognized form is left alone rather than guessed.
Adding a publisher means adding a row and a test. No network resolution.
"""

from __future__ import annotations

import re
from urllib.parse import parse_qs, unquote, urlsplit

from quant_brain.discovery.arxiv_search import canonical_abs_url
from quant_brain.discovery.source_quality import normalize_candidate_url

DOI_RESOLVER_HOSTS = frozenset({"doi.org", "dx.doi.org"})
SSRN_HOSTS = frozenset({"ssrn.com", "papers.ssrn.com"})

# A whole DOI: registrant prefix, then a non-empty suffix. Anchored at both ends
# by every caller, so a DOI can never be read out of the middle of a longer path.
_DOI = r"10\.\d{4,9}/\S+"
_RESOLVER_PATH = re.compile(rf"^/({_DOI})$")
_ARXIV_DOI = re.compile(r"^10\.48550/arxiv\.(?P<identifier>.+)$", re.IGNORECASE)
_SSRN_DOI = re.compile(r"^10\.2139/ssrn\.(?P<number>\d+)$", re.IGNORECASE)
_SSRN_ABSTRACT_PATH = re.compile(r"^/abstract=(?P<number>\d+)/?$")

# (host, full-path pattern whose group 1 is the DOI). Suffixes are slash-free
# on purpose: trailing segments such as ``/figures`` are not recognized.
PUBLISHER_DOI_PATHS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("europeanproceedings.com", re.compile(r"^/article/(10\.15405/[^/\s]+)/?$")),
    (
        "onlinelibrary.wiley.com",
        re.compile(r"^/doi/(?:abs/|full/|pdf/|epdf/)?(10\.1111/[^/\s]+)/?$"),
    ),
)


def _host(parts) -> str:
    host = (parts.hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def _doi_key(doi: str) -> str:
    """Key for a DOI, mapping the arXiv and SSRN registrants onto their works."""
    arxiv = _ARXIV_DOI.match(doi)
    if arxiv:
        canonical = canonical_abs_url(f"https://arxiv.org/abs/{arxiv.group('identifier')}")
        if canonical:
            return canonical
    ssrn = _SSRN_DOI.match(doi)
    if ssrn:
        return f"doi:10.2139/ssrn.{ssrn.group('number')}"
    # DOIs are case-insensitive by specification.
    return f"doi:{doi.lower()}"


def upstream_work_key(url: str) -> str:
    """Return one identity per upstream work, or the normalized URL if unknown."""
    raw = (url or "").strip()
    arxiv = canonical_abs_url(raw)
    if arxiv:
        return arxiv
    try:
        parts = urlsplit(raw)
    except ValueError:
        return normalize_candidate_url(raw)
    host = _host(parts)
    path = unquote(parts.path or "")

    if host in DOI_RESOLVER_HOSTS:
        match = _RESOLVER_PATH.match(path.rstrip("/"))
        if match:
            return _doi_key(match.group(1))

    for publisher, pattern in PUBLISHER_DOI_PATHS:
        if host == publisher:
            match = pattern.match(path)
            if match:
                return _doi_key(match.group(1))

    if host in SSRN_HOSTS:
        numbers = parse_qs(parts.query).get("abstract_id") or []
        if len(numbers) == 1 and numbers[0].isdigit():
            return f"doi:10.2139/ssrn.{numbers[0]}"
        match = _SSRN_ABSTRACT_PATH.match(path)
        if match:
            return f"doi:10.2139/ssrn.{match.group('number')}"

    return normalize_candidate_url(raw)

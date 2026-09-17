"""Executable form of ``brain/_system/research_source_quality_policy.md``.

The policy document defines Tier A/B/C/D in prose. This module makes the same
tiers decidable by a deterministic, offline function so the Scout can tell a
credible source from blogspam *before* it spends a fetch and a model call.

Tier names map onto the schema enum, not onto the letters:

    Tier A -> "primary"        Tier C -> "discovery-only"
    Tier B -> "practitioner"   Tier D -> "reject"

Why the policy lives in code rather than a data file under ``brain/_system/``:
that tree is agent-readable space. A tier list there would let an agent widen
its own promotion criteria, which is the exact direction of authority the
registry forbids (callers narrow, never widen). Frozen constants get reviewed
like any other guarantee.

Three independent signal families decide a tier:

1. Structural -- host/path *shape* (arXiv ``/abs/``, DOI, SSRN, academic
   research paths). Generalizes to hosts nobody enumerated.
2. Allowlist -- named institutions and practitioner blogs, because credibility
   is a fact about the author and cannot be read off a URL shape.
3. Reject -- commercial/promotional intent, which runs **first** so Tier-D
   marketing on an otherwise-credible host is still rejected.

A bare TLD is never a primary signal. ``.edu`` hosts carry student pages,
personal blogs, course assignments and abandoned material alongside real
research; ``.gov`` mixes regulatory material with press releases. Promoting on
TLD alone would recreate the promotion backdoor this module exists to close, so
every structural rule requires a path shape or membership in a recognized-host
set.

Scope: acquisition-time rejection targets commercial intent only. Grounding --
whether a claim is actually supported by its snapshot -- stays in
``quant_brain.llm.validators`` where a snapshot exists to compare against.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

from quant_brain.research.schema import SOURCE_QUALITY_VALUES

# Named institutions whose own site is primary evidence. Credibility here is a
# fact about the publisher, so this is irreducibly a list.
PRIMARY_DOMAINS = frozenset(
    {
        "aqr.com",
        "arxiv.org",
        "blackrock.com",
        "doi.org",
        "janestreet.com",
        "man.com",
        "quantconnect.com",
        "ssrn.com",
        "twosigma.com",
    }
)

# Recognized regulators, exchanges, central banks and statistical agencies.
# Membership here -- not the .gov TLD -- is what confers primary.
INSTITUTIONAL_HOSTS = frozenset(
    {
        "bis.org",
        "cftc.gov",
        "cmegroup.com",
        "ecb.europa.eu",
        "federalreserve.gov",
        "finra.org",
        "imf.org",
        "nber.org",
        "nyse.com",
        "sec.gov",
    }
)

# Named practitioners writing under their own identity with visible method.
PRACTITIONER_DOMAINS = frozenset(
    {
        "alphaarchitect.com",
        "hudsonthames.org",
        "qoppac.blogspot.com",
        "quantstart.com",
        "robotwealth.com",
        "stockcharts.com",
    }
)

# Hosts whose /docs/ really is reference documentation, so that a marketing
# page at /docs/why-choose-us cannot claim the same standing.
DOCS_HOSTS = frozenset(
    {
        "backtesting.py.readthedocs.io",
        "docs.python.org",
        "numpy.org",
        "pandas.pydata.org",
        "ta-lib.org",
        "vectorbt.dev",
    }
)

_STRUCTURAL_PRIMARY: tuple[tuple[str, re.Pattern[str], re.Pattern[str]], ...] = (
    # (signal name, host pattern, path pattern)
    ("arxiv-abs", re.compile(r"^arxiv\.org$"), re.compile(r"^/abs/\d{4}\.\d{4,5}")),
    ("doi", re.compile(r"^(?:dx\.)?doi\.org$"), re.compile(r"^/10\.\d{4,9}/")),
    (
        "ssrn-abstract",
        re.compile(r"^(?:www\.|papers\.)?ssrn\.com$"),
        re.compile(r"/abstract(?:_id)?=|^/sol3/papers\.cfm"),
    ),
)

# Path shapes that make a university page primary. An .edu host matching none of
# these is a discovery lead, not evidence.
ACADEMIC_RESEARCH_PATHS = re.compile(
    r"^/(?:research|publications?|working[-_]papers?|papers?|preprints?|"
    r"handle|bitstream|dspace|repository)(?:/|$)"
    r"|^/(?:dept|department|faculty|econ|finance|business|school)/",
    re.IGNORECASE,
)

# Commercial/promotional intent. Each pattern carries a name so a rejection can
# say which signal fired rather than returning a bare boolean.
REJECT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "guaranteed-returns",
        re.compile(
            r"\bguaranteed (?:returns?|profits?|income)\b|\brisk[- ]free profit\b|"
            r"\b(?:9[0-9]|100)% (?:win|accuracy|success)\b|\bnever lose\b|"
            r"\b\d{2,}% (?:returns?|gains?) (?:guaranteed|every)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "signal-selling",
        re.compile(
            r"\b(?:buy|join|subscribe to) (?:our|my) (?:signals?|alerts?|vip|telegram)\b|"
            r"\bsignal service\b|\bcopy my trades\b",
            re.IGNORECASE,
        ),
    ),
    (
        "course-funnel",
        re.compile(
            r"\benroll now\b|\blimited[- ]time offer\b|\bmasterclass\b|"
            r"\bget instant access\b|\bbonus module\b",
            re.IGNORECASE,
        ),
    ),
    (
        "screenshot-proof",
        re.compile(
            r"\bscreenshot (?:proves|proof)\b|\bproof of (?:profits?|earnings)\b|"
            r"\bmy broker statement\b",
            re.IGNORECASE,
        ),
    ),
)

# Affiliate/redirect shapes live in the URL rather than the prose.
_AFFILIATE_URL_RE = re.compile(
    r"[?&](?:ref|aff|affiliate|utm_campaign=affiliate)=|^/(?:go|out|recommends|refer)/",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class SourceVerdict:
    """One classification decision, with the evidence for it.

    ``tier`` is always a legal ``SOURCE_QUALITY_VALUES`` member, so the
    classifier structurally cannot emit a value the raw-research schema would
    later reject. ``signals`` names every rule that fired, for audit.
    """

    tier: str
    reason: str
    signals: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.tier not in SOURCE_QUALITY_VALUES:
            raise ValueError(
                f"illegal source tier {self.tier!r}; expected one of {SOURCE_QUALITY_VALUES}"
            )

    @property
    def is_promotable(self) -> bool:
        """Whether this tier may reach a durable source note. Mirrors the curator."""
        return self.tier in {"primary", "practitioner"}

    @property
    def is_rejected(self) -> bool:
        return self.tier == "reject"


def normalize_candidate_url(url: str) -> str:
    """Canonicalize a URL for *dedupe identity*.

    Deliberately distinct from ``live_discovery.normalize_snapshot_url``, which
    maps an empty path to ``"/"`` because snapshot filename hashes depend on
    that form. Do not merge the two: changing the snapshot normalizer silently
    changes every snapshot identity on disk. This one strips the trailing slash
    to nothing so ``https://x.com`` and ``https://x.com/`` are one candidate.
    """
    parts = urlsplit(url.strip())
    host = (parts.hostname or "").lower()
    netloc = f"{host}:{parts.port}" if parts.port else host
    path = parts.path.rstrip("/") or ""
    return urlunsplit((parts.scheme.lower() or "https", netloc, path, parts.query, ""))


def _host_of(url: str) -> str:
    host = (urlsplit(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def _host_matches(host: str, domains: frozenset[str]) -> bool:
    """True when ``host`` is one of ``domains`` or a subdomain of one."""
    return any(host == domain or host.endswith(f".{domain}") for domain in domains)


def _reject_signals(url: str, text: str) -> tuple[str, ...]:
    signals = [name for name, pattern in REJECT_PATTERNS if pattern.search(text)]
    if _AFFILIATE_URL_RE.search(urlsplit(url).path + "?" + urlsplit(url).query):
        signals.append("affiliate")
    return tuple(signals)


def classify_source(
    url: str,
    *,
    title: str = "",
    snippet: str = "",
    body: str = "",
) -> SourceVerdict:
    """Assign a source tier from the URL and whatever text is available.

    Precedence is reject -> structural primary -> institutional/allowlist
    primary -> academic research path -> practitioner -> ``discovery-only``.
    Reject runs first on purpose: promotional material on a credible host is
    still promotional.

    ``body`` is optional so the same function serves both pre-fetch (URL,
    title, snippet only) and post-fetch classification. Passing a body can only
    *demote* a source to ``reject``; it can never promote a tier, so a page
    cannot talk its way up by mentioning the right words.
    """
    host = _host_of(url)
    if not host:
        return SourceVerdict("reject", "url has no resolvable host", ("malformed-url",))

    text = " ".join(part for part in (title, snippet, body) if part)
    rejected = _reject_signals(url, text)
    if rejected:
        return SourceVerdict(
            "reject",
            f"promotional or commercial intent detected ({', '.join(rejected)})",
            rejected,
        )

    path = urlsplit(url).path or "/"

    for name, host_re, path_re in _STRUCTURAL_PRIMARY:
        if host_re.search(host) and path_re.search(path):
            return SourceVerdict("primary", f"structural primary signal: {name}", (name,))

    if _host_matches(host, INSTITUTIONAL_HOSTS):
        return SourceVerdict(
            "primary", f"recognized institutional host: {host}", ("institutional-host",)
        )

    if _host_matches(host, PRIMARY_DOMAINS):
        return SourceVerdict("primary", f"allowlisted primary host: {host}", ("primary-allowlist",))

    # A university host is primary only on a research/publication/repository
    # path. A personal or course page on the same host is a discovery lead.
    if host.endswith(".edu") and ACADEMIC_RESEARCH_PATHS.search(path):
        return SourceVerdict(
            "primary", f"academic research path on {host}", ("academic-research-path",)
        )

    if _host_matches(host, DOCS_HOSTS) and re.search(r"^/(?:docs?|api|reference)(?:/|$)", path):
        return SourceVerdict("primary", f"official documentation on {host}", ("official-docs",))

    if _host_matches(host, PRACTITIONER_DOMAINS):
        return SourceVerdict(
            "practitioner",
            f"identifiable practitioner host: {host}",
            ("practitioner-allowlist",),
        )

    if host.endswith(".edu"):
        return SourceVerdict(
            "discovery-only",
            f"{host} is a university host but not a research/publication path",
            ("edu-host-non-research-path",),
        )

    if host.endswith(".gov"):
        return SourceVerdict(
            "discovery-only",
            f"{host} is a government host but not a recognized institutional source",
            ("gov-host-not-recognized",),
        )

    return SourceVerdict(
        "discovery-only", f"no primary or practitioner signal for {host}", ("unrecognized-host",)
    )

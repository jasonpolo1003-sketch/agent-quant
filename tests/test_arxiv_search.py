"""The arXiv lane: parsing, canonical identity, and hostile-input handling.

Hermetic. Every test drives the parser directly or injects an opener; nothing
here reaches the network.
"""

from pathlib import Path

import pytest

from quant_brain.discovery.arxiv_search import (
    MAX_RESPONSE_BYTES,
    ArxivSearchError,
    build_arxiv_query,
    canonical_abs_url,
    parse_arxiv_feed,
    search_arxiv,
)

ATOM = (Path(__file__).parent / "fixtures" / "arxiv_search_atom.xml").read_text(encoding="utf-8")

EMPTY_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>ArXiv Query</title>
  <opensearch:totalResults xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/"
    >0</opensearch:totalResults>
</feed>
"""


class _Response:
    def __init__(self, body: bytes, url: str = "https://export.arxiv.org/api/query") -> None:
        self._body = body
        self._url = url

    def read(self, size: int = -1) -> bytes:
        return self._body if size < 0 else self._body[:size]

    def geturl(self) -> str:
        return self._url

    def __enter__(self):
        return self

    def __exit__(self, *_exc) -> bool:
        return False


def _opener(body: bytes, url: str = "https://export.arxiv.org/api/query"):
    def open_url(_request, timeout=None):
        del timeout
        return _Response(body, url)

    return open_url


def test_recorded_feed_yields_canonical_versionless_abs_urls():
    hits = parse_arxiv_feed(ATOM)

    assert len(hits) == 3
    for hit in hits:
        assert hit["url"].startswith("https://arxiv.org/abs/")
        assert hit["title"]
    # The recorded identifiers carry v3/v4/v1; canonical identity drops them.
    assert not any(hit["url"].rstrip("0123456789").endswith("v") for hit in hits)


def test_a_valid_empty_feed_is_an_answer_not_an_error():
    """ "arXiv has nothing" must be distinguishable from "arXiv did not reply"."""
    assert parse_arxiv_feed(EMPTY_FEED) == []


@pytest.mark.parametrize(
    "payload",
    [
        '<?xml version="1.0"?><!DOCTYPE feed SYSTEM "http://evil/x.dtd"><feed/>',
        '<?xml version="1.0"?><!DOCTYPE r [<!ENTITY x SYSTEM "file:///etc/passwd">]><r>&x;</r>',
    ],
)
def test_doctype_and_entity_declarations_are_refused(payload):
    with pytest.raises(ArxivSearchError, match="DOCTYPE or entity"):
        parse_arxiv_feed(payload)


def test_malformed_xml_fails_explicitly():
    with pytest.raises(ArxivSearchError, match="not well-formed"):
        parse_arxiv_feed("<feed><entry></feed>")


def test_entries_not_served_by_arxiv_are_discarded():
    """A feed cannot inject a candidate on some other host."""
    feed = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry><id>https://evil.example/abs/1234.5678</id><title>Hostile</title></entry>
      <entry><id>http://arxiv.org/abs/1234.5678v1</id><title>Real</title></entry>
    </feed>
    """
    hits = parse_arxiv_feed(feed)

    assert [hit["url"] for hit in hits] == ["https://arxiv.org/abs/1234.5678"]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("http://arxiv.org/abs/1909.04327v1", "https://arxiv.org/abs/1909.04327"),
        ("https://arxiv.org/abs/1909.04327", "https://arxiv.org/abs/1909.04327"),
        ("https://www.arxiv.org/abs/1909.04327v12", "https://arxiv.org/abs/1909.04327"),
        # /pdf/ and /abs/ are two renderings of one paper. Keying them apart
        # would let a single work satisfy the upstream minimum by itself.
        ("https://arxiv.org/pdf/1909.04327", "https://arxiv.org/abs/1909.04327"),
        ("https://arxiv.org/pdf/1909.04327v2.pdf", "https://arxiv.org/abs/1909.04327"),
        ("https://arxiv.org/abs/1909.04327v", "https://arxiv.org/abs/1909.04327"),
        ("https://arxiv.org/abs/math/0309285", "https://arxiv.org/abs/math/0309285"),
        ("https://arxiv.org/abs/hep-th/9901001v2", "https://arxiv.org/abs/hep-th/9901001"),
        ("https://arxiv.org.evil.com/abs/1909.04327", None),
        ("https://arxiv.org/", None),
        ("https://evil.example/abs/1909.04327", None),
        ("not a url", None),
        ("", None),
    ],
)
def test_canonical_abs_url_collapses_one_work_to_one_identity(raw, expected):
    assert canonical_abs_url(raw) == expected


def test_oversized_response_is_refused_rather_than_parsed():
    with pytest.raises(ArxivSearchError, match="exceeded"):
        search_arxiv("q", limit=3, opener=_opener(b"<feed/>" + b"x" * MAX_RESPONSE_BYTES))


def test_a_redirect_off_the_pinned_host_is_refused():
    with pytest.raises(ArxivSearchError, match="redirected off-host"):
        search_arxiv("q", limit=3, opener=_opener(ATOM.encode(), url="https://evil.example/api"))


def test_redirects_are_refused_rather_than_followed():
    """A chain that leaves the host and returns would pass a final-hop check."""
    from quant_brain.discovery.arxiv_search import _NoRedirect

    with pytest.raises(ArxivSearchError, match="redirected"):
        _NoRedirect().redirect_request(
            None, None, 302, "Found", {}, "https://evil.example/api/query"
        )


def test_transport_failure_is_reported_not_swallowed():
    def boom(_request, timeout=None):
        del timeout
        raise TimeoutError("connection timed out")

    with pytest.raises(ArxivSearchError, match="arXiv request failed"):
        search_arxiv("q", limit=3, opener=boom)


def test_search_deduplicates_repeated_identifiers():
    feed = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry><id>http://arxiv.org/abs/1234.5678v1</id><title>One</title></entry>
      <entry><id>https://arxiv.org/abs/1234.5678</id><title>One again</title></entry>
      <entry><id>http://arxiv.org/abs/1234.5678v9</id><title>One more</title></entry>
    </feed>
    """
    hits = search_arxiv("q", limit=5, opener=_opener(feed.encode()))

    assert len(hits) == 1


# --- the one deterministic query transformation -----------------------------
# These pin the exact generated expressions. If a future change makes a
# question's query different, that is a deliberate change to the rule for every
# question -- which is the point: no question gets a hand-tuned query to lift
# its candidate count over a gate threshold.


@pytest.mark.parametrize(
    ("question", "family", "expected"),
    [
        (
            "What source-supported EXIT rules pair with daily ETF RSI oversold entries",
            "mean_reversion",
            'all:"mean reversion" AND all:"exit"',
        ),
        (
            "What source-supported MAXIMUM HOLDING PERIODS are stated for mean reversion",
            "mean_reversion",
            'all:"mean reversion" AND all:"holding period"',
        ),
        (
            "What FIXED transaction costs and slippage assumptions are defensible",
            None,
            'all:"transaction costs" AND all:"slippage"',
        ),
    ],
)
def test_query_transformation_is_one_fixed_rule(question, family, expected):
    assert build_arxiv_query(question, family) == expected


def test_a_question_matching_no_phrase_still_produces_a_valid_query():
    assert build_arxiv_query("Something entirely unrelated", None).startswith("all:")


def test_at_most_two_phrases_are_conjoined():
    """Three-way conjunction returned zero results for every Phase 6 question."""
    query = build_arxiv_query(
        "mean reversion transaction costs holding period slippage exit backtest", None
    )

    assert query.count(" AND ") == 1

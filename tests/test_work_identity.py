"""One upstream work, one identity -- and two works never share one.

Found in the Gate D E1 dossier: ``https://doi.org/10.15405/epms.2022.10.4`` and
its European Proceedings landing page counted as two distinct upstream works, so
one paper could fill two of the three slots the Phase 6 minimum requires.

Recognition is a host-anchored table, not a generic "path ends with a DOI"
rule: DOI suffixes may contain ``/``, so a publisher sub-page is syntactically
indistinguishable from a DOI. The accepted failure mode is under-merging.
"""

import pytest

from quant_brain.discovery.source_quality import normalize_candidate_url
from quant_brain.discovery.work_identity import upstream_work_key
from quant_brain.research.executor import distinct_upstream_keys

# --- aliases of one work collapse ---------------------------------------------


@pytest.mark.parametrize(
    "first, second",
    [
        # The E1 finding itself.
        (
            "https://doi.org/10.15405/epms.2022.10.4",
            "https://www.europeanproceedings.com/article/10.15405/epms.2022.10.4",
        ),
        (
            "https://doi.org/10.15405/epms.2022.10.4",
            "https://www.europeanproceedings.com/article/10.15405/epms.2022.10.4/",
        ),
        # Wiley landing, abstract, full text and PDF views of one article.
        (
            "https://doi.org/10.1111/0022-1082.00163",
            "https://onlinelibrary.wiley.com/doi/10.1111/0022-1082.00163",
        ),
        (
            "https://doi.org/10.1111/0022-1082.00163",
            "https://onlinelibrary.wiley.com/doi/abs/10.1111/0022-1082.00163",
        ),
        (
            "https://doi.org/10.1111/0022-1082.00163",
            "https://onlinelibrary.wiley.com/doi/pdf/10.1111/0022-1082.00163",
        ),
        (
            "https://doi.org/10.1111/0022-1082.00163",
            "https://onlinelibrary.wiley.com/doi/full/10.1111/0022-1082.00163",
        ),
        # Resolver host, scheme, www. and DOI case are all the same work.
        ("http://dx.doi.org/10.1111/JOFI.12345", "https://doi.org/10.1111/jofi.12345"),
        ("https://www.doi.org/10.1111/jofi.12345/", "https://doi.org/10.1111/jofi.12345"),
        ("https://doi.org/10.1111%2Fjofi.12345", "https://doi.org/10.1111/jofi.12345"),
        # SSRN abstract page and its DOI.
        (
            "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4708400",
            "https://doi.org/10.2139/ssrn.4708400",
        ),
        ("https://www.ssrn.com/abstract=4339128", "https://doi.org/10.2139/SSRN.4339128"),
        # arXiv's DataCite DOI and the abs page, any version.
        ("https://doi.org/10.48550/arXiv.1909.04327", "https://arxiv.org/abs/1909.04327v2"),
    ],
)
def test_aliases_of_one_work_share_one_key(first, second):
    assert upstream_work_key(first) == upstream_work_key(second)


def test_the_e1_doi_alias_no_longer_counts_twice():
    sources = [
        {"url_or_citation": "https://doi.org/10.15405/epms.2022.10.4"},
        {"url_or_citation": "https://www.europeanproceedings.com/article/10.15405/epms.2022.10.4"},
    ]

    assert distinct_upstream_keys(sources) == ["doi:10.15405/epms.2022.10.4"]


# --- distinct works stay distinct ---------------------------------------------


@pytest.mark.parametrize(
    "first, second",
    [
        # Exact match, never a prefix.
        ("https://doi.org/10.15405/epms.2022.10.4", "https://doi.org/10.15405/epms.2022.10.40"),
        (
            "https://onlinelibrary.wiley.com/doi/10.1111/jofi.12345",
            "https://onlinelibrary.wiley.com/doi/10.1111/jofi.12346",
        ),
        # A trailing segment might be part of the DOI or a sub-page; unrecognized.
        (
            "https://doi.org/10.15405/epms.2022.10.4",
            "https://www.europeanproceedings.com/article/10.15405/epms.2022.10.4/figures",
        ),
        (
            "https://doi.org/10.1111/jofi.12345",
            "https://onlinelibrary.wiley.com/doi/10.1111/jofi.12345/suppl",
        ),
        # Documented limitation: a DOI-looking path on an unlisted host.
        (
            "https://doi.org/10.1111/jofi.12345",
            "https://publisher.example/article/10.1111/jofi.12345",
        ),
        # abstract_id means SSRN only on SSRN's own hosts.
        (
            "https://doi.org/10.2139/ssrn.4708400",
            "https://example.com/paper?abstract_id=4708400",
        ),
        # A DOI in a query string is not parsed.
        ("https://doi.org/10.1111/jofi.12345", "https://example.com/view?doi=10.1111/jofi.12345"),
        # Two arXiv works.
        ("https://doi.org/10.48550/arXiv.1909.04327", "https://arxiv.org/abs/1909.04328"),
    ],
)
def test_distinct_works_never_share_a_key(first, second):
    assert upstream_work_key(first) != upstream_work_key(second)


@pytest.mark.parametrize(
    "url",
    [
        "https://chartschool.stockcharts.com/table-of-contents/trading-strategies-and-models/trading-strategies/rsi-2",
        "https://www.naaim.org/wp-content/uploads/2014/04/paper.pdf",
        "https://example.com/a/b/?q=1",
        "https://www.sec.gov/comments/sr-nasdaq-2012-043/nasdaq2012043-28.pdf",
    ],
)
def test_urls_without_a_recognized_work_keep_their_existing_key(url):
    assert upstream_work_key(url) == normalize_candidate_url(url)


def test_arxiv_identity_is_unchanged():
    assert upstream_work_key("http://arxiv.org/abs/1909.04327v1") == (
        "https://arxiv.org/abs/1909.04327"
    )

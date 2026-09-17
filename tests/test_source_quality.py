"""Tier classification: the executable form of the source-quality policy.

These tests pin the promotion floor. Loosening any of them widens what can
reach ``brain/01_Sources/``, so a change here is a policy change.
"""

from __future__ import annotations

import pytest

from quant_brain.discovery.live_discovery import normalize_snapshot_url
from quant_brain.discovery.source_quality import (
    SourceVerdict,
    classify_source,
    normalize_candidate_url,
)
from quant_brain.research.schema import SOURCE_QUALITY_VALUES


def test_arxiv_abstract_urls_classify_as_primary_from_structure_not_an_allowlist():
    verdict = classify_source("https://arxiv.org/abs/2301.04567")
    assert verdict.tier == "primary"
    assert "arxiv-abs" in verdict.signals


def test_doi_and_ssrn_abstract_paths_classify_as_primary():
    assert classify_source("https://doi.org/10.1111/jofi.12345").tier == "primary"
    assert classify_source("https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3247865").tier == (
        "primary"
    )


def test_named_practitioner_blogs_classify_as_practitioner():
    verdict = classify_source("https://alphaarchitect.com/2020/05/momentum-investing/")
    assert verdict.tier == "practitioner"
    assert verdict.is_promotable


def test_unknown_hosts_default_to_discovery_only():
    verdict = classify_source("https://some-random-blog.example/rsi-explained")
    assert verdict.tier == "discovery-only"
    assert not verdict.is_promotable


def test_guaranteed_return_pages_classify_as_reject():
    verdict = classify_source(
        "https://tradingsecrets.example/system",
        title="Guaranteed returns with zero risk",
    )
    assert verdict.is_rejected
    assert "guaranteed-returns" in verdict.signals


def test_affiliate_redirect_urls_classify_as_reject():
    verdict = classify_source("https://reviews.example/go/broker?ref=abc123")
    assert verdict.is_rejected
    assert "affiliate" in verdict.signals


def test_reject_signals_win_over_an_allowlisted_primary_host():
    """Promotional material on a credible host is still promotional."""
    verdict = classify_source(
        "https://arxiv.org/abs/2301.04567",
        title="Enroll now for our masterclass",
    )
    assert verdict.is_rejected
    assert "course-funnel" in verdict.signals


def test_classification_signals_are_recorded_for_audit():
    verdict = classify_source("https://sec.gov/rules/final/2024/34-99999.pdf")
    assert verdict.signals
    assert verdict.reason


def test_every_returned_tier_is_a_legal_schema_source_quality():
    urls = [
        "https://arxiv.org/abs/2301.04567",
        "https://alphaarchitect.com/post",
        "https://unknown.example/page",
        "https://scam.example/go/x?ref=1",
        "not-a-url",
    ]
    for url in urls:
        assert classify_source(url).tier in SOURCE_QUALITY_VALUES


def test_an_illegal_tier_cannot_be_constructed():
    with pytest.raises(ValueError, match="illegal source tier"):
        SourceVerdict("tier-a", "nope")


# --- The TLD backdoor: a bare .edu/.gov is never enough --------------------


def test_a_university_research_or_publication_path_classifies_as_primary():
    verdict = classify_source("https://economics.harvard.edu/working-papers/liquidity-2023")
    assert verdict.tier == "primary"
    assert "academic-research-path" in verdict.signals


def test_a_personal_or_course_page_on_an_edu_host_is_only_a_discovery_lead():
    """Same host as a real working paper -- the path is what differs."""
    verdict = classify_source("https://economics.harvard.edu/~jsmith/blog/my-thoughts")
    assert verdict.tier == "discovery-only"
    assert "edu-host-non-research-path" in verdict.signals


def test_a_bare_edu_tld_is_never_sufficient_for_primary():
    for url in (
        "https://cs.example.edu/courses/cs101/hw3.html",
        "https://example.edu/students/clubs/investing",
        "https://example.edu/news/campus-dining-update",
    ):
        assert classify_source(url).tier == "discovery-only", url


def test_recognized_regulator_and_exchange_hosts_classify_as_primary():
    assert classify_source("https://www.sec.gov/investor/alerts/etfs.htm").tier == "primary"
    assert classify_source("https://www.cmegroup.com/education/margins.html").tier == "primary"


def test_an_unrecognized_gov_page_is_only_a_discovery_lead():
    verdict = classify_source("https://parks.somecity.gov/news/trail-reopening")
    assert verdict.tier == "discovery-only"
    assert "gov-host-not-recognized" in verdict.signals


def test_promotional_rejection_still_wins_on_an_academic_research_path():
    verdict = classify_source(
        "https://economics.harvard.edu/working-papers/x",
        body="Join our VIP telegram signal service for guaranteed returns",
    )
    assert verdict.is_rejected


def test_a_body_can_demote_a_source_but_never_promote_one():
    """Body text is downgrade-only: a page cannot talk its way up a tier."""
    promoted = classify_source(
        "https://unknown-blog.example/post",
        body="This peer-reviewed working paper from arxiv.org presents a DOI 10.1111/x",
    )
    assert promoted.tier == "discovery-only"

    demoted = classify_source(
        "https://alphaarchitect.com/post",
        body="Enroll now -- limited-time offer, bonus module included",
    )
    assert demoted.is_rejected


def test_malformed_urls_are_rejected_rather_than_defaulting_to_a_tier():
    verdict = classify_source("not-a-url")
    assert verdict.is_rejected
    assert "malformed-url" in verdict.signals


# --- Normalization ---------------------------------------------------------


def test_trailing_slash_and_case_variants_normalize_to_one_identity():
    variants = [
        "https://www.investopedia.com/terms/r/rsi.asp",
        "https://www.investopedia.com/terms/r/rsi.asp/",
        "HTTPS://WWW.Investopedia.com/terms/r/rsi.asp",
        "https://www.investopedia.com/terms/r/rsi.asp#section",
    ]
    identities = {normalize_candidate_url(url) for url in variants}
    assert len(identities) == 1


def test_candidate_normalizer_does_not_share_empty_path_semantics_with_snapshot_normalizer():
    """Two normalizers exist on purpose; merging them would rewrite snapshot identities."""
    bare = "https://example.com"
    assert normalize_candidate_url(bare) == "https://example.com"
    assert normalize_snapshot_url(bare) == "https://example.com/"


def test_normalization_preserves_the_query_string():
    url = "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3247865"
    assert "abstract_id=3247865" in normalize_candidate_url(url)

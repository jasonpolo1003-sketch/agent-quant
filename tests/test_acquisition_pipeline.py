"""Bounded acquisition: dedupe, ranking, budget, and pre-fetch rejection.

Pure functions only -- no network, no disk, no database.
"""

from __future__ import annotations

import json
from pathlib import Path

from quant_brain.discovery.acquisition import (
    MIN_CONTENT_CHARS,
    Candidate,
    assess_fetched_content,
    dedupe_candidates,
    rank_candidates,
    rejection_ledger_markdown,
    score_candidate,
)
from quant_brain.discovery.source_quality import classify_source

FIXTURES = Path(__file__).parent / "fixtures"
MIXED_HITS = json.loads((FIXTURES / "acquisition_search_mixed.json").read_text(encoding="utf-8"))
FETCH_BODIES = json.loads(
    (FIXTURES / "acquisition_fetch_bodies.json").read_text(encoding="utf-8")
)
QUERY = "source supported exit rules for RSI mean reversion on ETFs"


def _mixed_candidates() -> list[Candidate]:
    return dedupe_candidates(MIXED_HITS["results"])


def test_cross_channel_duplicate_urls_collapse_to_a_single_candidate():
    """The same Investopedia page arrives twice, differing only by trailing slash."""
    urls = [hit["url"] for hit in MIXED_HITS["results"]]
    assert sum("rsi.asp" in url for url in urls) == 2, "fixture must contain the duplicate pair"

    candidates = _mixed_candidates()
    rsi_pages = [c for c in candidates if "rsi.asp" in c.url]
    assert len(rsi_pages) == 1


def test_a_primary_candidate_at_search_rank_six_outranks_blogspam_at_rank_one():
    candidates = _mixed_candidates()
    arxiv = next(c for c in candidates if "arxiv.org" in c.url)
    assert arxiv.rank is not None and arxiv.rank >= 6, "fixture must bury the arXiv hit"

    accepted, _ = rank_candidates(candidates, QUERY, limit=5)
    assert any("arxiv.org" in c.url for c in accepted)
    assert accepted[0].tier in {"primary", "practitioner"}


def test_rejected_candidates_never_enter_the_accepted_budget():
    candidates = _mixed_candidates()
    accepted, rejected = rank_candidates(candidates, QUERY, limit=5)

    assert not any(c.tier == "reject" for c in accepted)
    rejected_urls = {c.url for c in rejected if c.tier == "reject"}
    assert rejected_urls, "fixture must contain promotional material"


def test_a_rejected_candidate_with_high_term_overlap_still_cannot_win_a_slot():
    """A finite penalty would let topical slop out-score a clean lead."""
    slop_url = "https://scam.example/go/x?ref=1"
    slop_title = "RSI mean reversion exit rules for ETFs guaranteed returns"
    slop = Candidate(
        url=slop_url,
        title=slop_title,
        rank=1,
        verdict=classify_source(slop_url, title=slop_title),
    )
    clean = Candidate(
        url="https://unknown.example/notes",
        title="unrelated",
        rank=9,
        verdict=classify_source("https://unknown.example/notes"),
    )
    assert score_candidate(slop, QUERY) < score_candidate(clean, QUERY)


def test_keyword_stuffing_cannot_outrank_credible_sources():
    """Term density is the one signal an SEO page fully controls; tier is not."""
    candidates = _mixed_candidates()
    accepted, _ = rank_candidates(candidates, QUERY, limit=5)

    seo = next(c for c in accepted if "seo-farm" in c.url)
    credible = [c for c in accepted if c.tier in {"primary", "practitioner"}]
    assert len(credible) >= 3
    assert all(c.score > seo.score for c in credible)


def test_accepted_candidates_never_exceed_the_requested_limit():
    candidates = _mixed_candidates()
    for limit in (1, 2, 3, 5):
        accepted, _ = rank_candidates(candidates, QUERY, limit=limit)
        assert len(accepted) <= limit


def test_every_candidate_is_either_accepted_or_recorded_as_rejected():
    candidates = _mixed_candidates()
    accepted, rejected = rank_candidates(candidates, QUERY, limit=5)
    assert len(accepted) + len(rejected) == len(candidates)


def test_a_candidate_that_only_lost_the_budget_is_not_labelled_a_quality_failure():
    candidates = _mixed_candidates()
    _, rejected = rank_candidates(candidates, QUERY, limit=1)
    over_budget = [c for c in rejected if "over-budget" in (c.verdict.signals if c.verdict else ())]
    assert over_budget
    for candidate in over_budget:
        assert "budget" in candidate.verdict.reason
        assert candidate.tier != "reject"


def test_empty_page_content_is_rejected_before_any_snapshot_is_written():
    verdict = assess_fetched_content("https://example.com/x", "")
    assert verdict is not None and verdict.is_rejected
    assert "empty-content" in verdict.signals


def test_cookie_banner_boilerplate_is_rejected_as_thin_content():
    body = FETCH_BODIES["https://seo-farm.example/rsi-guide"]
    verdict = assess_fetched_content("https://seo-farm.example/rsi-guide", body)
    assert verdict is not None and verdict.is_rejected
    assert verdict.signals[0] in {"cookie-banner", "thin-content"}


def test_a_nav_prefix_cannot_hide_a_cookie_banner():
    """Anchored patterns let "Home About Contact" defeat the detector."""
    body = "Home About Contact Privacy " + FETCH_BODIES["https://seo-farm.example/rsi-guide"]
    verdict = assess_fetched_content("https://seo-farm.example/x", body)
    assert verdict is not None and verdict.is_rejected


def test_a_long_article_mentioning_cookies_is_not_treated_as_a_banner():
    """Boilerplate detection applies to short shells, not to real content."""
    article = FETCH_BODIES["https://arxiv.org/abs/2301.04567"]
    body = "We use cookies on this site. " + article * 2
    assert len(" ".join(body.split())) > 2000
    assert assess_fetched_content("https://arxiv.org/abs/2301.04567", body) is None


def test_a_javascript_shell_page_is_rejected():
    body = FETCH_BODIES["https://spa.example/app"]
    verdict = assess_fetched_content("https://spa.example/app", body)
    assert verdict is not None and verdict.is_rejected


def test_promotional_body_text_is_rejected_before_model_extraction():
    url = "https://tradingsecrets.example/system"
    verdict = assess_fetched_content(url, FETCH_BODIES[url])
    assert verdict is not None and verdict.is_rejected


def test_a_substantive_primary_page_passes_the_content_floor():
    url = "https://arxiv.org/abs/2301.04567"
    assert assess_fetched_content(url, FETCH_BODIES[url]) is None


def test_a_substantive_practitioner_page_passes_the_content_floor():
    url = "https://alphaarchitect.com/2020/05/momentum-exit-rules/"
    assert assess_fetched_content(url, FETCH_BODIES[url]) is None


def test_a_page_just_under_the_floor_is_rejected_with_its_measurements():
    verdict = assess_fetched_content("https://x.example/p", "word " * 50)
    assert verdict is not None
    assert str(MIN_CONTENT_CHARS) in verdict.reason
    assert "thin-content" in verdict.signals


def test_search_snippet_without_a_fetchable_body_cannot_become_a_source():
    """A snippet is a lead. Without a body there is nothing to snapshot or quote."""
    snippet_only = MIXED_HITS["results"][-1]
    assert not snippet_only.get("body")
    verdict = assess_fetched_content(snippet_only["url"], "")
    assert verdict is not None and verdict.is_rejected


def test_zero_credible_candidates_yields_an_empty_accept_list_rather_than_filling_it():
    only_slop = [
        Candidate(
            url="https://scam.example/go/a?ref=1",
            verdict=classify_source("https://scam.example/go/a?ref=1"),
        ),
        Candidate(
            url="https://scam.example/go/b?ref=2",
            verdict=classify_source("https://scam.example/go/b?ref=2"),
        ),
    ]
    accepted, rejected = rank_candidates(only_slop, QUERY, limit=5)
    assert accepted == []
    assert len(rejected) == 2


def test_rejection_ledger_names_every_rejected_url_with_its_reason():
    candidates = _mixed_candidates()
    _, rejected = rank_candidates(candidates, QUERY, limit=5)
    ledger = rejection_ledger_markdown(rejected)

    assert "## Rejected Candidates" in ledger
    for candidate in rejected:
        assert candidate.url in ledger
    assert ledger.count("\n|") >= len(rejected)


def test_an_empty_rejection_list_produces_no_ledger_section():
    assert rejection_ledger_markdown([]) == ""


def test_candidate_records_are_json_safe_for_events():
    candidates = _mixed_candidates()
    accepted, rejected = rank_candidates(candidates, QUERY, limit=5)
    payload = {
        "accepted": [c.as_record() for c in accepted],
        "rejected": [c.as_record() for c in rejected],
    }
    round_tripped = json.loads(json.dumps(payload))
    assert round_tripped["accepted"][0]["tier"]
    assert "signals" in round_tripped["rejected"][0]

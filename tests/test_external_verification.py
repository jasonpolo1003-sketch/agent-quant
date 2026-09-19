import pytest
from test_external_intake import native_pdf

from quant_brain.research.external_intake import Intake

QUOTE = "Exit when RSI > 50 or after 10 trading days."
BODY = (
    ("Methodology context with daily bars and unvalidated results. " * 30)
    + "\n"
    + QUOTE
    + "\nExecution occurs at the next open."
)


def setup(tmp_path, claim=QUOTE, quote=QUOTE, url="https://chartschool.stockcharts.com/test"):
    s = Intake(tmp_path / "store")
    r = s.import_report(native_pdf(tmp_path / "a.pdf", claim), provider="test")
    c = s.add_claim(r["id"], url=url, claim=claim, quote=quote, locator="page 1")
    return s, c


def test_fetch_cache_separate_from_per_claim_evaluation(tmp_path):
    s, a = setup(tmp_path)
    b = s.add_claim(
        a["report_id"],
        url="https://chartschool.stockcharts.com/test",
        claim="Exit never.",
        quote="Exit never.",
        locator="page 1 second claim",
    )
    calls = []

    def fetch(url):
        calls.append(url)
        return {"content": BODY}

    first = s.verify(a["id"], allow_network=True, fetch=fetch)
    other = s.verify(b["id"], fetch=fetch)
    assert len(calls) == 1
    assert first["quote_match"] and not other["quote_match"]
    assert first["claim_id"] != other["claim_id"]
    assert first["fetch_id"] == other["fetch_id"]
    assert s.history(b["id"])[-1]["state"] == "unresolved"
    assert s.verify(a["id"], fetch=fetch)["id"] == first["id"]
    assert s.handoff() == []  # quotation is not a scope review


@pytest.mark.parametrize(
    "claim", ["Exit when RSI < 50 or after 10 trading days.", "Exit when RSI > 50."]
)
def test_reversal_or_removed_cap_never_supported(tmp_path, claim):
    s, c = setup(tmp_path, claim=claim)
    v = s.verify(c["id"], allow_network=True, fetch=lambda u: {"content": BODY})
    assert v["quote_match"] and not v["full_rule_match"]
    with pytest.raises(ValueError):
        s.approve_scope(c["id"], reason="Reviewed", reviewer="tester")
    assert not s.handoff()


def test_no_network_without_permission_and_access_wall_retained(tmp_path):
    s, c = setup(tmp_path)

    def forbidden(u):
        pytest.fail("network was not authorized")

    result = s.verify(c["id"], fetch=forbidden)
    assert result["outcome"] == "not_attempted"
    result = s.verify(
        c["id"], allow_network=True, fetch=lambda u: {"content": "CAPTCHA verify you are human"}
    )
    assert result["outcome"] == "access_blocked"
    assert s.history(c["id"])[-1]["state"] == "blocked"
    assert s.verify(c["id"], fetch=forbidden)["id"] == result["id"]


def test_verified_scope_and_tier_remain_independent(tmp_path):
    s, c = setup(tmp_path, url="https://example.org/research")
    s.verify(c["id"], allow_network=True, fetch=lambda u: {"content": BODY})
    s.approve_scope(
        c["id"],
        reason="Full rule including cap checked; not an ETF performance claim.",
        reviewer="tester",
    )
    assert s.history(c["id"])[-1]["state"] == "supported_in_scope"
    assert s.handoff() == []  # discovery-only source stays ineligible


def test_curator_handoff_readonly_and_revalidates_snapshot(tmp_path):
    s, c = setup(tmp_path)
    v = s.verify(c["id"], allow_network=True, fetch=lambda u: {"content": BODY})
    s.approve_scope(c["id"], reason="All conditions retained.", reviewer="tester")
    before = s.db_path.read_bytes()
    handoff = s.handoff()
    assert len(handoff) == 1 and handoff[0]["main_claim"] == QUOTE
    assert s.db_path.read_bytes() == before
    assert not (s.root / "brain" / "01_Sources").exists()
    from pathlib import Path

    Path(v["snapshot_path"]).write_text("tampered", encoding="utf-8")
    with pytest.raises(ValueError, match="integrity"):
        s.handoff()


def test_new_failed_fetch_revokes_old_eligibility(tmp_path):
    s, c = setup(tmp_path)
    s.verify(c["id"], allow_network=True, fetch=lambda u: {"content": BODY})
    s.approve_scope(c["id"], reason="All conditions retained.", reviewer="tester")
    assert s.handoff()
    s.verify(c["id"], allow_network=True, force=True, fetch=lambda u: {"content": "CAPTCHA"})
    assert not s.handoff()


# A severed token is not a quotation. Substring containment accepted a changed
# numeric threshold -- "Exit when RSI > 5" sits inside "Exit when RSI > 50 ..."
# -- which passed the exact-quotation gate while asserting a rule the source
# never states, and carried a fabricated evidence span to the curator handoff.
@pytest.mark.parametrize(
    "quote",
    [
        "Exit when RSI > 5",  # splits the threshold 50
        "Exit when RSI > 50 or after 10 trading day",  # splits the plural days
        "xit when RSI > 5",  # clipped at both ends
    ],
)
def test_truncated_quotation_never_matches_or_reaches_handoff(tmp_path, quote):
    s, c = setup(tmp_path, claim=quote, quote=quote)
    v = s.verify(c["id"], allow_network=True, fetch=lambda u: {"content": BODY})
    assert v["outcome"] == "fetched"
    assert not v["quote_match"] and not v["full_rule_match"]
    with pytest.raises(ValueError, match="exactly match"):
        s.approve_scope(c["id"], reason="Reviewed", reviewer="tester")
    assert s.handoff() == []


# Quoting a complete fragment is honest; only mid-token truncation is refused.
@pytest.mark.parametrize(
    "quote",
    [
        "Exit when RSI > 50",  # clean prefix of the sentence
        "or after 10 trading days",  # interior span
        "Execution occurs at the next open.",  # trailing sentence
        QUOTE,
    ],
)
def test_clean_partial_quotations_still_locate(tmp_path, quote):
    s, c = setup(tmp_path, claim=quote, quote=quote)
    v = s.verify(c["id"], allow_network=True, fetch=lambda u: {"content": BODY})
    assert v["quote_match"]


def test_decimal_truncation_is_not_a_quotation(tmp_path):
    body = ("Methodology context with daily bars and unvalidated results. " * 30) + (
        "\nRSI(2) below 20.0 at the close."
    )
    s, c = setup(tmp_path, claim="RSI(2) below 20.", quote="RSI(2) below 20.")
    v = s.verify(c["id"], allow_network=True, fetch=lambda u: {"content": body})
    assert not v["quote_match"]
    s2, c2 = setup(tmp_path / "whole", claim="RSI(2) below 20.0", quote="RSI(2) below 20.0")
    assert s2.verify(c2["id"], allow_network=True, fetch=lambda u: {"content": body})["quote_match"]


# Built from code points rather than pasted glyphs: these characters are the
# point of the test, and a literal fullwidth 5 is indistinguishable from an
# ASCII 5 when reading the file.
FW_50 = chr(0xFF15) + chr(0xFF10)  # fullwidth "50"
FW_5 = chr(0xFF15)
AI_50 = chr(0x6F5) + chr(0x6F0)  # extended Arabic-Indic "50"
AI_5 = chr(0x6F5)
MIDDLE_DOT = chr(0xB7)  # decimal separator in some typography
MINUS = chr(0x2212)
EN_DASH = chr(0x2013)


# Found in re-review: the first correction guarded only a quote ending in "."
# or "," before a digit, leaving the mirror case open. "Threshold is 1" out of
# "1,250" misstates the value 1250-fold and passed every gate.
@pytest.mark.parametrize(
    ("fragment", "quote"),
    [
        ("Threshold is 1,250 units per signal.", "Threshold is 1"),
        ("Win rate 0.55 overall in sample.", "Win rate 0"),
        ("Stop loss at 2% per trade applies.", "Stop loss at 2"),
        ("Use a 200-day moving average here.", "Use a 200"),
        ("Exit at 12:30 today always.", "Exit at 12"),
        # Non-ASCII digits are digits too; an ASCII-only class let the original
        # defect back in wearing a different script.
        (f"Exit when RSI > {FW_50} or later.", f"Exit when RSI > {FW_5}"),
        (f"RSI > {AI_50} today.", f"RSI > {AI_5}"),
        # Typographic separators join numbers too, so a source that writes its
        # decimal or range that way must not re-open the truncation.
        (f"Win rate 0{MIDDLE_DOT}55 overall.", "Win rate 0"),
        (f"Range is 20{MINUS}30 days.", "Range is 20"),
        (f"Range is 20{EN_DASH}30 days.", "Range is 20"),
    ],
)
def test_number_truncation_at_either_edge_is_refused(tmp_path, fragment, quote):
    body = ("Methodology context with daily bars and unvalidated results. " * 30) + "\n" + fragment
    s, c = setup(tmp_path, claim=quote, quote=quote)
    v = s.verify(c["id"], allow_network=True, fetch=lambda u: {"content": body})
    assert not v["quote_match"] and not v["full_rule_match"]
    with pytest.raises(ValueError, match="exactly match"):
        s.approve_scope(c["id"], reason="Reviewed", reviewer="tester")
    assert s.handoff() == []


# The same values quoted whole stay legitimate: a separator only joins a number
# when digits sit on both sides, so a trailing comma or period is a clean edge.
@pytest.mark.parametrize(
    ("fragment", "quote"),
    [
        ("Threshold is 1,250 units per signal.", "Threshold is 1,250"),
        ("Win rate 0.55 overall in sample.", "Win rate 0.55"),
        ("Stop loss at 2% per trade applies.", "Stop loss at 2%"),
        ("Use a 200-day moving average here.", "Use a 200-day moving average"),
        ("Exit at 12:30 today always.", "Exit at 12:30"),
        ("Hold for 10 days, then exit the position.", "Hold for 10 days"),
        (f"Exit when RSI > {FW_50} or later.", f"Exit when RSI > {FW_50}"),
        (f"Win rate 0{MIDDLE_DOT}55 overall.", f"Win rate 0{MIDDLE_DOT}55"),
        (f"Range is 20{EN_DASH}30 days.", f"Range is 20{EN_DASH}30"),
        # An em dash is sentence punctuation, not a range: quoting up to it is
        # a clean edge and must not be refused.
        (f"It rose 20{chr(0x2014)} then fell.", "It rose 20"),
    ],
)
def test_whole_numbers_and_clean_edges_still_locate(tmp_path, fragment, quote):
    body = ("Methodology context with daily bars and unvalidated results. " * 30) + "\n" + fragment
    s, c = setup(tmp_path, claim=quote, quote=quote)
    assert s.verify(c["id"], allow_network=True, fetch=lambda u: {"content": body})["quote_match"]


def test_stale_cached_match_cannot_approve_or_hand_off(tmp_path):
    """A catalog verified under the old substring rule must not stay promotable.

    `verify_claim` returns a cached evaluation before matching runs, and
    UNIQUE(claim_id,fetch_id) prevents writing a corrected row for the same
    fetch, so the stale flag survives re-verification. Approval and handoff
    therefore re-derive the check from the snapshot instead of trusting it.
    """
    import json

    quote = "Exit when RSI > 5"
    s, c = setup(tmp_path, claim=quote, quote=quote)
    s.verify(c["id"], allow_network=True, fetch=lambda u: {"content": BODY})
    with s.connection() as conn:
        row = conn.execute(
            "SELECT id,data FROM evaluations WHERE claim_id=?", (c["id"],)
        ).fetchone()
        stale = dict(json.loads(row[1]), quote_match=True, full_rule_match=True)
        conn.execute("UPDATE evaluations SET data=? WHERE id=?", (json.dumps(stale), row[0]))

    # Re-verification returns the poisoned cached row, exactly as it would on a
    # catalog built before the fix.
    assert s.verify(c["id"], fetch=lambda u: {"content": BODY})["full_rule_match"]
    with pytest.raises(ValueError, match="exactly match"):
        s.approve_scope(c["id"], reason="Reviewed", reviewer="tester")
    s.record_review(c["id"], state="partially_supported", reason="forced", reviewer="tester")
    assert s.handoff() == []

import pytest
from test_external_intake import native_pdf

from quant_brain.research.external_intake import Intake


def report(store, tmp_path, text="Exit when RSI > 50 or after 10 trading days."):
    return store.import_report(native_pdf(tmp_path / "a.pdf", text), provider="test")


def test_claims_dedupe_sources_not_report_provenance(tmp_path):
    s = Intake(tmp_path / "store")
    a = report(s, tmp_path)
    b = s.import_report(native_pdf(tmp_path / "b.pdf", "Another report."), provider="other")
    x = s.add_claim(
        a["id"],
        url="https://example.org/rule/",
        claim="Exit when RSI > 50.",
        quote="",
        locator="page 1",
    )
    y = s.add_claim(
        b["id"],
        url="https://example.org/rule",
        claim="Different interpretation.",
        quote="",
        locator="page 1",
    )
    assert x["target_id"] == y["target_id"] and x["id"] != y["id"]
    assert (
        s.add_claim(
            a["id"],
            url="https://example.org/rule/",
            claim="Exit when RSI > 50.",
            quote="",
            locator="page 1",
        )["id"]
        == x["id"]
    )
    data = s.summary()
    assert data["distinct_source_targets"] == 1 and data["claim_count"] == 2
    assert data["independent_corroboration"] == "not_assessed"


def test_state_history_keeps_a_b_a_and_noop_is_idempotent(tmp_path):
    s = Intake(tmp_path / "store")
    r = report(s, tmp_path)
    c = s.add_claim(r["id"], url="", claim="Book lead", quote="", locator="page 1")
    s.record_review(c["id"], state="unresolved", reason="check", reviewer="tester")
    s.record_review(c["id"], state="contradicted", reason="opposing passage", reviewer="tester")
    s.record_review(c["id"], state="unresolved", reason="check", reviewer="tester")
    s.record_review(c["id"], state="unresolved", reason="check", reviewer="tester")
    assert [x["state"] for x in s.history(c["id"])] == [
        "unreviewed_lead",
        "unresolved",
        "contradicted",
        "unresolved",
    ]
    assert all(x["reviewer"] for x in s.history(c["id"]))


def test_invalid_claim_cannot_orphan_history(tmp_path):
    s = Intake(tmp_path / "store")
    with pytest.raises(ValueError):
        s.record_review("absent", state="unresolved", reason="why", reviewer="tester")

import pytest
from test_external_intake import native_pdf

from quant_brain.research.external_intake import Intake
from quant_brain.research.external_reports import import_candidates
from quant_brain.research.external_verification import public_url


def test_connection_context_closes_database(tmp_path):
    import sqlite3

    s = Intake(tmp_path / "store")
    with s.connection() as conn:
        conn.execute("SELECT 1")
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        conn.execute("SELECT 1")


def test_same_claim_can_be_tracked_for_two_research_questions(tmp_path):
    s = Intake(tmp_path / "store")
    r = s.import_report(native_pdf(tmp_path / "a.pdf"), provider="test")
    fields = dict(url="https://example.org", claim="A claim", quote="", locator="page 1")
    a = s.add_claim(r["id"], research_id="RQ-A", **fields)
    b = s.add_claim(r["id"], research_id="RQ-B", **fields)
    assert a["id"] != b["id"] and b["research_id"] == "RQ-B"


def test_oversized_pdf_refused_before_reading(tmp_path, monkeypatch):
    import quant_brain.research.external_intake as module

    pdf = native_pdf(tmp_path / "a.pdf")
    monkeypatch.setattr(module, "MAX_REPORT_BYTES", 1, raising=False)
    s = Intake(tmp_path / "store")
    with pytest.raises(ValueError, match="size"):
        s.import_report(pdf, provider="test")


def test_blank_pdf_contributes_no_claims_and_has_followup(tmp_path):
    from pypdf import PdfWriter

    w = PdfWriter()
    w.add_blank_page(width=612, height=792)
    w.write(tmp_path / "blank.pdf")
    s = Intake(tmp_path / "store")
    result = import_candidates(s, tmp_path / "blank.pdf", provider="test")
    assert result["claims"] == [] and result["report"]["followup_action"]


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "https://127.0.0.1",
        "https://localhost",
        "https://10.0.0.1/x",
        "https://user:secret@example.org",
        "https://example.org:9090",
    ],
)
def test_nonpublic_or_credential_urls_never_fetched(url):
    assert not public_url(url)

"""Offline vertical slices for the external retention catalog."""

import hashlib
import sqlite3
from pathlib import Path

import pytest

from quant_brain.config import PROJECT_ROOT
from quant_brain.research import external_intake as intake


@pytest.mark.parametrize(
    "root",
    [
        PROJECT_ROOT,
        PROJECT_ROOT.parent,
        PROJECT_ROOT / "scratch",
        PROJECT_ROOT.parent / "memory_vault",
    ],
)
def test_production_related_workspaces_rejected_before_writes(root, monkeypatch):
    def forbidden_write(*args, **kwargs):
        pytest.fail("production validation must run before filesystem mutation")

    monkeypatch.setattr(Path, "mkdir", forbidden_write)
    with pytest.raises(ValueError, match="isolated"):
        intake.Intake(root)


def test_workspace_symlink_escape_rejected_before_database_creation(tmp_path):
    root = tmp_path / "sandbox"
    root.mkdir()
    # An alias out of the artifact root is unsafe even if not production.
    outside = tmp_path / "outside.sqlite"
    outside.write_bytes(b"untouched")
    (root / "external.sqlite").hardlink_to(outside)
    with pytest.raises(ValueError, match="alias"):
        intake.Intake(root)
    assert outside.read_bytes() == b"untouched"


def test_copied_production_database_is_not_an_intake_workspace(tmp_path):
    with sqlite3.connect(tmp_path / "external.sqlite") as conn:
        conn.execute("CREATE TABLE research_questions (id TEXT)")
    with pytest.raises(ValueError, match="catalog"):
        intake.Intake(tmp_path)


def native_pdf(path, text="A report with a bibliographic lead: Author, Book (1999)."):
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
    )
    stream = DecodedStreamObject()
    escaped = text.replace("(", r"\(").replace(")", r"\)")
    stream.set_data(f"BT /F1 12 Tf 30 700 Td ({escaped}) Tj ET".encode())
    page[NameObject("/Contents")] = writer._add_object(stream)
    writer.write(path)
    return path


def test_native_text_preserves_bibliographic_leads_and_extraction_provenance(tmp_path):
    import json

    text = "A report with a bibliographic lead: Author, Book (1999)."
    pdf = native_pdf(tmp_path / "native.pdf", text)
    store = intake.Intake(tmp_path / "sandbox")
    report = store.import_report(pdf, provider="Claude")
    assert report["extraction_status"] == "extracted"
    assert text in json.loads(Path(report["text_path"]).read_text())[0]
    assert report["extractor_version"]
    assert report["extraction_mode"] == "layout"
    assert (
        report["text_sha256"] == hashlib.sha256(Path(report["text_path"]).read_bytes()).hexdigest()
    )


def test_artifact_alias_rejected_even_with_isolated_database(tmp_path):
    pdf = native_pdf(tmp_path / "native.pdf")
    store = intake.Intake(tmp_path / "sandbox")
    sha = hashlib.sha256(pdf.read_bytes()).hexdigest()
    outside = tmp_path / "untouched.pdf"
    outside.write_bytes(b"untouched")
    (store.root / f"{sha}.pdf").hardlink_to(outside)
    with pytest.raises(ValueError, match="alias"):
        store.import_report(pdf, provider="Claude")
    assert outside.read_bytes() == b"untouched"


def test_import_preserves_original_and_is_idempotent(tmp_path):
    pdf = tmp_path / "report.pdf"
    pdf.write_bytes(b"not a valid PDF; retained even when extraction fails")
    store = intake.Intake(tmp_path / "isolated")
    first = store.import_report(pdf, provider="ChatGPT")
    again = store.import_report(pdf, provider="ChatGPT")
    assert first == again
    assert first["sha256"] == hashlib.sha256(pdf.read_bytes()).hexdigest()
    assert Path(first["original_path"]).read_bytes() == pdf.read_bytes()
    assert first["provider"] == "ChatGPT"
    assert first["origin"] == str(pdf.resolve())
    assert first["extraction_status"] == "extraction_blocked"
    assert first["extraction_reason"]


def test_same_bytes_at_different_path_share_report_keep_observations(tmp_path):
    pdf = native_pdf(tmp_path / "a.pdf")
    copy = tmp_path / "b.pdf"
    copy.write_bytes(pdf.read_bytes())
    store = intake.Intake(tmp_path / "store")
    one = store.import_report(pdf, provider="ChatGPT")
    two = store.import_report(copy, provider="Other")
    assert one["id"] == two["id"]
    with store.connection() as c:
        assert c.execute("select count(*) from observations").fetchone()[0] == 2


def test_tampered_retained_pdf_detected_on_reimport(tmp_path):
    pdf = native_pdf(tmp_path / "a.pdf")
    store = intake.Intake(tmp_path / "store")
    report = store.import_report(pdf, provider="test")
    Path(report["original_path"]).write_bytes(b"tampered")
    with pytest.raises(ValueError, match="integrity"):
        store.import_report(pdf, provider="test")

    with sqlite3.connect(store.db_path) as conn:
        assert conn.execute("select count(*) from reports").fetchone()[0] == 1

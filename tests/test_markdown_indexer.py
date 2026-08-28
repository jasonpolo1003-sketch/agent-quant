from pathlib import Path

from quant_brain.db.init_db import connect, init_database
from quant_brain.indexing.markdown_indexer import (
    index_markdown_file,
    index_markdown_tree,
    parse_frontmatter,
    split_markdown_sections,
)


def sample_note():
    return """---
id: SRC-test123
type: source_note
status: curated
title: Test Source
source_kind: docs
---

# Source — Test Source

## Summary

This is a short summary.

## Useful Claims

- Claim one.
- Claim two.

## Evidence

- Evidence one.
"""


def test_parse_frontmatter_extracts_metadata_and_body():
    meta, body = parse_frontmatter(sample_note())

    assert meta["id"] == "SRC-test123"
    assert meta["type"] == "source_note"
    assert meta["title"] == "Test Source"
    assert body.startswith("# Source")


def test_split_markdown_sections_uses_headings_with_line_numbers():
    sections = split_markdown_sections(sample_note())

    heading_paths = [section["heading_path"] for section in sections]
    assert "Source — Test Source > Summary" in heading_paths
    assert "Source — Test Source > Useful Claims" in heading_paths
    summary = next(s for s in sections if s["heading_path"].endswith("Summary"))
    assert "short summary" in summary["text"]
    assert summary["start_line"] < summary["end_line"]


def test_index_markdown_file_upserts_note_and_chunks(tmp_path):
    db_path = tmp_path / "brain.sqlite"
    init_database(db_path)
    note_path = tmp_path / "brain" / "01_Sources" / "docs" / "SRC-test123.md"
    note_path.parent.mkdir(parents=True)
    note_path.write_text(sample_note(), encoding="utf-8")

    result = index_markdown_file(tmp_path, db_path, note_path)

    assert result["note_id"] == "SRC-test123"
    assert result["chunks_indexed"] >= 3

    with connect(db_path) as conn:
        note = conn.execute("select note_id, path, title, type from notes").fetchone()
        chunks = conn.execute(
            "select note_id, heading_path, text, embedding_status from chunks order by start_line"
        ).fetchall()

    assert dict(note) == {
        "note_id": "SRC-test123",
        "path": "brain/01_Sources/docs/SRC-test123.md",
        "title": "Test Source",
        "type": "source_note",
    }
    assert len(chunks) == result["chunks_indexed"]
    assert all(row["embedding_status"] == "pending" for row in chunks)
    assert any("Useful Claims" in row["heading_path"] for row in chunks)


def test_index_markdown_file_removes_stale_chunks_on_reindex(tmp_path):
    db_path = tmp_path / "brain.sqlite"
    init_database(db_path)
    note_path = tmp_path / "note.md"
    note_path.write_text("---\nid: NOTE-1\ntitle: One\ntype: test\n---\n\n# One\n\n## A\n\nfirst\n\n## B\n\nsecond\n", encoding="utf-8")
    index_markdown_file(tmp_path, db_path, note_path)

    note_path.write_text("---\nid: NOTE-1\ntitle: One\ntype: test\n---\n\n# One\n\n## A\n\nchanged\n", encoding="utf-8")
    index_markdown_file(tmp_path, db_path, note_path)

    with connect(db_path) as conn:
        headings = [r[0] for r in conn.execute("select heading_path from chunks").fetchall()]

    assert headings == ["One", "One > A"]


def test_index_markdown_tree_indexes_multiple_notes(tmp_path):
    db_path = tmp_path / "brain.sqlite"
    init_database(db_path)
    brain = tmp_path / "brain"
    (brain / "01_Sources" / "docs").mkdir(parents=True)
    (brain / "01_Sources" / "docs" / "a.md").write_text("---\nid: A\ntitle: A\ntype: source_note\n---\n\n# A\n\nAlpha", encoding="utf-8")
    (brain / "_system").mkdir()
    (brain / "_system" / "ignore.md").write_text("# system", encoding="utf-8")

    result = index_markdown_tree(tmp_path, db_path, brain, exclude_dirs={"_system"})

    assert result["files_indexed"] == 1
    with connect(db_path) as conn:
        assert conn.execute("select count(*) from notes").fetchone()[0] == 1
        assert conn.execute("select count(*) from chunks").fetchone()[0] == 1


def test_index_markdown_file_keeps_repeated_identical_sections_addressable(tmp_path):
    db_path = tmp_path / "brain.sqlite"
    init_database(db_path)
    note_path = tmp_path / "brain" / "00_Inbox" / "packet.md"
    note_path.parent.mkdir(parents=True)
    note_path.write_text(
        "---\nid: WP-repeat\ntype: agent_work_packet\n---\n\n"
        "# Packet\n\n## Retrieved Context\n\n"
        "### Research Question\n\nSame text\n\n"
        "### Research Question\n\nSame text\n",
        encoding="utf-8",
    )

    result = index_markdown_file(tmp_path, db_path, note_path)

    with connect(db_path) as conn:
        rows = conn.execute(
            "SELECT chunk_id, heading_path FROM chunks "
            "WHERE heading_path = 'Packet > Retrieved Context > Research Question'"
        ).fetchall()
    assert result["chunks_indexed"] == 4
    assert len(rows) == 2
    assert len({row["chunk_id"] for row in rows}) == 2

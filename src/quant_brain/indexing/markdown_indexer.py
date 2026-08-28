from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any
from uuid import uuid5, NAMESPACE_URL

from quant_brain.config import BRAIN_DIR, PROJECT_ROOT
from quant_brain.db.init_db import DEFAULT_DB_PATH, connect, init_database

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_frontmatter(markdown: str) -> tuple[dict[str, str], str]:
    """Parse simple YAML frontmatter without adding a YAML dependency."""
    match = FRONTMATTER_RE.match(markdown)
    if not match:
        return {}, markdown
    meta: dict[str, str] = {}
    for raw_line in match.group(1).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip().strip('"').strip("'")
    return meta, markdown[match.end() :]


def _line_number_at(char_offset: int, line_starts: list[int]) -> int:
    line_no = 1
    for idx, start in enumerate(line_starts, start=1):
        if start > char_offset:
            break
        line_no = idx
    return line_no


def split_markdown_sections(markdown: str) -> list[dict[str, Any]]:
    """Split a markdown file into heading-based sections for retrieval."""
    _meta, body = parse_frontmatter(markdown)
    lines = body.splitlines()
    sections: list[dict[str, Any]] = []
    stack: list[tuple[int, str]] = []
    current_heading: str | None = None
    current_start_line = 1
    current_lines: list[str] = []

    def flush(end_line: int) -> None:
        nonlocal current_lines, current_heading, current_start_line
        text = "\n".join(current_lines).strip()
        if current_heading and text:
            sections.append(
                {
                    "heading_path": current_heading,
                    "text": text,
                    "start_line": current_start_line,
                    "end_line": end_line,
                }
            )
        current_lines = []

    for line_no, line in enumerate(lines, start=1):
        match = HEADING_RE.match(line)
        if match:
            flush(line_no - 1)
            level = len(match.group(1))
            title = match.group(2).strip()
            stack = [(lvl, name) for lvl, name in stack if lvl < level]
            stack.append((level, title))
            current_heading = " > ".join(name for _lvl, name in stack)
            current_start_line = line_no
            current_lines = [line]
        else:
            current_lines.append(line)
    flush(len(lines))

    if not sections:
        text = body.strip()
        if text:
            sections.append(
                {
                    "heading_path": "Document",
                    "text": text,
                    "start_line": 1,
                    "end_line": len(lines),
                }
            )
    return sections


def _note_id_for(path: Path, meta: dict[str, str], project_root: Path) -> str:
    meta_id = meta.get("id")
    note_type = meta.get("type")
    if meta_id:
        # Research briefs and raw research can share the same research_id, so
        # include type to keep each physical Markdown file addressable.
        if meta_id.startswith("RQ-") and note_type:
            return f"{meta_id}-{note_type}"
        return meta_id
    rel = path.relative_to(project_root).as_posix() if path.is_relative_to(project_root) else path.as_posix()
    return "NOTE-" + uuid5(NAMESPACE_URL, rel).hex[:12]


def _chunk_id(note_id: str, heading_path: str, text_hash: str) -> str:
    return "CHUNK-" + uuid5(NAMESPACE_URL, f"{note_id}|{heading_path}|{text_hash}").hex[:16]


def _token_estimate(text: str) -> int:
    return max(1, len(text.split()))


def _source_id_for_note(note_id: str, meta: dict[str, str]) -> str | None:
    note_type = meta.get("type")
    if note_type == "source_note" or note_id.startswith("SRC-"):
        return note_id
    return None


def index_markdown_file(
    project_root: str | Path,
    db_path: str | Path,
    markdown_path: str | Path,
) -> dict[str, Any]:
    """Index one markdown file into notes/chunks tables."""
    root = Path(project_root).resolve()
    path = Path(markdown_path).resolve()
    text = path.read_text(encoding="utf-8")
    meta, _body = parse_frontmatter(text)
    note_id = _note_id_for(path, meta, root)
    rel_path = path.relative_to(root).as_posix() if path.is_relative_to(root) else path.as_posix()
    title = meta.get("title") or path.stem
    note_type = meta.get("type") or "markdown"
    content_hash = sha256_text(text)
    sections = split_markdown_sections(text)
    candidate_source_id = _source_id_for_note(note_id, meta)

    init_database(db_path)
    with connect(db_path) as conn:
        source_id = None
        if candidate_source_id:
            existing_source = conn.execute(
                "SELECT source_id FROM sources WHERE source_id = ?", (candidate_source_id,)
            ).fetchone()
            source_id = candidate_source_id if existing_source else None
        conn.execute(
            """
            INSERT INTO notes (note_id, path, title, type, status, content_hash, indexed_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(note_id) DO UPDATE SET
                path = excluded.path,
                title = excluded.title,
                type = excluded.type,
                status = excluded.status,
                content_hash = excluded.content_hash,
                indexed_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            """,
            (note_id, rel_path, title, note_type, meta.get("status", "active"), content_hash),
        )
        conn.execute("DELETE FROM chunks WHERE note_id = ?", (note_id,))
        used_chunk_ids: set[str] = set()
        for section in sections:
            section_hash = sha256_text(section["text"])
            chunk_id = _chunk_id(note_id, section["heading_path"], section_hash)
            if chunk_id in used_chunk_ids:
                chunk_id = _chunk_id(
                    note_id,
                    f"{section['heading_path']}|line:{section['start_line']}",
                    section_hash,
                )
            used_chunk_ids.add(chunk_id)
            conn.execute(
                """
                INSERT INTO chunks (
                    chunk_id, note_id, source_id, heading_path, text_hash, text,
                    token_count, start_line, end_line, embedding_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
                """,
                (
                    chunk_id,
                    note_id,
                    source_id,
                    section["heading_path"],
                    section_hash,
                    section["text"],
                    _token_estimate(section["text"]),
                    section["start_line"],
                    section["end_line"],
                ),
            )
        conn.commit()
    return {"note_id": note_id, "path": rel_path, "chunks_indexed": len(sections)}


def index_markdown_tree(
    project_root: str | Path = PROJECT_ROOT,
    db_path: str | Path = DEFAULT_DB_PATH,
    brain_dir: str | Path = BRAIN_DIR,
    exclude_dirs: set[str] | None = None,
) -> dict[str, Any]:
    """Index markdown files under the brain folder."""
    root = Path(project_root)
    base = Path(brain_dir)
    exclude_dirs = exclude_dirs or {"_system"}
    results = []
    for path in sorted(base.rglob("*.md")):
        if any(part in exclude_dirs for part in path.parts):
            continue
        results.append(index_markdown_file(root, db_path, path))
    return {
        "files_indexed": len(results),
        "chunks_indexed": sum(r["chunks_indexed"] for r in results),
        "notes": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Index Markdown brain notes into SQLite chunks.")
    parser.add_argument("index", nargs="?", default="index")
    parser.add_argument("--project-root", default=str(PROJECT_ROOT))
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--brain-dir", default=str(BRAIN_DIR))
    parser.add_argument("--include-system", action="store_true")
    args = parser.parse_args()
    if args.index != "index":
        raise SystemExit("Only supported command is: index")
    excludes = set() if args.include_system else {"_system"}
    result = index_markdown_tree(args.project_root, args.db, args.brain_dir, excludes)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

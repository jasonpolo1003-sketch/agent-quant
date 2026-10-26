"""The LEARN tutor: a NotebookLM-style teacher over sources Jason picks.

The tutor only sees the text of the selected files, numbered by line so it can
cite ``[path:line]``. It has no tools. Saved answers are study notes under
``terminal/learning/``, outside ``brain/``, so the indexer never treats them as
evidence.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import frontmatter

SOURCE_GROUPS: dict[str, list[str]] = {
    "Plan & rules": ["PLAN.md", "AGENTS.md", "README.md", "SESSION_HANDOFF.md",
                     "brain/_system/plan/*.md", "brain/_system/*.md", "brain/80_Summaries/*.md"],
    "Decisions": ["brain/07_Decision_Log/*.md"],
    "Sources": ["brain/01_Sources/*.md", "brain/01_Sources/**/*.md",
                "brain/02_Strategy_Doors/*.md"],
    "Strategy & results": ["brain/03_Strategy_Cards/*.md", "brain/04_Backtest_Reports/**/*.md",
                           "brain/05_Reviews/*.md"],
    "Run receipts": ["brain/00_Inbox/Failed_Runs/*.md", "brain/00_Inbox/Curator_Reviews/*.md"],
    "Raw research & snapshots": ["brain/00_Inbox/Research_Briefs/*.md",
                                 "brain/00_Inbox/Raw_Research/*.md",
                                 "brain/00_Inbox/Source_Snapshots/**/*.md"],
    "Agents": ["agents/*.md"],
    "Code": ["src/quant_brain/**/*.py", "scripts/*.py"],
    "Data manifests": ["data/manifests/*.json"],
    "Study notes": ["terminal/learning/*.md"],
}
SOURCE_SUFFIXES = {".md", ".py", ".json", ".txt"}
MAX_CONTEXT_CHARS = 350_000  # comfortably inside a 200k-token window, with room to answer
LEARNING_DIR = "terminal/learning"

TEACHER_SYSTEM = """You are a patient teacher inside Jason's Quant Agent Brain terminal.
Jason is learning quantitative research and wants to understand this project well enough
to rebuild it himself.

Rules:
- Facts about THIS project (its rules, code, data, runs, results, decisions) come ONLY from
  the <sources> block. Each source line is prefixed with its line number.
- Cite every project fact as [path:line] or [path:start-end], using the exact paths given.
- You may explain general concepts (e.g. look-ahead bias, Sharpe ratio) from your own
  knowledge, but mark them as *General background* so Jason can tell them apart from
  what the sources say.
- If the sources do not answer a question about the project, say "The selected sources
  don't cover that", and suggest which kind of file would. Never invent numbers, results
  or rules.
- Teach: define jargon the first time it appears, use a small concrete example when it
  helps, and end longer answers with a one-line "Key idea:" summary.
- When asked how something works in code, walk through it in order and name the files and
  functions involved, so Jason could rebuild it.
- A backtest never proves future profit. Say so if a question assumes it does.
- Be concise. Use short paragraphs and simple Markdown (lists, `code`, **bold**).
- Write plainly. Do not use em-dashes; use a period, comma or colon instead."""


class SourceError(ValueError):
    pass


def list_sources(project_root: Path) -> list[dict[str, Any]]:
    seen: set[str] = set()
    groups = []
    for group, patterns in SOURCE_GROUPS.items():
        items = []
        for pattern in patterns:
            for path in sorted(project_root.glob(pattern)):
                rel = path.relative_to(project_root).as_posix()
                if path.is_file() and path.suffix in SOURCE_SUFFIXES and rel not in seen:
                    seen.add(rel)
                    items.append({"path": rel, "size": path.stat().st_size})
        if items:
            groups.append({"group": group, "items": items})
    return groups


def allowed_source(project_root: Path, rel: str) -> Path:
    """Resolve a requested source, refusing anything outside the allowlisted groups."""
    root = project_root.resolve()
    candidate = (root / rel).resolve()
    if not candidate.is_relative_to(root) or not candidate.is_file():
        raise SourceError(f"not a readable source: {rel}")
    rel_posix = candidate.relative_to(root).as_posix()
    allowed = {i["path"] for g in list_sources(root) for i in g["items"]}
    if rel_posix not in allowed:
        raise SourceError(f"not an allowed source: {rel}")
    return candidate


def read_source(project_root: Path, rel: str) -> str:
    return allowed_source(project_root, rel).read_text(encoding="utf-8", errors="replace")


def build_context(project_root: Path, paths: list[str], max_chars: int = MAX_CONTEXT_CHARS,
                  virtual: dict[str, str] | None = None) -> tuple[str, list[dict[str, Any]]]:
    """Line-numbered source text plus a report of what was included or cut.

    ``virtual`` supplies text for names that are not files, such as ``run:<id>``
    event logs rendered by the caller.
    """
    if not paths:
        raise SourceError("pick at least one source")
    virtual = virtual or {}
    texts = [(p, virtual[p] if p in virtual else read_source(project_root, p))
             for p in dict.fromkeys(paths)]
    total = sum(len(t) for _, t in texts)
    share = max_chars / total if total > max_chars else 1.0
    blocks, report = [], []
    for rel, text in texts:
        lines = text.splitlines()
        keep = len(lines)
        if share < 1.0:  # cut every source proportionally, and say so
            budget, used, keep = int(len(text) * share), 0, 0
            for line in lines:
                used += len(line) + 1
                if used > budget:
                    break
                keep += 1
        numbered = "\n".join(f"{i + 1}: {line}" for i, line in enumerate(lines[:keep]))
        note = "" if keep == len(lines) else f"\n[truncated after line {keep} of {len(lines)}]"
        blocks.append(f'<source path="{rel}">\n{numbered}{note}\n</source>')
        report.append({"path": rel, "lines": len(lines), "included_lines": keep,
                       "truncated": keep < len(lines)})
    return "<sources>\n" + "\n".join(blocks) + "\n</sources>", report


def build_prompt(context: str, question: str, history: list[dict[str, str]] | None = None) -> str:
    parts = [context]
    for turn in (history or [])[-6:]:
        role = "Jason" if turn.get("role") == "user" else "Tutor"
        parts.append(f"<{role.lower()}>\n{turn.get('text', '')[:4000]}\n</{role.lower()}>")
    parts.append(f"<question>\n{question.strip()}\n</question>")
    return "\n\n".join(parts)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or "note"


def save_note(project_root: Path, *, title: str, question: str, answer: str,
              sources: list[str], backend: str) -> str:
    folder = project_root / LEARNING_DIR
    folder.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC)
    base = f"{now:%Y-%m-%d}-{_slug(title)}"
    path = folder / f"{base}.md"
    n = 2
    while path.exists():
        path = folder / f"{base}-{n}.md"
        n += 1
    post = frontmatter.Post(
        f"## Question\n\n{question.strip()}\n\n## Answer\n\n{answer.strip()}\n",
        title=title, type="study_note", trusted=False, created=now.isoformat(timespec="seconds"),
        backend=backend, sources=sources,
    )
    path.write_text(frontmatter.dumps(post) + "\n", encoding="utf-8")
    return path.relative_to(project_root).as_posix()


def list_notes(project_root: Path) -> list[dict[str, Any]]:
    folder = project_root / LEARNING_DIR
    out = []
    for path in sorted(folder.glob("*.md"), reverse=True) if folder.is_dir() else []:
        try:
            post = frontmatter.load(path)
        except Exception:  # still list it, untitled
            post = frontmatter.Post("")
        out.append({"path": path.relative_to(project_root).as_posix(),
                    "title": str(post.get("title") or path.stem),
                    "created": str(post.get("created") or ""),
                    "sources": post.get("sources") or []})
    return out

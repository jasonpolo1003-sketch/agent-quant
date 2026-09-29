"""One catalogue of what can act on this repo: harness agents, Claude Code skills, Codex skills."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import frontmatter

from quant_brain.harness.registry import RegistryError, load_registry


def harness_agents(project_root: Path) -> list[dict[str, Any]]:
    try:
        registry = load_registry(project_root)
    except RegistryError as exc:
        return [{"name": "registry error", "error": str(exc)}]
    return [
        {
            "name": spec.name,
            "handles": sorted(spec.handles),
            "model": spec.model,
            "enabled": spec.enabled,
            "read_paths": list(spec.allowed_read_paths),
            "write_paths": list(spec.allowed_write_paths),
            "path": spec.path,
        }
        for spec in sorted(registry.values(), key=lambda s: s.name)
    ]


def _skill_files(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.rglob("SKILL.md") if ".git" not in p.parts)


def _describe(path: Path, origin: str, base: Path) -> dict[str, Any]:
    try:
        post = frontmatter.load(path)
        meta = post.metadata
    except Exception:  # an unparseable skill is still listed, flagged
        meta = {"description": "(front matter unreadable)"}
    description = " ".join(str(meta.get("description") or "").split())
    return {
        "name": str(meta.get("name") or path.parent.name),
        "description": description[:300],
        "origin": origin,
        "location": path.parent.relative_to(base).as_posix(),
    }


def skills(project_root: Path, claude_home: Path, codex_home: Path) -> dict[str, list[dict]]:
    claude = [_describe(p, "user", claude_home) for p in _skill_files(claude_home / "skills")]
    claude += [_describe(p, "project", project_root)
               for p in _skill_files(project_root / ".claude" / "skills")]
    codex = [_describe(p, "system" if ".system" in p.parts else "user", codex_home)
             for p in _skill_files(codex_home / "skills")]
    prompts = codex_home / "prompts"
    if prompts.is_dir():
        codex += [{"name": p.stem, "description": "custom prompt", "origin": "prompt",
                   "location": p.relative_to(codex_home).as_posix()}
                  for p in sorted(prompts.glob("*.md"))]
    return {"harness": harness_agents(project_root), "claude": claude, "codex": codex}

from __future__ import annotations

from pathlib import Path


class PathViolation(Exception):
    """Raised when a write target falls outside an agent's declared paths.

    This is the harness's enforcement boundary. Declaration-time validation in
    registry.py rejects obviously unsafe strings; this module resolves the real
    filesystem path -- following `..` and symlinks -- before allowing a write.
    """

    def __init__(self, target: str, allowed: tuple[str, ...] | list[str]) -> None:
        self.target = target
        self.allowed = tuple(allowed)
        super().__init__(
            f"write target {target!r} is outside the agent's allowed write paths "
            f"{list(self.allowed)}"
        )


def _resolve_under_root(project_root: Path, candidate: str | Path) -> Path:
    """Resolve a candidate path, refusing anything that leaves the project root."""
    root = project_root.resolve()
    relative = Path(str(candidate).replace("\\", "/"))
    resolved = relative.resolve() if relative.is_absolute() else (root / relative).resolve()
    if resolved != root and root not in resolved.parents:
        raise PathViolation(str(candidate), ())
    return resolved


def resolve_write_target(
    project_root: str | Path,
    target: str | Path,
    allowed_write_paths: tuple[str, ...] | list[str],
) -> Path:
    """Return the resolved write path, or raise PathViolation.

    Comparison happens on fully resolved paths so that `..` segments and
    symlinks cannot smuggle a write outside the declared directories. String
    prefix checks are not sufficient: `brain/00_Inbox/../../etc/passwd` has an
    allowed prefix but an unallowed destination.
    """
    if not allowed_write_paths:
        raise PathViolation(str(target), ())

    root = Path(project_root).resolve()
    resolved = _resolve_under_root(root, target)

    for allowed in allowed_write_paths:
        try:
            base = _resolve_under_root(root, allowed)
        except PathViolation:
            # A declared path that escapes the root can never authorize a write.
            continue
        if resolved == base or base in resolved.parents:
            return resolved

    raise PathViolation(str(target), allowed_write_paths)


def assert_write_allowed(
    project_root: str | Path,
    target: str | Path,
    allowed_write_paths: tuple[str, ...] | list[str],
) -> None:
    """Raise PathViolation unless the target is inside an allowed write path."""
    resolve_write_target(project_root, target, allowed_write_paths)


def is_write_allowed(
    project_root: str | Path,
    target: str | Path,
    allowed_write_paths: tuple[str, ...] | list[str],
) -> bool:
    """Non-raising variant for callers that want to branch rather than fail."""
    try:
        resolve_write_target(project_root, target, allowed_write_paths)
    except PathViolation:
        return False
    return True

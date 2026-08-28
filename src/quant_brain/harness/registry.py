from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from pathlib import Path
from typing import Any

import frontmatter

from quant_brain.config import PROJECT_ROOT

# Models an agent may declare. Mirrors PLAN.md section 9 (model policy).
# `null` means the agent is deterministic Python and calls no model.
ALLOWED_MODELS = frozenset(
    {
        "qwen3:14b",
        "qwen3.8:27b",
        "nomic-embed-text",
    }
)

REQUIRED_FIELDS = (
    "name",
    "handles",
    "model",
    "enabled",
    "allowed_read_paths",
    "allowed_write_paths",
    "output_contract",
)

_RESERVED_KEYS = frozenset(REQUIRED_FIELDS)


class RegistryError(Exception):
    """Raised when an agent declaration is missing, malformed, or unsafe.

    Loud failure is deliberate: a silently skipped agent is how a harness
    quietly stops doing half its job.
    """


@dataclass(frozen=True)
class AgentSpec:
    name: str
    handles: frozenset[str]
    model: str | None
    enabled: bool
    allowed_read_paths: tuple[str, ...]
    allowed_write_paths: tuple[str, ...]
    output_contract: str
    instructions: str
    path: str
    extras: dict[str, Any] = field(default_factory=dict)

    def handles_task(self, task_type: str) -> bool:
        return task_type in self.handles


def _normalize_path(raw: Any, agent_name: str, field_name: str) -> str:
    """Normalize a declared project-relative path and reject unsafe forms."""
    if not isinstance(raw, str) or not raw.strip():
        raise RegistryError(
            f"{agent_name}: {field_name} entries must be non-empty strings, got {raw!r}"
        )
    value = raw.strip().replace("\\", "/")

    if value.startswith("/") or (len(value) > 1 and value[1] == ":"):
        raise RegistryError(
            f"{agent_name}: {field_name} must be project-relative, got absolute path {raw!r}"
        )

    if value.startswith("./"):
        value = value[2:]

    parts = PurePosixPath(value).parts
    if ".." in parts:
        raise RegistryError(
            f"{agent_name}: {field_name} must not escape the project root, got {raw!r}"
        )
    if not parts:
        raise RegistryError(f"{agent_name}: {field_name} entry resolves to nothing: {raw!r}")

    normalized = "/".join(parts)
    # Preserve the trailing slash convention so directories stay visually distinct
    # from files in packets and in enforcement comparisons.
    if raw.strip().endswith("/") or raw.strip().endswith("\\"):
        normalized += "/"
    return normalized


def _normalize_path_list(raw: Any, agent_name: str, field_name: str) -> tuple[str, ...]:
    if raw is None:
        raise RegistryError(f"{agent_name}: missing required field '{field_name}'")
    if isinstance(raw, str):
        raise RegistryError(
            f"{agent_name}: {field_name} must be a list, not a string ({raw!r})"
        )
    if not isinstance(raw, (list, tuple)):
        raise RegistryError(f"{agent_name}: {field_name} must be a list, got {type(raw).__name__}")
    normalized = tuple(_normalize_path(item, agent_name, field_name) for item in raw)
    if not normalized:
        raise RegistryError(f"{agent_name}: {field_name} cannot be empty")
    return normalized


def _parse_handles(raw: Any, agent_name: str) -> frozenset[str]:
    if raw is None:
        raise RegistryError(f"{agent_name}: missing required field 'handles'")
    if isinstance(raw, str):
        raise RegistryError(
            f"{agent_name}: handles must be a list of task types, not a string ({raw!r})"
        )
    if not isinstance(raw, (list, tuple)):
        raise RegistryError(f"{agent_name}: handles must be a list, got {type(raw).__name__}")
    values = []
    for item in raw:
        if not isinstance(item, str) or not item.strip():
            raise RegistryError(f"{agent_name}: handles entries must be non-empty strings")
        values.append(item.strip())
    if not values:
        raise RegistryError(f"{agent_name}: handles cannot be empty")
    return frozenset(values)


def _parse_model(raw: Any, agent_name: str) -> str | None:
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise RegistryError(f"{agent_name}: model must be a string or null, got {raw!r}")
    value = raw.strip()
    if value.lower() in {"null", "none", ""}:
        return None
    if value not in ALLOWED_MODELS:
        raise RegistryError(
            f"{agent_name}: model {value!r} is not in the allowed set "
            f"{sorted(ALLOWED_MODELS)} (see PLAN.md section 9)"
        )
    return value


def _parse_enabled(raw: Any, agent_name: str) -> bool:
    if isinstance(raw, bool):
        return raw
    raise RegistryError(f"{agent_name}: enabled must be true or false, got {raw!r}")


def has_declaration(project_root: str | Path, name: str) -> bool:
    """Report whether an agent file carries registry frontmatter."""
    path = Path(project_root) / "agents" / f"{name}.md"
    if not path.exists():
        return False
    document = frontmatter.loads(path.read_text(encoding="utf-8"))
    return bool(document.metadata)


def load_agent_spec(project_root: str | Path, name: str) -> AgentSpec:
    """Load and validate one agent declaration from agents/<name>.md."""
    root = Path(project_root)
    path = root / "agents" / f"{name}.md"
    if not path.exists():
        raise RegistryError(f"agent file not found: {path}")

    document = frontmatter.loads(path.read_text(encoding="utf-8"))
    metadata = document.metadata
    if not metadata:
        raise RegistryError(
            f"{name}: agent file has no frontmatter; a registry agent must declare "
            f"{list(REQUIRED_FIELDS)}"
        )

    missing = [key for key in REQUIRED_FIELDS if key not in metadata]
    if missing:
        raise RegistryError(f"{name}: missing required frontmatter fields: {missing}")

    declared_name = metadata["name"]
    if declared_name != name:
        raise RegistryError(
            f"{name}: frontmatter name {declared_name!r} does not match filename stem {name!r}"
        )

    output_contract = metadata["output_contract"]
    if not isinstance(output_contract, str) or not output_contract.strip():
        raise RegistryError(f"{name}: output_contract must be a non-empty string")

    return AgentSpec(
        name=name,
        handles=_parse_handles(metadata.get("handles"), name),
        model=_parse_model(metadata.get("model"), name),
        enabled=_parse_enabled(metadata.get("enabled"), name),
        allowed_read_paths=_normalize_path_list(
            metadata.get("allowed_read_paths"), name, "allowed_read_paths"
        ),
        allowed_write_paths=_normalize_path_list(
            metadata.get("allowed_write_paths"), name, "allowed_write_paths"
        ),
        output_contract=output_contract.strip(),
        instructions=document.content.strip(),
        path=path.relative_to(root).as_posix(),
        extras={k: v for k, v in metadata.items() if k not in _RESERVED_KEYS},
    )


def load_registry(project_root: str | Path = PROJECT_ROOT) -> dict[str, AgentSpec]:
    """Load every agent declaration under agents/.

    Any malformed declaration raises. The registry is all-or-nothing so a broken
    agent surfaces immediately instead of vanishing from dispatch.
    """
    root = Path(project_root)
    agents_dir = root / "agents"
    if not agents_dir.exists():
        raise RegistryError(f"agents directory not found: {agents_dir}")

    registry: dict[str, AgentSpec] = {}
    for path in sorted(agents_dir.glob("*.md")):
        registry[path.stem] = load_agent_spec(root, path.stem)
    return registry


def agents_for_task_type(registry: dict[str, AgentSpec], task_type: str) -> list[AgentSpec]:
    """Return enabled agents declaring the given task type, ordered by name."""
    return sorted(
        (spec for spec in registry.values() if spec.enabled and spec.handles_task(task_type)),
        key=lambda spec: spec.name,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect the agent registry.")
    parser.add_argument("--project-root", default=str(PROJECT_ROOT))
    parser.add_argument("--task-type", default=None, help="Show agents handling this task type.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    registry = load_registry(args.project_root)
    specs = (
        agents_for_task_type(registry, args.task_type)
        if args.task_type
        else sorted(registry.values(), key=lambda spec: spec.name)
    )

    if args.json:
        print(
            json.dumps(
                [
                    {
                        "name": spec.name,
                        "handles": sorted(spec.handles),
                        "model": spec.model,
                        "enabled": spec.enabled,
                        "allowed_read_paths": list(spec.allowed_read_paths),
                        "allowed_write_paths": list(spec.allowed_write_paths),
                        "output_contract": spec.output_contract,
                        "extras": spec.extras,
                    }
                    for spec in specs
                ],
                indent=2,
            )
        )
        return

    if not specs:
        print(f"No enabled agents handle task type: {args.task_type}")
        return
    for spec in specs:
        status = "enabled" if spec.enabled else "disabled"
        print(f"{spec.name}  [{status}]  model={spec.model or 'deterministic'}")
        print(f"  handles: {', '.join(sorted(spec.handles))}")
        print(f"  writes:  {', '.join(spec.allowed_write_paths)}")


if __name__ == "__main__":
    main()

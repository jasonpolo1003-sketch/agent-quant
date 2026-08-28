import pytest

from quant_brain.harness.registry import (
    RegistryError,
    agents_for_task_type,
    has_declaration,
    load_agent_spec,
    load_registry,
)

VALID_FRONTMATTER = """---
name: research_scout
handles: [discovery]
model: qwen3:14b
enabled: true
allowed_read_paths:
  - AGENTS.md
  - brain/01_Sources/
allowed_write_paths:
  - brain/00_Inbox/Raw_Research/
output_contract: raw_research_note_v1
max_sources: 5
---

# Research Scout Agent

Find sources.
"""


def write_agent(root, name, text):
    agents_dir = root / "agents"
    agents_dir.mkdir(exist_ok=True)
    path = agents_dir / f"{name}.md"
    path.write_text(text, encoding="utf-8")
    return path


def test_load_agent_spec_parses_declaration(tmp_path):
    write_agent(tmp_path, "research_scout", VALID_FRONTMATTER)

    spec = load_agent_spec(tmp_path, "research_scout")

    assert spec.name == "research_scout"
    assert spec.handles == frozenset({"discovery"})
    assert spec.model == "qwen3:14b"
    assert spec.enabled is True
    assert spec.allowed_write_paths == ("brain/00_Inbox/Raw_Research/",)
    assert spec.output_contract == "raw_research_note_v1"
    assert spec.extras["max_sources"] == 5
    assert "Find sources" in spec.instructions
    assert spec.path == "agents/research_scout.md"
    assert spec.handles_task("discovery")
    assert not spec.handles_task("curation")


def test_deterministic_agent_may_declare_null_model(tmp_path):
    write_agent(
        tmp_path,
        "knowledge_curator",
        VALID_FRONTMATTER.replace("name: research_scout", "name: knowledge_curator")
        .replace("handles: [discovery]", "handles: [curation]")
        .replace("model: qwen3:14b", "model: null"),
    )

    spec = load_agent_spec(tmp_path, "knowledge_curator")

    assert spec.model is None


def test_missing_frontmatter_raises(tmp_path):
    write_agent(tmp_path, "research_scout", "# Research Scout\n\nNo frontmatter here.")

    with pytest.raises(RegistryError, match="no frontmatter"):
        load_agent_spec(tmp_path, "research_scout")


def test_missing_required_field_raises(tmp_path):
    write_agent(
        tmp_path,
        "research_scout",
        VALID_FRONTMATTER.replace("output_contract: raw_research_note_v1\n", ""),
    )

    with pytest.raises(RegistryError, match="missing required frontmatter fields"):
        load_agent_spec(tmp_path, "research_scout")


def test_name_must_match_filename(tmp_path):
    write_agent(tmp_path, "research_scout", VALID_FRONTMATTER.replace("name: research_scout", "name: other"))

    with pytest.raises(RegistryError, match="does not match filename stem"):
        load_agent_spec(tmp_path, "research_scout")


def test_empty_handles_raises(tmp_path):
    write_agent(tmp_path, "research_scout", VALID_FRONTMATTER.replace("handles: [discovery]", "handles: []"))

    with pytest.raises(RegistryError, match="handles cannot be empty"):
        load_agent_spec(tmp_path, "research_scout")


def test_handles_as_string_raises(tmp_path):
    write_agent(
        tmp_path, "research_scout", VALID_FRONTMATTER.replace("handles: [discovery]", "handles: discovery")
    )

    with pytest.raises(RegistryError, match="must be a list of task types"):
        load_agent_spec(tmp_path, "research_scout")


def test_unknown_model_raises(tmp_path):
    write_agent(tmp_path, "research_scout", VALID_FRONTMATTER.replace("model: qwen3:14b", "model: gpt-4o"))

    with pytest.raises(RegistryError, match="not in the allowed set"):
        load_agent_spec(tmp_path, "research_scout")


@pytest.mark.parametrize(
    "bad_path",
    ["/etc/passwd", "C:/Windows/system32", "../outside/", "brain/../../escape/"],
)
def test_unsafe_paths_are_rejected(tmp_path, bad_path):
    write_agent(
        tmp_path,
        "research_scout",
        VALID_FRONTMATTER.replace("  - brain/00_Inbox/Raw_Research/", f"  - {bad_path}"),
    )

    with pytest.raises(RegistryError):
        load_agent_spec(tmp_path, "research_scout")


def test_non_boolean_enabled_raises(tmp_path):
    write_agent(tmp_path, "research_scout", VALID_FRONTMATTER.replace("enabled: true", "enabled: yes-please"))

    with pytest.raises(RegistryError, match="enabled must be true or false"):
        load_agent_spec(tmp_path, "research_scout")


def test_load_registry_and_task_type_lookup(tmp_path):
    write_agent(tmp_path, "research_scout", VALID_FRONTMATTER)
    write_agent(
        tmp_path,
        "knowledge_curator",
        VALID_FRONTMATTER.replace("name: research_scout", "name: knowledge_curator")
        .replace("handles: [discovery]", "handles: [curation]")
        .replace("model: qwen3:14b", "model: null"),
    )
    write_agent(
        tmp_path,
        "retired_agent",
        VALID_FRONTMATTER.replace("name: research_scout", "name: retired_agent").replace(
            "enabled: true", "enabled: false"
        ),
    )

    registry = load_registry(tmp_path)

    assert set(registry) == {"research_scout", "knowledge_curator", "retired_agent"}
    assert [s.name for s in agents_for_task_type(registry, "discovery")] == ["research_scout"]
    assert [s.name for s in agents_for_task_type(registry, "curation")] == ["knowledge_curator"]
    # A disabled agent never becomes a dispatch candidate.
    assert agents_for_task_type(registry, "discovery") == [registry["research_scout"]]
    assert agents_for_task_type(registry, "nonexistent") == []


def test_load_registry_fails_loudly_on_one_bad_agent(tmp_path):
    write_agent(tmp_path, "research_scout", VALID_FRONTMATTER)
    write_agent(tmp_path, "broken", "# Broken\n\nNo frontmatter.")

    with pytest.raises(RegistryError):
        load_registry(tmp_path)


def test_has_declaration_distinguishes_migrated_agents(tmp_path):
    write_agent(tmp_path, "research_scout", VALID_FRONTMATTER)
    write_agent(tmp_path, "legacy", "# Legacy\n\nNo frontmatter.")

    assert has_declaration(tmp_path, "research_scout") is True
    assert has_declaration(tmp_path, "legacy") is False
    assert has_declaration(tmp_path, "missing") is False


def test_real_project_agents_load(tmp_path):
    """The shipped agent files must be valid declarations."""
    from quant_brain.config import PROJECT_ROOT

    registry = load_registry(PROJECT_ROOT)

    assert "research_scout" in registry
    assert "knowledge_curator" in registry
    assert registry["research_scout"].handles_task("discovery")
    assert registry["knowledge_curator"].handles_task("curation")
    # Curator must not be able to write strategy cards: that needs a human gate (PLAN.md Phase 8).
    assert not any(
        "03_Strategy_Cards" in path for path in registry["knowledge_curator"].allowed_write_paths
    )

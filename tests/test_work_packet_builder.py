from pathlib import Path

import pytest

from quant_brain.agents.work_packet import (
    AgentWorkPacket,
    build_work_packet,
    format_work_packet_markdown,
    load_agent_role,
    save_work_packet,
)
from quant_brain.db.init_db import connect, init_database
from quant_brain.harness.registry import RegistryError
from quant_brain.indexing.embeddings import HASH_MODEL, embed_pending_chunks

DECLARED_SCOUT = """---
name: research_scout
handles: [discovery]
model: qwen3:14b
enabled: true
allowed_read_paths:
  - brain/01_Sources/
allowed_write_paths:
  - brain/00_Inbox/Raw_Research/
  - brain/00_Inbox/Source_Snapshots/
output_contract: raw_research_note_v1
---

# Research Scout Agent

Find sources.
"""


def seed_declared_scout(root):
    agents_dir = root / "agents"
    agents_dir.mkdir(exist_ok=True)
    (agents_dir / "research_scout.md").write_text(DECLARED_SCOUT, encoding="utf-8")


def seed_context(db_path):
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO notes (note_id, path, title, type)
            VALUES ('SRC-lookahead', 'brain/01_Sources/docs/lookahead.md', 'Lookahead', 'source_note')
            """
        )
        conn.execute(
            """
            INSERT INTO chunks (
                chunk_id, note_id, heading_path, text_hash, text,
                token_count, start_line, end_line, embedding_status
            ) VALUES (
                'CHUNK-lookahead', 'SRC-lookahead', 'Lookahead > Evidence',
                'hash1', 'Lookahead bias uses future data and can make a backtest cheat.',
                10, 1, 2, 'pending'
            )
            """
        )
        conn.commit()
    embed_pending_chunks(db_path, model=HASH_MODEL, dimensions=64)


def test_load_agent_role_reads_agent_markdown(tmp_path):
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    (agents_dir / "research_scout.md").write_text("# Research Scout\n\n## Job\n\nFind sources.", encoding="utf-8")

    role = load_agent_role(tmp_path, "research_scout")

    assert role["agent_role"] == "research_scout"
    assert "Find sources" in role["instructions"]
    assert role["path"] == "agents/research_scout.md"


def test_format_work_packet_markdown_has_task_role_context_files_and_output_contract():
    packet = AgentWorkPacket(
        packet_id="WP-test",
        agent_role="research_scout",
        task="Research ETF mean reversion",
        role_instructions="# Research Scout\nFind sources.",
        retrieved_context="# Retrieved Context Packet\ncontext",
        allowed_read_paths=["brain/01_Sources/"],
        allowed_write_paths=["brain/00_Inbox/Raw_Research/"],
        output_contract="Write one raw research note and final JSON block.",
    )

    text = format_work_packet_markdown(packet)

    assert "# Agent Work Packet — WP-test" in text
    assert "research_scout" in text
    assert "Research ETF mean reversion" in text
    assert "# Retrieved Context Packet" in text
    assert "brain/00_Inbox/Raw_Research/" in text
    assert "Write one raw research note" in text
    assert "Do not edit outside allowed write paths" in text


def test_build_work_packet_combines_role_and_retrieval_context(tmp_path):
    db_path = tmp_path / "brain.sqlite"
    init_database(db_path)
    seed_context(db_path)
    (tmp_path / "agents").mkdir()
    (tmp_path / "agents" / "knowledge_curator.md").write_text(
        "# Knowledge Curator\n\n## Job\n\nPromote useful sources.", encoding="utf-8"
    )

    packet = build_work_packet(
        project_root=tmp_path,
        db_path=db_path,
        agent_role="knowledge_curator",
        task="Review lookahead bias source notes",
        retrieval_query="future data lookahead bias",
        allowed_read_paths=["brain/01_Sources/"],
        allowed_write_paths=["brain/00_Inbox/Curator_Reviews/", "brain/01_Sources/"],
        output_contract="Return promote_source or needs_more_work.",
        model=HASH_MODEL,
        dimensions=64,
        log_retrieval=True,
    )

    assert packet.agent_role == "knowledge_curator"
    assert "Promote useful sources" in packet.role_instructions
    assert "CHUNK-lookahead" in packet.retrieved_context
    assert packet.retrieval_query_id is not None
    assert "brain/01_Sources/" in packet.allowed_read_paths


def test_declared_agent_paths_are_used_when_caller_passes_none(tmp_path):
    db_path = tmp_path / "brain.sqlite"
    init_database(db_path)
    seed_context(db_path)
    seed_declared_scout(tmp_path)

    packet = build_work_packet(
        project_root=tmp_path,
        db_path=db_path,
        agent_role="research_scout",
        task="Find RSI exit rules",
        model=HASH_MODEL,
        dimensions=64,
    )

    assert packet.allowed_write_paths == [
        "brain/00_Inbox/Raw_Research/",
        "brain/00_Inbox/Source_Snapshots/",
    ]
    assert packet.allowed_read_paths == ["brain/01_Sources/"]
    # The agent's declared contract wins over the generic default.
    assert packet.output_contract == "raw_research_note_v1"


def test_caller_may_narrow_declared_paths(tmp_path):
    db_path = tmp_path / "brain.sqlite"
    init_database(db_path)
    seed_context(db_path)
    seed_declared_scout(tmp_path)

    packet = build_work_packet(
        project_root=tmp_path,
        db_path=db_path,
        agent_role="research_scout",
        task="Find RSI exit rules",
        allowed_write_paths=["brain/00_Inbox/Raw_Research/"],
        model=HASH_MODEL,
        dimensions=64,
    )

    assert packet.allowed_write_paths == ["brain/00_Inbox/Raw_Research/"]


def test_caller_cannot_widen_declared_paths(tmp_path):
    db_path = tmp_path / "brain.sqlite"
    init_database(db_path)
    seed_context(db_path)
    seed_declared_scout(tmp_path)

    with pytest.raises(RegistryError, match="narrowing is allowed, widening is not"):
        build_work_packet(
            project_root=tmp_path,
            db_path=db_path,
            agent_role="research_scout",
            task="Find RSI exit rules",
            allowed_write_paths=["brain/01_Sources/"],
            model=HASH_MODEL,
        dimensions=64,
        )


def test_save_work_packet_writes_markdown_and_records_agent_task(tmp_path):
    db_path = tmp_path / "brain.sqlite"
    init_database(db_path)
    packet = AgentWorkPacket(
        packet_id="WP-save",
        agent_role="research_scout",
        task="Research task",
        role_instructions="Role instructions",
        retrieved_context="Context",
        allowed_read_paths=["brain/"],
        allowed_write_paths=["brain/00_Inbox/"],
        output_contract="Output contract",
    )

    path = save_work_packet(tmp_path, db_path, packet)

    assert Path(path).exists()
    text = Path(path).read_text(encoding="utf-8")
    assert "WP-save" in text
    with connect(db_path) as conn:
        row = conn.execute("select task_id, agent_role, status, input_path from agent_tasks").fetchone()
    assert row["task_id"] == "WP-save"
    assert row["agent_role"] == "research_scout"
    assert row["status"] == "ready"
    assert row["input_path"] == str(path)

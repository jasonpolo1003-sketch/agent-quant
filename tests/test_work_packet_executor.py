from pathlib import Path

import pytest

from quant_brain.agents.executor import execute_work_packet
from quant_brain.agents.work_packet import AgentWorkPacket, save_work_packet
from quant_brain.db.init_db import connect, init_database


def make_packet(
    tmp_path: Path,
    db_path: Path,
    *,
    packet_id: str = "WP-execute",
    allowed_write_paths: list[str] | None = None,
    task: str = "Review whether lookahead bias should update the validation checklist",
    evidence_text: str = "A strategy can appear profitable when it uses future data.",
) -> Path:
    packet = AgentWorkPacket(
        packet_id=packet_id,
        agent_role="knowledge_curator",
        task=task,
        role_instructions="# Knowledge Curator\nPreserve uncertainty.",
        retrieved_context=f"""# Retrieved Context Packet

## Retrieved Chunks

### Context 1

- chunk_id: CHUNK-lookahead
- note_id: SRC-lookahead
- path: brain/01_Sources/docs/lookahead.md
- heading: Lookahead Bias > Risks
- score: 0.9000

```text
{evidence_text}
```
""",
        allowed_read_paths=["brain/01_Sources/"],
        allowed_write_paths=(
            allowed_write_paths
            if allowed_write_paths is not None
            else ["brain/00_Inbox/Curator_Reviews/"]
        ),
        output_contract=(
            "Return a curator note with recommendation, cited source paths/headings, "
            "and exact proposed checklist change."
        ),
    )
    return Path(save_work_packet(tmp_path, db_path, packet))


def test_execute_work_packet_writes_cited_result_and_completes_database_task(tmp_path):
    db_path = tmp_path / "brain.sqlite"
    init_database(db_path)
    packet_path = make_packet(tmp_path, db_path)

    result = execute_work_packet(tmp_path, db_path, packet_path)

    output_path = Path(result.output_path)
    assert output_path.exists()
    assert output_path.parent == tmp_path / "brain" / "00_Inbox" / "Curator_Reviews"
    text = output_path.read_text(encoding="utf-8")
    assert "brain/01_Sources/docs/lookahead.md" in text
    assert "Lookahead Bias > Risks" in text
    assert "Confirm every signal input was available at the simulated decision time" in text
    assert result.status == "completed"

    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT status, output_path, started_at, completed_at, error "
            "FROM agent_tasks WHERE task_id = ?",
            ("WP-execute",),
        ).fetchone()
    assert row["status"] == "completed"
    assert row["output_path"] == str(output_path)
    assert row["started_at"] is not None
    assert row["completed_at"] is not None
    assert row["error"] is None


def test_execute_work_packet_rejects_write_path_escape_and_records_failure(tmp_path):
    db_path = tmp_path / "brain.sqlite"
    init_database(db_path)
    packet_path = make_packet(
        tmp_path,
        db_path,
        packet_id="WP-escape",
        allowed_write_paths=["../outside/"],
    )

    # Enforcement lives in harness.paths; a declared path that escapes the root
    # cannot authorize a write, so no allowed path remains.
    with pytest.raises(ValueError, match="outside the agent's allowed write paths"):
        execute_work_packet(tmp_path, db_path, packet_path)

    assert not (tmp_path.parent / "outside" / "WP-escape-result.md").exists()
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT status, output_path, completed_at, error "
            "FROM agent_tasks WHERE task_id = ?",
            ("WP-escape",),
        ).fetchone()
    assert row["status"] == "failed"
    assert row["output_path"] is None
    assert row["completed_at"] is not None
    assert "outside the agent's allowed write paths" in row["error"]


def test_execute_work_packet_rejects_unsupported_deterministic_task(tmp_path):
    db_path = tmp_path / "brain.sqlite"
    init_database(db_path)
    packet_path = make_packet(
        tmp_path,
        db_path,
        packet_id="WP-unsupported",
        task="Draft a momentum strategy card",
        evidence_text="Momentum is a broad method family.",
    )

    with pytest.raises(ValueError, match="does not support this task"):
        execute_work_packet(tmp_path, db_path, packet_path)

    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT status, error FROM agent_tasks WHERE task_id = ?",
            ("WP-unsupported",),
        ).fetchone()
    assert row["status"] == "failed"
    assert "does not support this task" in row["error"]

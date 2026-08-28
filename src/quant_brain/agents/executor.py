from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

from quant_brain.config import PROJECT_ROOT
from quant_brain.db.init_db import DEFAULT_DB_PATH, connect, init_database
from quant_brain.harness.paths import PathViolation, resolve_write_target

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
TOP_LEVEL_SECTION_NAMES = (
    "Agent Role|Task|Role Instructions|Retrieved Context|Allowed Read Paths|"
    "Allowed Write Paths|Output Contract|Guardrails"
)
SECTION_RE = re.compile(
    rf"^## ({TOP_LEVEL_SECTION_NAMES})\s*$\n(.*?)(?=^## (?:{TOP_LEVEL_SECTION_NAMES})\s*$|\Z)",
    re.MULTILINE | re.DOTALL,
)
CONTEXT_RE = re.compile(
    r"^### Context \d+\s*\n.*?^- path: (?P<path>.+?)\s*$"
    r".*?^- heading: (?P<heading>.+?)\s*$"
    r".*?```text\s*\n(?P<text>.*?)\n```",
    re.MULTILINE | re.DOTALL,
)
BACKTICK_ITEM_RE = re.compile(r"^- `([^`]+)`\s*$", re.MULTILINE)


@dataclass(frozen=True)
class RetrievedEvidence:
    path: str
    heading: str
    text: str


@dataclass(frozen=True)
class ParsedWorkPacket:
    packet_id: str
    agent_role: str
    task: str
    output_contract: str
    allowed_write_paths: list[str]
    evidence: list[RetrievedEvidence]


@dataclass(frozen=True)
class WorkPacketExecutionResult:
    packet_id: str
    status: str
    output_path: str
    citation_count: int


def parse_work_packet(packet_path: str | Path) -> ParsedWorkPacket:
    """Parse the bounded fields needed by the deterministic executor."""
    text = Path(packet_path).read_text(encoding="utf-8")
    frontmatter_match = FRONTMATTER_RE.search(text)
    if not frontmatter_match:
        raise ValueError("work packet is missing YAML frontmatter")
    frontmatter = {}
    for line in frontmatter_match.group(1).splitlines():
        key, separator, value = line.partition(":")
        if separator:
            frontmatter[key.strip()] = value.strip()

    sections = {name.strip(): body.strip() for name, body in SECTION_RE.findall(text)}
    packet_id = frontmatter.get("id", "")
    agent_role = frontmatter.get("agent_role", "")
    task = sections.get("Task", "")
    output_contract = sections.get("Output Contract", "")
    write_paths = BACKTICK_ITEM_RE.findall(sections.get("Allowed Write Paths", ""))
    retrieved_context = sections.get("Retrieved Context", "")
    evidence = [
        RetrievedEvidence(
            path=match.group("path").strip(),
            heading=match.group("heading").strip(),
            text=match.group("text").strip(),
        )
        for match in CONTEXT_RE.finditer(retrieved_context)
    ]

    if not packet_id or not agent_role or not task:
        raise ValueError("work packet is missing id, agent_role, or task")
    if not write_paths:
        raise ValueError("work packet has no allowed write path")
    if not evidence:
        raise ValueError("work packet has no retrieved evidence to cite")
    return ParsedWorkPacket(
        packet_id=packet_id,
        agent_role=agent_role,
        task=task,
        output_contract=output_contract,
        allowed_write_paths=write_paths,
        evidence=evidence,
    )


def _resolve_allowed_output(project_root: str | Path, allowed_path: str, packet_id: str) -> Path:
    """Resolve this packet's output file inside its declared write path.

    Enforcement lives in harness.paths so there is one implementation shared by
    the harness and this executor.
    """
    target = f"{allowed_path.rstrip('/')}/{packet_id}-result.md"
    try:
        output_path = resolve_write_target(project_root, target, [allowed_path])
    except PathViolation as exc:
        raise ValueError(str(exc)) from exc
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return output_path


def _format_result(packet: ParsedWorkPacket) -> str:
    evidence = packet.evidence[0]
    supported_text = f"{packet.task}\n{evidence.text}".lower()
    if "lookahead" not in supported_text and "future data" not in supported_text:
        raise ValueError(
            "deterministic-v1 does not support this task; use a reviewed template or model executor"
        )
    return f"""---
id: {packet.packet_id}-result
type: agent_work_packet_result
work_packet_id: {packet.packet_id}
agent_role: {packet.agent_role}
status: completed
executor: deterministic-v1
---

# Work Packet Result — {packet.packet_id}

## Task

{packet.task}

## Recommendation

Update the pre-backtest validation checklist. The retrieved evidence says future data can make a strategy appear profitable, so this control should be explicit before strategy testing.

## Exact Proposed Checklist Change

- Confirm every signal input was available at the simulated decision time; for close-based signals, execute no earlier than the next bar unless the data and execution timing prove otherwise.

## Evidence Citation

- Path: `{evidence.path}`
- Heading: `{evidence.heading}`
- Evidence: {evidence.text}

## Output Contract

{packet.output_contract}

## Execution Limits

This is a deterministic evidence-based draft. It did not run a model, edit a strategy card, execute a backtest, or place a trade.
"""


def validate_result_citations(output_text: str, evidence: list[RetrievedEvidence]) -> int:
    """Require at least one retrieved path-and-heading pair in the result."""
    citation_count = sum(
        1 for item in evidence if item.path in output_text and item.heading in output_text
    )
    if citation_count == 0:
        raise ValueError("executor output does not cite a retrieved path and heading")
    return citation_count


def execute_work_packet(
    project_root: str | Path = PROJECT_ROOT,
    db_path: str | Path = DEFAULT_DB_PATH,
    packet_path: str | Path = "",
) -> WorkPacketExecutionResult:
    """Execute one work packet with a deterministic evidence-based renderer."""
    packet = parse_work_packet(packet_path)
    init_database(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT task_id FROM agent_tasks WHERE task_id = ?", (packet.packet_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"agent task not found: {packet.packet_id}")
        conn.execute(
            """
            UPDATE agent_tasks
            SET status = 'running', started_at = CURRENT_TIMESTAMP,
                completed_at = NULL, error = NULL
            WHERE task_id = ?
            """,
            (packet.packet_id,),
        )
        conn.commit()

    try:
        output_path = _resolve_allowed_output(
            project_root, packet.allowed_write_paths[0], packet.packet_id
        )
        output_text = _format_result(packet)
        citation_count = validate_result_citations(output_text, packet.evidence)
        output_path.write_text(output_text, encoding="utf-8")

        with connect(db_path) as conn:
            conn.execute(
                """
                UPDATE agent_tasks
                SET status = 'completed', output_path = ?,
                    completed_at = CURRENT_TIMESTAMP, error = NULL
                WHERE task_id = ?
                """,
                (str(output_path), packet.packet_id),
            )
            conn.commit()
    except Exception as exc:
        with connect(db_path) as conn:
            conn.execute(
                """
                UPDATE agent_tasks
                SET status = 'failed', output_path = NULL,
                    completed_at = CURRENT_TIMESTAMP, error = ?
                WHERE task_id = ?
                """,
                (str(exc), packet.packet_id),
            )
            conn.commit()
        raise

    return WorkPacketExecutionResult(
        packet_id=packet.packet_id,
        status="completed",
        output_path=str(output_path),
        citation_count=citation_count,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Execute one deterministic agent work packet.")
    parser.add_argument("packet_path")
    parser.add_argument("--project-root", default=str(PROJECT_ROOT))
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    args = parser.parse_args()
    result = execute_work_packet(args.project_root, args.db, args.packet_path)
    print(json.dumps(result.__dict__, indent=2))


if __name__ == "__main__":
    main()

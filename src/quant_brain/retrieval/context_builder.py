from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from quant_brain.db.init_db import DEFAULT_DB_PATH, connect, init_database
from quant_brain.indexing.embeddings import DEFAULT_MODEL, search_similar_chunks


def _chunk_ids(chunks: list[dict[str, Any]]) -> list[str]:
    return [str(chunk["chunk_id"]) for chunk in chunks]


def _answer_hash(markdown: str) -> str:
    return hashlib.sha256(markdown.encode("utf-8")).hexdigest()


def format_context_markdown(query: str, chunks: list[dict[str, Any]]) -> str:
    """Format retrieved chunks into a bounded agent context packet."""
    lines = [
        "# Retrieved Context Packet",
        "",
        "## Query",
        "",
        query,
        "",
        "## How To Use",
        "",
        "Use this context as evidence, not as proof. Cite the file path and heading when making claims. If the context is weak or missing, say so instead of guessing.",
        "",
        "## Retrieved Chunks",
        "",
    ]
    if not chunks:
        lines.extend(["No chunks retrieved.", ""])
        return "\n".join(lines)

    for idx, chunk in enumerate(chunks, start=1):
        lines.extend(
            [
                f"### Context {idx}",
                "",
                f"- chunk_id: {chunk['chunk_id']}",
                f"- note_id: {chunk['note_id']}",
                f"- path: {chunk['note_path']}",
                f"- heading: {chunk['heading_path']}",
                f"- score: {chunk['score']:.4f}",
                "",
                "```text",
                str(chunk["text"]).strip(),
                "```",
                "",
            ]
        )
    return "\n".join(lines)


def log_retrieval(
    db_path: str | Path,
    packet: dict[str, Any],
    agent_id: str | None = None,
    task_id: str | None = None,
) -> str:
    """Record a retrieval packet in retrieval_log for auditability."""
    init_database(db_path)
    query_id = f"QUERY-{uuid4().hex[:10]}"
    final_ids = _chunk_ids(packet["chunks"])
    with connect(db_path) as conn:
        if task_id:
            conn.execute(
                """
                INSERT INTO agent_tasks (task_id, agent_role, status)
                VALUES (?, ?, 'context_retrieval')
                ON CONFLICT(task_id) DO NOTHING
                """,
                (task_id, agent_id or "unknown_agent"),
            )
        conn.execute(
            """
            INSERT INTO retrieval_log (
                query_id, agent_id, task_id, query_text, filters_json,
                retrieved_chunk_ids_json, final_chunk_ids_json, answer_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                query_id,
                agent_id,
                task_id,
                packet["query"],
                json.dumps(packet.get("filters", {})),
                json.dumps(final_ids),
                json.dumps(final_ids),
                _answer_hash(packet["markdown"]),
            ),
        )
        conn.commit()
    return query_id


def build_retrieval_context(
    db_path: str | Path,
    query: str,
    limit: int = 5,
    model: str = DEFAULT_MODEL,
    dimensions: int | None = None,
    agent_id: str | None = None,
    task_id: str | None = None,
    log: bool = False,
) -> dict[str, Any]:
    """Search indexed chunks and package them for an agent."""
    if not query.strip():
        raise ValueError("query cannot be empty")
    chunks = search_similar_chunks(
        db_path=db_path,
        query=query,
        limit=limit,
        model=model,
        dimensions=dimensions,
    )
    packet: dict[str, Any] = {
        "query": query,
        "model": model,
        "dimensions": dimensions,
        "limit": limit,
        "filters": {},
        "chunks": chunks,
        "markdown": format_context_markdown(query, chunks),
    }
    if log:
        packet["query_id"] = log_retrieval(db_path, packet, agent_id=agent_id, task_id=task_id)
    return packet


def main() -> None:
    parser = argparse.ArgumentParser(description="Build retrieval context packets for agents.")
    parser.add_argument("query")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--dimensions", type=int, default=None)
    parser.add_argument("--agent-id", default=None)
    parser.add_argument("--task-id", default=None)
    parser.add_argument("--log", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    packet = build_retrieval_context(
        db_path=args.db,
        query=args.query,
        limit=args.limit,
        model=args.model,
        dimensions=args.dimensions,
        agent_id=args.agent_id,
        task_id=args.task_id,
        log=args.log,
    )
    if args.json:
        print(json.dumps(packet, indent=2))
    else:
        print(packet["markdown"])


if __name__ == "__main__":
    main()

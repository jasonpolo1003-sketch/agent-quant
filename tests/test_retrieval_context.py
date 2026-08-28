import json

from quant_brain.db.init_db import connect, init_database
from quant_brain.indexing.embeddings import HASH_MODEL, embed_pending_chunks
from quant_brain.retrieval.context_builder import (
    build_retrieval_context,
    format_context_markdown,
    log_retrieval,
)


def seed_chunk(db_path, chunk_id, note_id, path, heading, text):
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO notes (note_id, path, title, type)
            VALUES (?, ?, ?, 'source_note')
            ON CONFLICT(note_id) DO NOTHING
            """,
            (note_id, path, note_id),
        )
        conn.execute(
            """
            INSERT INTO chunks (
                chunk_id, note_id, heading_path, text_hash, text,
                token_count, start_line, end_line, embedding_status
            ) VALUES (?, ?, ?, ?, ?, 10, 1, 2, 'pending')
            """,
            (chunk_id, note_id, heading, chunk_id + '-hash', text),
        )
        conn.commit()


def setup_indexed_db(tmp_path):
    db_path = tmp_path / "brain.sqlite"
    init_database(db_path)
    seed_chunk(
        db_path,
        "CHUNK-lookahead",
        "SRC-lookahead",
        "brain/01_Sources/docs/lookahead.md",
        "Lookahead > Evidence",
        "Lookahead bias uses future data and can make a backtest cheat.",
    )
    seed_chunk(
        db_path,
        "CHUNK-rsi",
        "SRC-rsi",
        "brain/01_Sources/web/rsi.md",
        "RSI > Summary",
        "RSI identifies overbought and oversold market conditions.",
    )
    embed_pending_chunks(db_path, model=HASH_MODEL, dimensions=64)
    return db_path


def test_format_context_markdown_includes_citations_paths_scores_and_rules():
    chunks = [
        {
            "chunk_id": "CHUNK-1",
            "note_id": "SRC-1",
            "note_path": "brain/01_Sources/docs/source.md",
            "heading_path": "Source > Evidence",
            "text": "Evidence text.",
            "score": 0.42,
        }
    ]

    text = format_context_markdown("lookahead bias", chunks)

    assert "# Retrieved Context Packet" in text
    assert "Query" in text
    assert "lookahead bias" in text
    assert "brain/01_Sources/docs/source.md" in text
    assert "Source > Evidence" in text
    assert "score: 0.4200" in text
    assert "Use this context as evidence, not as proof" in text


def test_build_retrieval_context_returns_markdown_and_structured_chunks(tmp_path):
    db_path = setup_indexed_db(tmp_path)

    packet = build_retrieval_context(db_path, "future data lookahead bias", limit=1, model=HASH_MODEL, dimensions=64)

    assert packet["query"] == "future data lookahead bias"
    assert len(packet["chunks"]) == 1
    assert packet["chunks"][0]["chunk_id"] == "CHUNK-lookahead"
    assert "CHUNK-lookahead" in packet["markdown"]
    assert "brain/01_Sources/docs/lookahead.md" in packet["markdown"]


def test_log_retrieval_records_query_and_selected_chunks(tmp_path):
    db_path = setup_indexed_db(tmp_path)
    packet = build_retrieval_context(db_path, "future data lookahead bias", limit=2, model=HASH_MODEL, dimensions=64)

    query_id = log_retrieval(db_path, packet, agent_id="curator", task_id="TASK-1")

    assert query_id.startswith("QUERY-")
    with connect(db_path) as conn:
        row = conn.execute("select * from retrieval_log where query_id = ?", (query_id,)).fetchone()

    assert row["agent_id"] == "curator"
    assert row["task_id"] == "TASK-1"
    assert row["query_text"] == "future data lookahead bias"
    final_ids = json.loads(row["final_chunk_ids_json"])
    assert "CHUNK-lookahead" in final_ids


def test_build_retrieval_context_can_log_when_requested(tmp_path):
    db_path = setup_indexed_db(tmp_path)

    packet = build_retrieval_context(
        db_path,
        "future data lookahead bias",
        limit=1,
        model=HASH_MODEL,
        dimensions=64,
        agent_id="research_scout",
        task_id="RQ-1",
        log=True,
    )

    assert packet["query_id"].startswith("QUERY-")
    with connect(db_path) as conn:
        assert conn.execute("select count(*) from retrieval_log").fetchone()[0] == 1

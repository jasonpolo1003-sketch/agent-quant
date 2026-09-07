from quant_brain.db.init_db import connect, init_database
from quant_brain.indexing.embeddings import (
    HASH_MODEL,
    cosine_similarity,
    embed_pending_chunks,
    hash_embed_text,
    search_similar_chunks,
)


def seed_chunk(db_path, chunk_id, text):
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO notes (note_id, path, title, type)
            VALUES ('NOTE-1', 'note.md', 'Note', 'source_note')
            ON CONFLICT(note_id) DO NOTHING
            """
        )
        conn.execute(
            """
            INSERT INTO chunks (
                chunk_id, note_id, heading_path, text_hash, text,
                token_count, start_line, end_line, embedding_status
            ) VALUES (?, 'NOTE-1', 'Note > Section', ?, ?, 10, 1, 2, 'pending')
            """,
            (chunk_id, chunk_id + '-hash', text),
        )
        conn.commit()


def test_hash_embed_text_returns_normalized_fixed_size_vector():
    vec = hash_embed_text("lookahead bias next bar execution", dimensions=32)

    assert len(vec) == 32
    assert abs(sum(v * v for v in vec) - 1.0) < 1e-9
    assert hash_embed_text("lookahead bias next bar execution", dimensions=32) == vec


def test_cosine_similarity_scores_related_vectors_higher_than_unrelated():
    query = hash_embed_text("lookahead bias future data")
    related = hash_embed_text("avoid lookahead future data in backtests")
    unrelated = hash_embed_text("volume candles moving average")

    assert cosine_similarity(query, related) > cosine_similarity(query, unrelated)


def test_embed_pending_chunks_creates_embedding_rows_and_marks_chunks_embedded(tmp_path):
    db_path = tmp_path / "brain.sqlite"
    init_database(db_path)
    seed_chunk(db_path, "CHUNK-1", "Lookahead bias means using future data.")
    seed_chunk(db_path, "CHUNK-2", "RSI can define oversold conditions.")

    result = embed_pending_chunks(db_path, model=HASH_MODEL, dimensions=32)

    assert result["embedded_count"] == 2
    with connect(db_path) as conn:
        rows = conn.execute("select chunk_id, model, dimensions from embeddings order by chunk_id").fetchall()
        statuses = conn.execute("select embedding_status from chunks order by chunk_id").fetchall()

    assert [dict(r) for r in rows] == [
        {"chunk_id": "CHUNK-1", "model": "local-hash-embedding-v1", "dimensions": 32},
        {"chunk_id": "CHUNK-2", "model": "local-hash-embedding-v1", "dimensions": 32},
    ]
    assert [r["embedding_status"] for r in statuses] == ["embedded", "embedded"]


def test_search_similar_chunks_returns_best_matching_chunk(tmp_path):
    db_path = tmp_path / "brain.sqlite"
    init_database(db_path)
    seed_chunk(db_path, "CHUNK-lookahead", "Lookahead bias uses future data and can make a backtest cheat.")
    seed_chunk(db_path, "CHUNK-rsi", "RSI identifies overbought and oversold market conditions.")
    embed_pending_chunks(db_path, model=HASH_MODEL, dimensions=64)

    results = search_similar_chunks(db_path, "future data lookahead bias", limit=1, model=HASH_MODEL, dimensions=64)

    assert len(results) == 1
    assert results[0]["chunk_id"] == "CHUNK-lookahead"
    assert results[0]["score"] > 0

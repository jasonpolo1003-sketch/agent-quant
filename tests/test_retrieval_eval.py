"""Retrieval-eval tests.

These run against the HASH backend only, so the suite never requires Ollama.
The semantic backend's quality is measured by running scripts/retrieval_eval.py
manually; see brain/00_Inbox/Model_Evaluations/.
"""

import sys
from pathlib import Path

from quant_brain.db.init_db import connect, init_database
from quant_brain.indexing.embeddings import HASH_MODEL, embed_pending_chunks

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from retrieval_eval import evaluate


def seed(db_path, note_id, path, heading, text, chunk_id):
    with connect(db_path) as conn:
        conn.execute(
            "INSERT INTO notes (note_id, path, title, type) VALUES (?, ?, ?, 'source_note') "
            "ON CONFLICT(note_id) DO NOTHING",
            (note_id, path, note_id),
        )
        conn.execute(
            """
            INSERT INTO chunks (
                chunk_id, note_id, heading_path, text_hash, text,
                token_count, start_line, end_line, embedding_status
            ) VALUES (?, ?, ?, ?, ?, 10, 1, 2, 'pending')
            """,
            (chunk_id, note_id, heading, f"hash-{chunk_id}", text),
        )
        conn.commit()


def test_evaluate_reports_recall_and_mrr(tmp_path):
    db_path = tmp_path / "brain.sqlite"
    init_database(db_path)
    seed(
        db_path,
        "SRC-lookahead",
        "brain/01_Sources/docs/look-ahead-bias.md",
        "Lookahead",
        "Lookahead bias means a backtest used future data unavailable at decision time.",
        "CHUNK-1",
    )
    seed(
        db_path,
        "SRC-rsi",
        "brain/01_Sources/docs/relative-strength-index.md",
        "RSI",
        "The relative strength index compares average gains to average losses over a period.",
        "CHUNK-2",
    )
    embed_pending_chunks(db_path, model=HASH_MODEL, dimensions=64)

    fixtures = (
        ("lookahead bias future data", "look-ahead-bias"),
        ("relative strength index average gains", "relative-strength-index"),
    )
    report = evaluate(db_path, model=HASH_MODEL, limit=5, fixtures=fixtures, dimensions=64)

    assert report["model"] == HASH_MODEL
    assert report["fixture_count"] == 2
    assert report["recall_at_5"] == 1.0
    assert report["recall_at_1"] == 1.0
    assert report["mrr"] == 1.0
    assert all(row["rank"] == 1 for row in report["results"])


def test_evaluate_reports_a_miss_as_none_rank(tmp_path):
    db_path = tmp_path / "brain.sqlite"
    init_database(db_path)
    seed(
        db_path,
        "SRC-rsi",
        "brain/01_Sources/docs/relative-strength-index.md",
        "RSI",
        "The relative strength index compares average gains to average losses.",
        "CHUNK-1",
    )
    embed_pending_chunks(db_path, model=HASH_MODEL, dimensions=64)

    fixtures = (("something entirely absent from the corpus", "nonexistent-note"),)
    report = evaluate(db_path, model=HASH_MODEL, limit=5, fixtures=fixtures, dimensions=64)

    assert report["recall_at_5"] == 0.0
    assert report["mrr"] == 0.0
    assert report["results"][0]["rank"] is None

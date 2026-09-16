from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

from quant_brain.db.init_db import DEFAULT_DB_PATH, connect, init_database
from quant_brain.llm.ollama_client import DEFAULT_EMBED_MODEL
from quant_brain.llm.ollama_client import embed as ollama_embed

# The hash backend is lexical, not semantic: it matches only on shared literal
# tokens. It stays registered because pytest must never require Ollama, but it
# is no longer the default -- see brain/_system/embedding_indexer_workflow.md.
HASH_MODEL = "local-hash-embedding-v1"
HASH_DIMENSIONS = 256

DEFAULT_MODEL = DEFAULT_EMBED_MODEL
DEFAULT_DIMENSIONS = 768

TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_'-]*")


def tokenize(text: str) -> list[str]:
    return [token.lower().strip("'\"") for token in TOKEN_RE.findall(text)]


def hash_embed_text(text: str, dimensions: int = DEFAULT_DIMENSIONS) -> list[float]:
    """Create a deterministic local embedding vector using feature hashing.

    This is a lightweight baseline: free, offline, reproducible, and good enough
    to test the RAG plumbing before swapping in a semantic model.
    """
    if dimensions <= 0:
        raise ValueError("dimensions must be positive")
    vector = [0.0] * dimensions
    for token in tokenize(text):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[idx] += sign
    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0:
        return vector
    return [v / norm for v in vector]


def embed_text(text: str, model: str = DEFAULT_MODEL, dimensions: int | None = None) -> list[float]:
    """Embed text with the named backend.

    The hash backend is deterministic and offline (used by tests); every other
    model name is served by the local Ollama server.
    """
    if model == HASH_MODEL:
        return hash_embed_text(text, dimensions=dimensions or HASH_DIMENSIONS)
    return ollama_embed(text, model=model)


def backend_dimensions(model: str, requested: int | None = None) -> int:
    """Resolve the vector width for a backend."""
    if model == HASH_MODEL:
        return requested or HASH_DIMENSIONS
    if requested:
        return requested
    return DEFAULT_DIMENSIONS


def vector_norm(vector: list[float]) -> float:
    return math.sqrt(sum(v * v for v in vector))


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("vectors must have the same dimensions")
    left_norm = vector_norm(left)
    right_norm = vector_norm(right)
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return sum(a * b for a, b in zip(left, right, strict=True)) / (left_norm * right_norm)


def embed_pending_chunks(
    db_path: str | Path = DEFAULT_DB_PATH,
    model: str = DEFAULT_MODEL,
    dimensions: int | None = None,
    limit: int | None = None,
    reembed_all: bool = False,
) -> dict[str, Any]:
    """Embed chunks and store vectors in SQLite.

    By default only chunks marked pending are processed. ``reembed_all`` ignores
    that status, which is how a new backend backfills vectors for chunks another
    model already embedded -- the (chunk_id, model) primary key lets both
    backends coexist.
    """
    init_database(db_path)
    dimensions = backend_dimensions(model, dimensions)
    sql = "SELECT chunk_id, text FROM chunks"
    if not reembed_all:
        sql += " WHERE embedding_status = 'pending'"
    sql += " ORDER BY created_at ASC, chunk_id ASC"
    params: tuple[Any, ...] = ()
    if limit is not None:
        sql += " LIMIT ?"
        params = (limit,)

    with connect(db_path) as conn:
        rows = conn.execute(sql, params).fetchall()
        for row in rows:
            vector = embed_text(row["text"], model=model, dimensions=dimensions)
            conn.execute(
                """
                INSERT INTO embeddings (chunk_id, model, dimensions, vector_json, vector_norm, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(chunk_id, model) DO UPDATE SET
                    dimensions = excluded.dimensions,
                    vector_json = excluded.vector_json,
                    vector_norm = excluded.vector_norm,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (row["chunk_id"], model, len(vector), json.dumps(vector), vector_norm(vector)),
            )
            conn.execute(
                """
                UPDATE chunks
                SET embedding_status = 'embedded', embedding_model = ?, vector_id = ?, updated_at = CURRENT_TIMESTAMP
                WHERE chunk_id = ?
                """,
                (model, f"{model}:{row['chunk_id']}", row["chunk_id"]),
            )
        conn.commit()
    return {"model": model, "dimensions": dimensions, "embedded_count": len(rows)}


def search_similar_chunks(
    db_path: str | Path,
    query: str,
    limit: int = 5,
    model: str = DEFAULT_MODEL,
    dimensions: int | None = None,
) -> list[dict[str, Any]]:
    """Return chunks ranked by cosine similarity to a query."""
    query_vector = embed_text(query, model=model, dimensions=dimensions)
    init_database(db_path)
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT
                c.chunk_id,
                c.note_id,
                n.path AS note_path,
                c.heading_path,
                c.text,
                e.vector_json
            FROM embeddings e
            JOIN chunks c ON c.chunk_id = e.chunk_id
            JOIN notes n ON n.note_id = c.note_id
            WHERE e.model = ? AND e.dimensions = ?
            """,
            (model, len(query_vector)),
        ).fetchall()

    if not rows:
        # An empty result here usually means a dimension mismatch, not an empty
        # corpus: vectors were stored at one width and the query built another.
        # Silence would look like "nothing relevant found", so say what happened.
        with connect(db_path) as conn:
            stored = conn.execute(
                "SELECT model, dimensions, COUNT(*) AS n FROM embeddings GROUP BY model, dimensions"
            ).fetchall()
        if stored:
            available = ", ".join(f"{r['model']}@{r['dimensions']} ({r['n']})" for r in stored)
            raise ValueError(
                f"no embeddings for model {model!r} at {len(query_vector)} dimensions; "
                f"stored: {available}. Re-embed with this model or pass matching dimensions."
            )

    scored = []
    for row in rows:
        vector = json.loads(row["vector_json"])
        scored.append(
            {
                "chunk_id": row["chunk_id"],
                "note_id": row["note_id"],
                "note_path": row["note_path"],
                "heading_path": row["heading_path"],
                "text": row["text"],
                "score": cosine_similarity(query_vector, vector),
            }
        )
    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:limit]


def main() -> None:
    parser = argparse.ArgumentParser(description="Embed indexed Markdown chunks and search them.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    embed_cmd = sub.add_parser("embed")
    embed_cmd.add_argument("--db", default=str(DEFAULT_DB_PATH))
    embed_cmd.add_argument("--model", default=DEFAULT_MODEL)
    embed_cmd.add_argument("--dimensions", type=int, default=None)
    embed_cmd.add_argument("--limit", type=int, default=None)
    embed_cmd.add_argument(
        "--reembed-all",
        action="store_true",
        help="Embed every chunk, not just pending ones (use when switching backends).",
    )

    search_cmd = sub.add_parser("search")
    search_cmd.add_argument("query")
    search_cmd.add_argument("--db", default=str(DEFAULT_DB_PATH))
    search_cmd.add_argument("--model", default=DEFAULT_MODEL)
    search_cmd.add_argument("--dimensions", type=int, default=None)
    search_cmd.add_argument("--limit", type=int, default=5)

    args = parser.parse_args()
    if args.cmd == "embed":
        print(
            json.dumps(
                embed_pending_chunks(
                    args.db, args.model, args.dimensions, args.limit, args.reembed_all
                ),
                indent=2,
            )
        )
    elif args.cmd == "search":
        print(json.dumps(search_similar_chunks(args.db, args.query, args.limit, args.model, args.dimensions), indent=2))


if __name__ == "__main__":
    main()

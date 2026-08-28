from __future__ import annotations

from pathlib import Path

from quant_brain.db.init_db import DEFAULT_DB_PATH, connect, init_database

# Columns added after the original schema shipped. `init_database` runs
# CREATE TABLE IF NOT EXISTS, which will not alter an existing table, so
# additive columns need this guarded pass. Kept deliberately tiny: a full
# migration framework is overkill for a single-user local SQLite file.
ADDITIVE_COLUMNS: tuple[tuple[str, str, str], ...] = (
    ("agent_tasks", "task_type", "TEXT"),
    ("agent_tasks", "run_id", "TEXT"),
)


def _existing_columns(conn, table: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}


def apply_migrations(db_path: str | Path = DEFAULT_DB_PATH) -> list[str]:
    """Add any missing additive columns. Idempotent and safe on a populated DB."""
    init_database(db_path)
    applied: list[str] = []
    with connect(db_path) as conn:
        for table, column, column_type in ADDITIVE_COLUMNS:
            if column not in _existing_columns(conn, table):
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
                applied.append(f"{table}.{column}")
        conn.commit()
    return applied


if __name__ == "__main__":
    changes = apply_migrations()
    print(f"Applied: {changes}" if changes else "Schema already current.")

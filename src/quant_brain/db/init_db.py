from __future__ import annotations

import sqlite3
from pathlib import Path

from quant_brain.config import DB_DIR

SCHEMA_PATH = Path(__file__).with_name("schema.sql")
DEFAULT_DB_PATH = DB_DIR / "brain.sqlite"


def init_database(db_path: str | Path = DEFAULT_DB_PATH) -> Path:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(schema)
        conn.commit()
    return path


def connect(db_path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(Path(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


if __name__ == "__main__":
    created = init_database()
    print(f"Initialized database: {created}")

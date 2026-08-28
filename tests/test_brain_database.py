import sqlite3

from quant_brain.db.init_db import connect, init_database


REQUIRED_TABLES = {
    "notes",
    "sources",
    "chunks",
    "strategy_cards",
    "backtests",
    "metrics",
    "reviews",
    "agent_tasks",
    "retrieval_log",
}


def table_names(db_path):
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "select name from sqlite_master where type = 'table' and name not like 'sqlite_%'"
        ).fetchall()
    return {row[0] for row in rows}


def column_names(db_path, table):
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(f"pragma table_info({table})").fetchall()
    return {row[1] for row in rows}


def test_init_database_creates_required_tables(tmp_path):
    db_path = tmp_path / "brain.sqlite"

    init_database(db_path)

    assert REQUIRED_TABLES.issubset(table_names(db_path))


def test_strategy_cards_table_tracks_lifecycle_fields(tmp_path):
    db_path = tmp_path / "brain.sqlite"

    init_database(db_path)

    columns = column_names(db_path, "strategy_cards")
    assert {
        "strategy_id",
        "title",
        "method_family",
        "status",
        "stage",
        "confidence",
        "note_path",
        "created_at",
        "updated_at",
    }.issubset(columns)


def test_backtests_table_links_strategy_dataset_and_code(tmp_path):
    db_path = tmp_path / "brain.sqlite"

    init_database(db_path)

    columns = column_names(db_path, "backtests")
    assert {
        "backtest_id",
        "strategy_id",
        "dataset_id",
        "code_commit",
        "config_json",
        "status",
        "started_at",
        "completed_at",
    }.issubset(columns)


def test_connect_helper_enables_foreign_keys(tmp_path):
    db_path = tmp_path / "brain.sqlite"

    init_database(db_path)

    with connect(db_path) as conn:
        foreign_keys = conn.execute("pragma foreign_keys").fetchone()[0]

    assert foreign_keys == 1

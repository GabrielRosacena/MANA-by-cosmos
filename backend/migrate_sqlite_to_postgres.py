from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import psycopg2
from psycopg2 import sql

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv(*args, **kwargs):
        return False


TABLE_ORDER = [
    ("clusters", ["id"]),
    ("users", ["username"]),
    ("system_settings", ["section"]),
    ("posts", ["id"]),
    ("comments", ["id"]),
    ("preprocessed_texts", ["id"]),
    ("watchlists", ["id"]),
    ("post_topics", ["id"]),
    ("post_clusters", ["id"]),
    ("sentiments", ["id"]),
    ("post_priorities", ["id"]),
    ("activity_logs", ["id"]),
]

BOOLEAN_COLUMNS = {
    ("posts", "is_relevant"),
    ("preprocessed_texts", "is_emotion_only"),
    ("preprocessed_texts", "is_relevant"),
    ("sentiments", "sarcasm_flag"),
}


def get_backend_dir() -> Path:
    return Path(__file__).resolve().parent


def sqlite_db_path() -> Path:
    return get_backend_dir() / "instance" / "mana.db"


def build_upsert_sql(table_name: str, columns: list[str], pk_columns: list[str]):
    insert_columns = sql.SQL(", ").join(sql.Identifier(column) for column in columns)
    insert_values = sql.SQL(", ").join(sql.Placeholder() for _ in columns)
    conflict_target = sql.SQL(", ").join(sql.Identifier(column) for column in pk_columns)
    update_columns = [column for column in columns if column not in pk_columns]

    if update_columns:
        set_clause = sql.SQL(", ").join(
            sql.SQL("{} = EXCLUDED.{}").format(sql.Identifier(column), sql.Identifier(column))
            for column in update_columns
        )
        conflict_action = sql.SQL("DO UPDATE SET {}").format(set_clause)
    else:
        conflict_action = sql.SQL("DO NOTHING")

    return sql.SQL(
        "INSERT INTO {table} ({columns}) VALUES ({values}) "
        "ON CONFLICT ({conflict_target}) {conflict_action}"
    ).format(
        table=sql.Identifier(table_name),
        columns=insert_columns,
        values=insert_values,
        conflict_target=conflict_target,
        conflict_action=conflict_action,
    )


def sync_sequence(pg_conn, table_name: str, pk_column: str):
    with pg_conn.cursor() as cur:
        cur.execute("SELECT pg_get_serial_sequence(%s, %s)", (table_name, pk_column))
        sequence_name = cur.fetchone()[0]
        if not sequence_name:
            return
        cur.execute(
            sql.SQL(
                "SELECT setval(%s, COALESCE((SELECT MAX({pk}) FROM {table}), 1), "
                "(SELECT COUNT(*) > 0 FROM {table}))"
            ).format(
                pk=sql.Identifier(pk_column),
                table=sql.Identifier(table_name),
            ),
            (sequence_name,),
        )


def normalize_value(table_name: str, column_name: str, value):
    if (table_name, column_name) in BOOLEAN_COLUMNS and value is not None:
        return bool(value)
    return value


def migrate():
    backend_dir = get_backend_dir()
    load_dotenv(backend_dir / ".env")

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise SystemExit("DATABASE_URL is not set in backend/.env")

    sqlite_path = sqlite_db_path()
    if not sqlite_path.exists():
        raise SystemExit(f"SQLite database not found: {sqlite_path}")

    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    pg_conn = psycopg2.connect(db_url)

    try:
        migrated_counts = {}
        with pg_conn:
            for table_name, pk_columns in TABLE_ORDER:
                sqlite_rows = sqlite_conn.execute(
                    f'SELECT * FROM "{table_name}"'
                ).fetchall()
                migrated_counts[table_name] = len(sqlite_rows)
                if not sqlite_rows:
                    continue

                columns = list(sqlite_rows[0].keys())
                statement = build_upsert_sql(table_name, columns, pk_columns)

                with pg_conn.cursor() as cur:
                    for row in sqlite_rows:
                        cur.execute(
                            statement,
                            [normalize_value(table_name, column, row[column]) for column in columns],
                        )

                if len(pk_columns) == 1 and "id" in pk_columns:
                    sync_sequence(pg_conn, table_name, "id")

        return migrated_counts
    finally:
        sqlite_conn.close()
        pg_conn.close()


if __name__ == "__main__":
    results = migrate()
    for table_name, count in results.items():
        print(f"{table_name}: migrated {count}")

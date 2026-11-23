import argparse
import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import (
    MetaData,
    Table,
    create_engine,
    func,
    inspect,
    select,
    text,
)
from sqlalchemy.engine import Connection, Engine, URL

from app.database.db import engine as target_engine


APPLICATION_TABLES = (
    "users",
    "products",
    "orders",
    "tickets",
    "order_items",
    "ticket_messages",
    "ticket_status_history",
)
BASELINE_REVISION = "2046a0fd4f04"
BATCH_SIZE = 500


def _canonical_value(value: Any) -> tuple[str, Any]:
    if isinstance(value, Decimal):
        return ("decimal", str(value))
    if isinstance(value, (datetime, date)):
        return (type(value).__name__, value.isoformat())
    if isinstance(value, bytes):
        return ("bytes", value.hex())
    return (type(value).__name__, value)


def _table_digest(connection: Connection, table: Table) -> tuple[int, str]:
    column_names = sorted(column.name for column in table.columns)
    primary_key_names = [
        column.name for column in table.primary_key.columns
    ]
    if not primary_key_names:
        raise ValueError(f"Table {table.name!r} has no primary key.")

    statement = select(
        *(table.c[name] for name in column_names)
    ).order_by(*(table.c[name] for name in primary_key_names))
    result = connection.execute(statement)
    digest = hashlib.sha256()
    row_count = 0
    while rows := result.fetchmany(BATCH_SIZE):
        for row in rows:
            encoded = json.dumps(
                [_canonical_value(value) for value in row],
                ensure_ascii=True,
                separators=(",", ":"),
            ).encode("utf-8")
            digest.update(len(encoded).to_bytes(8, "big"))
            digest.update(encoded)
            row_count += 1
    return row_count, digest.hexdigest()


def _reflected_tables(connection: Connection) -> dict[str, Table]:
    existing_tables = set(inspect(connection).get_table_names())
    missing_tables = set(APPLICATION_TABLES) - existing_tables
    if missing_tables:
        raise RuntimeError(
            "SQLite source is missing application tables: "
            f"{', '.join(sorted(missing_tables))}."
        )
    metadata = MetaData()
    metadata.reflect(bind=connection, only=APPLICATION_TABLES)
    return {name: metadata.tables[name] for name in APPLICATION_TABLES}


def _check_source(connection: Connection) -> dict[str, Table]:
    integrity = connection.exec_driver_sql("PRAGMA integrity_check").scalar_one()
    if integrity != "ok":
        raise RuntimeError(f"SQLite integrity check failed: {integrity}")

    violations = connection.exec_driver_sql(
        "PRAGMA foreign_key_check"
    ).fetchmany(1)
    if violations:
        raise RuntimeError(
            "SQLite foreign-key check found violations; refusing to copy data."
        )

    tables = _reflected_tables(connection)
    return tables


def _check_target(
    connection: Connection,
) -> dict[str, Table]:
    existing_tables = set(inspect(connection).get_table_names())
    missing_tables = set(APPLICATION_TABLES) - existing_tables
    if missing_tables:
        raise RuntimeError(
            "PostgreSQL schema is incomplete. Apply migrations before copying "
            f"data; missing tables: {', '.join(sorted(missing_tables))}."
        )
    if "alembic_version" not in existing_tables:
        raise RuntimeError(
            "PostgreSQL has no Alembic migration history. Apply migrations "
            "before copying data."
        )

    revisions = connection.execute(
        text("SELECT version_num FROM alembic_version")
    ).scalars().all()
    if revisions != [BASELINE_REVISION]:
        raise RuntimeError(
            "PostgreSQL schema revision is not the expected initial baseline. "
            "Apply or review migrations before copying data."
        )

    tables = _reflected_tables(connection)
    nonempty = [
        name
        for name, table in tables.items()
        if connection.execute(
            select(func.count()).select_from(table)
        ).scalar_one()
    ]
    if nonempty:
        raise RuntimeError(
            "PostgreSQL application tables are not empty; refusing to "
            f"overwrite or mix data: {', '.join(nonempty)}."
        )
    return tables


def migrate_sqlite_to_postgres(
    source_path: Path,
    destination: Engine,
) -> dict[str, dict[str, int | str]]:
    source_path = source_path.expanduser().resolve()
    if not source_path.is_file():
        raise FileNotFoundError(f"SQLite source file not found: {source_path}")
    if destination.dialect.name != "postgresql":
        raise ValueError("The destination DATABASE_URL must use PostgreSQL.")

    source = create_engine(
        URL.create("sqlite", database=str(source_path)),
        connect_args={"check_same_thread": False},
    )
    try:
        with source.connect() as source_connection:
            source_tables = _check_source(source_connection)
            source_digests = {
                name: _table_digest(source_connection, source_tables[name])
                for name in APPLICATION_TABLES
            }

            with destination.begin() as target_connection:
                target_tables = _check_target(target_connection)
                for name in APPLICATION_TABLES:
                    source_table = source_tables[name]
                    target_table = target_tables[name]
                    source_columns = set(source_table.columns.keys())
                    target_columns = set(target_table.columns.keys())
                    if source_columns != target_columns:
                        raise RuntimeError(
                            f"Column mismatch for {name}: SQLite has "
                            f"{sorted(source_columns)}, PostgreSQL has "
                            f"{sorted(target_columns)}."
                        )

                    primary_key = list(source_table.primary_key.columns)
                    result = source_connection.execute(
                        select(source_table).order_by(*primary_key)
                    )
                    while rows := result.fetchmany(BATCH_SIZE):
                        records = [
                            dict(row._mapping) for row in rows
                        ]
                        target_connection.execute(target_table.insert(), records)

                for name in APPLICATION_TABLES:
                    source_count, source_digest = source_digests[name]
                    target_count, target_digest = _table_digest(
                        target_connection, target_tables[name]
                    )
                    if (target_count, target_digest) != (
                        source_count,
                        source_digest,
                    ):
                        raise RuntimeError(
                            f"PostgreSQL verification failed for {name}; "
                            "the transaction will be rolled back."
                        )

                    max_id = target_connection.execute(
                        select(func.max(target_tables[name].c.id))
                    ).scalar_one()
                    target_connection.execute(
                        text(
                            "SELECT setval("
                            "pg_get_serial_sequence(:table_name, 'id')::regclass, "
                            ":last_value, :is_called)"
                        ),
                        {
                            "table_name": name,
                            "last_value": max_id or 1,
                            "is_called": max_id is not None,
                        },
                    )

        return {
            name: {
                "rows": source_digests[name][0],
                "sha256": source_digests[name][1],
            }
            for name in APPLICATION_TABLES
        }
    finally:
        source.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Copy a verified SQLite database into an empty PostgreSQL "
            "database configured by DATABASE_URL."
        )
    )
    parser.add_argument(
        "--source",
        required=True,
        type=Path,
        help="Path to a backed-up SQLite database file.",
    )
    args = parser.parse_args()

    migrated = migrate_sqlite_to_postgres(args.source, target_engine)
    print("SQLite data copied and verified successfully.")
    for table, result in migrated.items():
        print(
            f"{table}: {result['rows']} rows "
            f"(sha256 {result['sha256']})"
        )


if __name__ == "__main__":
    main()

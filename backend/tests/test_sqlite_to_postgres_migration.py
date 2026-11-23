import pytest
from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine

from migrate_sqlite_to_postgres import (
    APPLICATION_TABLES,
    _check_target,
    migrate_sqlite_to_postgres,
)


def test_migration_requires_existing_sqlite_source(tmp_path):
    destination = create_engine("sqlite:///:memory:")
    try:
        with pytest.raises(FileNotFoundError, match="SQLite source file not found"):
            migrate_sqlite_to_postgres(
                tmp_path / "missing.db",
                destination,
            )
    finally:
        destination.dispose()


def test_migration_requires_postgresql_destination(tmp_path):
    source_path = tmp_path / "source.db"
    source_path.touch()
    destination = create_engine("sqlite:///:memory:")
    try:
        with pytest.raises(ValueError, match="destination DATABASE_URL"):
            migrate_sqlite_to_postgres(source_path, destination)
    finally:
        destination.dispose()


def test_target_guard_rejects_nonempty_application_tables():
    engine = create_engine("sqlite:///:memory:")
    metadata = MetaData()
    application_tables = {
        name: Table(name, metadata, Column("id", Integer, primary_key=True))
        for name in APPLICATION_TABLES
    }
    alembic_version = Table(
        "alembic_version",
        metadata,
        Column("version_num", String, primary_key=True),
    )
    metadata.create_all(engine)

    with engine.begin() as connection:
        connection.execute(
            alembic_version.insert().values(version_num="2046a0fd4f04")
        )
        connection.execute(application_tables["users"].insert().values(id=1))

    try:
        with engine.connect() as connection:
            with pytest.raises(RuntimeError, match="refusing to overwrite"):
                _check_target(connection)
    finally:
        engine.dispose()

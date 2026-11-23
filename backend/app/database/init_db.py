from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.database.db import engine


_APPLICATION_TABLES = {
    "users",
    "products",
    "orders",
    "order_items",
    "tickets",
    "ticket_messages",
    "ticket_status_history",
}


def main():
    backend_dir = Path(__file__).resolve().parents[2]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option(
        "script_location", str(backend_dir / "migrations")
    )
    with engine.connect() as connection:
        existing_tables = set(inspect(connection).get_table_names())
    if (
        "alembic_version" not in existing_tables
        and existing_tables.intersection(_APPLICATION_TABLES)
    ):
        raise RuntimeError(
            "An existing database without Alembic version history was found. "
            "Back it up and verify its schema, then run "
            "`python -m alembic stamp head` once before initializing it."
        )
    command.upgrade(config, "head")
    print("Database migrations applied successfully.")


if __name__ == "__main__":
    main()

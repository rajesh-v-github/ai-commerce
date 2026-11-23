from sqlalchemy import event

from app.database.db import create_database_engine


def test_sqlite_engine_uses_thread_compatible_connection_option():
    engine = create_database_engine("sqlite:///:memory:")
    connection_options = {}

    @event.listens_for(engine, "do_connect")
    def capture_connection_options(_dialect, _connection_record, _args, kwargs):
        connection_options.update(kwargs)
        return engine.dialect.connect(*_args, **kwargs)

    try:
        assert engine.dialect.name == "sqlite"
        with engine.connect():
            pass
        assert connection_options["check_same_thread"] is False
    finally:
        engine.dispose()


def test_postgresql_url_uses_psycopg_driver():
    engine = create_database_engine(
        "postgresql://user:password@localhost/ai_commerce"
    )
    try:
        assert engine.dialect.name == "postgresql"
        assert engine.url.drivername == "postgresql+psycopg"
    finally:
        engine.dispose()

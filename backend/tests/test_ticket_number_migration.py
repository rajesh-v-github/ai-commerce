from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy import text

from app.api import copilot as copilot_api
from app.database.migrations import ensure_ticket_number_column
from app.schemas.copilot import CopilotInsightsRequest


def test_migration_adds_ticket_numbers_without_changing_primary_keys():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE tickets ("
                "id INTEGER PRIMARY KEY, subject VARCHAR)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO tickets (id, subject) VALUES "
                "(1, 'First'), (2, 'Second'), (15, 'Fifteenth')"
            )
        )

    ensure_ticket_number_column(engine)

    with engine.connect() as connection:
        rows = connection.execute(
            text('SELECT id, "TicketNumber" FROM tickets ORDER BY id')
        ).fetchall()
        assert rows == [
            (1, "TKT-001"),
            (2, "TKT-002"),
            (15, "TKT-015"),
        ]

    ensure_ticket_number_column(engine)

    with engine.connect() as connection:
        assert connection.execute(
            text('SELECT COUNT(*) FROM tickets WHERE "TicketNumber" IS NULL')
        ).scalar_one() == 0

    engine.dispose()


def test_ticket_summary_resolves_ticket_number_to_internal_id(monkeypatch):
    ticket = SimpleNamespace(id=42, ticket_number="TKT-042", user_id=7)
    ticket_summary = {"ticket": ticket}

    class TicketQuery:
        def filter(self, _condition):
            return self

        def first(self):
            return ticket

    class Database:
        def query(self, _model):
            return TicketQuery()

    internal_ids = []
    monkeypatch.setattr(
        copilot_api,
        "get_ticket_summary",
        lambda _db, ticket_id: internal_ids.append(ticket_id) or ticket_summary,
    )
    monkeypatch.setattr(
        copilot_api, "generate_executive_summary", lambda _db, _id: {}
    )
    monkeypatch.setattr(copilot_api, "recommend_next_action", lambda _db, _id: {})
    monkeypatch.setattr(copilot_api, "generate_draft_response", lambda _db, _id: {})
    monkeypatch.setattr(copilot_api, "get_customer_360", lambda _db, _id: {})

    result = copilot_api.get_copilot_insights(
        CopilotInsightsRequest(ticket_number=" tkt-042 "),
        Database(),
        SimpleNamespace(),
    )

    assert internal_ids == [42]
    assert result["ticket_summary"] is ticket_summary

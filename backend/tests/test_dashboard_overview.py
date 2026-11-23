from datetime import datetime
from datetime import timedelta
from datetime import timezone
from decimal import Decimal
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.dashboard import get_dashboard_overview
from app.database.db import Base
from app.models.order import Order
from app.models.ticket import Ticket
from app.models.ticket_message import TicketMessage
from app.models.ticket_status_history import TicketStatusHistory
from app.models.user import User


def test_dashboard_overview_returns_operational_metrics_and_real_activity():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    today = now.date()

    with Session(engine) as db:
        user = User(username="support", password_hash="hash", role="support")
        db.add(user)
        db.flush()

        high_priority = Ticket(
            ticket_number="TKT-001",
            user_id=user.id,
            subject="Urgent issue",
            status="IN_PROGRESS",
            priority="HIGH",
        )
        open_ticket = Ticket(
            ticket_number="TKT-002",
            user_id=user.id,
            subject="New issue",
            status="OPEN",
            priority="MEDIUM",
        )
        resolved_ticket = Ticket(
            ticket_number="TKT-003",
            user_id=user.id,
            subject="Completed issue",
            status="RESOLVED",
            priority="LOW",
        )
        db.add_all([high_priority, open_ticket, resolved_ticket])
        db.flush()

        db.add_all(
            [
                Order(
                    order_number="ORD-001",
                    customer_id=user.id,
                    customer_name="Customer",
                    status="DELIVERED",
                    total_amount=Decimal("42.50"),
                    idempotency_key="order-001",
                ),
                Order(
                    order_number="ORD-002",
                    customer_id=user.id,
                    customer_name="Customer",
                    status="PROCESSING",
                    total_amount=Decimal("12.00"),
                    idempotency_key="order-002",
                ),
            ]
        )
        db.add_all(
            [
                TicketMessage(
                    ticket_id=high_priority.id,
                    user_id=user.id,
                    message="Recent customer reply",
                    created_at=now - timedelta(days=1),
                ),
                TicketMessage(
                    ticket_id=resolved_ticket.id,
                    user_id=user.id,
                    message="Previous period reply",
                    created_at=now - timedelta(days=8),
                ),
                TicketStatusHistory(
                    ticket_id=high_priority.id,
                    changed_by_user_id=user.id,
                    old_status="OPEN",
                    new_status="IN_PROGRESS",
                    changed_at=now - timedelta(days=1),
                ),
            ]
        )
        db.commit()

        result = get_dashboard_overview(db, SimpleNamespace())

    assert result["total_tickets"] == 3
    assert result["total_orders"] == 2
    assert result["ticket_status_counts"] == {
        "OPEN": 1,
        "IN_PROGRESS": 1,
        "RESOLVED": 1,
        "CLOSED": 0,
    }
    assert result["order_status_counts"] == {"DELIVERED": 1, "PROCESSING": 1}
    assert result["attention_tickets"][0]["ticket_number"] == "TKT-001"
    assert result["attention_tickets"][1]["ticket_number"] == "TKT-002"
    assert result["attention_tickets"][1]["days_since_activity"] is None
    assert result["recent_orders"][0]["order_number"] == "ORD-002"
    assert result["ticket_activity_trend"]["current_period_count"] == 2
    assert result["ticket_activity_trend"]["previous_period_count"] == 1
    assert result["ticket_activity_trend"]["change_percent"] == 100
    assert len(result["ticket_activity_trend"]["daily"]) == 7
    assert result["ticket_activity_trend"]["daily"][-1]["date"] == today.isoformat()
    assert len(result["recent_activity"]) == 3

    engine.dispose()


def test_dashboard_overview_handles_no_activity_without_comparison_period():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    with Session(engine) as db:
        result = get_dashboard_overview(db, SimpleNamespace())

    assert result["ticket_activity_trend"]["current_period_count"] == 0
    assert result["ticket_activity_trend"]["previous_period_count"] == 0
    assert result["ticket_activity_trend"]["change_percent"] is None
    assert all(day["count"] == 0 for day in result["ticket_activity_trend"]["daily"])

    engine.dispose()

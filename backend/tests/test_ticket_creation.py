import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.tickets import create_ticket
from app.database.db import Base
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.ticket import TicketCreate


@pytest.fixture
def ticket_database():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        yield db
    engine.dispose()


def create_user(db, username, role):
    user = User(username=username, password_hash="hash", role=role)
    db.add(user)
    db.flush()
    return user


def test_support_ticket_is_assigned_to_selected_customer(ticket_database):
    support_user = create_user(ticket_database, "support", "support")
    customer = create_user(ticket_database, "customer", "customer")

    ticket = create_ticket(
        TicketCreate(
            subject="Damaged item",
            description="The item arrived damaged.",
            priority="HIGH",
            customer_id=customer.id,
        ),
        ticket_database,
        support_user,
    )

    assert ticket.user_id == customer.id
    assert ticket.ticket_number == f"TKT-{ticket.id:03d}"
    assert ticket.status == "OPEN"


def test_support_ticket_requires_customer_selection(ticket_database):
    support_user = create_user(ticket_database, "support", "support")

    with pytest.raises(HTTPException) as error:
        create_ticket(
            TicketCreate(subject="Issue", description="Details"),
            ticket_database,
            support_user,
        )

    assert error.value.status_code == 422
    assert ticket_database.query(Ticket).count() == 0


def test_support_cannot_assign_ticket_to_non_customer(ticket_database):
    support_user = create_user(ticket_database, "support", "support")
    other_support = create_user(ticket_database, "other-support", "support")

    with pytest.raises(HTTPException) as error:
        create_ticket(
            TicketCreate(
                subject="Issue",
                description="Details",
                customer_id=other_support.id,
            ),
            ticket_database,
            support_user,
        )

    assert error.value.status_code == 404


def test_customer_ticket_remains_assigned_to_current_user(ticket_database):
    customer = create_user(ticket_database, "customer", "customer")

    ticket = create_ticket(
        TicketCreate(subject="Issue", description="Details"),
        ticket_database,
        customer,
    )

    assert ticket.user_id == customer.id


def test_customer_cannot_create_ticket_for_another_customer(ticket_database):
    customer = create_user(ticket_database, "customer", "customer")
    other_customer = create_user(ticket_database, "other-customer", "customer")

    with pytest.raises(HTTPException) as error:
        create_ticket(
            TicketCreate(
                subject="Issue",
                description="Details",
                customer_id=other_customer.id,
            ),
            ticket_database,
            customer,
        )

    assert error.value.status_code == 403

# app/models/ticket_status_history.py

from datetime import datetime

from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import ForeignKey
from sqlalchemy import DateTime

from app.database.db import Base


class TicketStatusHistory(Base):

    __tablename__ = "ticket_status_history"

    id = Column(
        Integer,
        primary_key=True
    )

    ticket_id = Column(
        Integer,
        ForeignKey("tickets.id")
    )

    changed_by_user_id = Column(
        Integer,
        ForeignKey("users.id")
    )

    old_status = Column(String)

    new_status = Column(String)

    changed_at = Column(
        DateTime,
        default=datetime.utcnow
    )
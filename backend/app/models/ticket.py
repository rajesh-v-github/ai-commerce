from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import ForeignKey

from app.database.db import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True)

    ticket_number = Column("TicketNumber", String, nullable=True)

    user_id = Column(Integer, ForeignKey("users.id"))

    subject = Column(String)
    description = Column(String)
    status = Column(String)

    priority = Column(String, default="MEDIUM")

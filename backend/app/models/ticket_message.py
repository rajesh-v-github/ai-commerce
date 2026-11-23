from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import ForeignKey
from datetime import datetime
from sqlalchemy import DateTime
from sqlalchemy.orm import relationship

from app.database.db import Base

class TicketMessage(Base):
    __tablename__ = "ticket_messages"
    id = Column(
        Integer,
        primary_key=True
    )
    ticket_id = Column(
        Integer,
        ForeignKey("tickets.id")
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id")
    )
    
    message = Column(String)
    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )
    user = relationship("User")
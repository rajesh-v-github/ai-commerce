from typing import Optional

from pydantic import BaseModel

from enum import Enum


class TicketStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class TicketCreate(BaseModel):
    subject: str
    description: str
    priority: str = "MEDIUM"
    customer_id: Optional[int] = None


class TicketStatusUpdate(BaseModel):
    status: TicketStatus


class TicketMessageCreate(BaseModel):
    message: str

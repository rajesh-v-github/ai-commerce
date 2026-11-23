from typing import Optional
from pydantic import BaseModel


class CopilotRequest(BaseModel):
    customer_id: Optional[int] = None
    ticket_id: Optional[int] = None
    question: str


class CopilotInsightsRequest(BaseModel):
    ticket_number: str


class AIAssistantRequest(BaseModel):
    feature: str
    customer_id: Optional[int] = None
    ticket_id: Optional[int] = None
    order_id: Optional[int] = None
    question: str

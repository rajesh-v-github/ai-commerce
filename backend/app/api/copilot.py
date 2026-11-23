from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.database.db import get_db

from app.api.dependencies import get_current_support_user

from app.models.user import User
from app.models.ticket import Ticket

from app.schemas.copilot import (
    AIAssistantRequest,
    CopilotInsightsRequest,
    CopilotRequest,
)

from app.agents.copilot import SupportCopilot

from app.agents.tools import (
    generate_draft_response,
    generate_executive_summary,
    get_customer_360,
    get_ticket_summary,
    recommend_next_action,
)

router = APIRouter(prefix="/copilot", tags=["copilot"])


@router.post("")
def copilot(
    request: CopilotRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_support_user),
):

    response = SupportCopilot.handle(
        db, request.customer_id, request.ticket_id, request.question
    )

    return {"response": response}


@router.post("/insights")
def get_copilot_insights(
    request: CopilotInsightsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_support_user),
):
    ticket = (
        db.query(Ticket)
        .filter(Ticket.ticket_number == request.ticket_number.strip().upper())
        .first()
    )

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    ticket_id = ticket.id
    ticket_summary = get_ticket_summary(db, ticket_id)

    executive_summary = generate_executive_summary(db, ticket_id)

    next_action = recommend_next_action(db, ticket_id)

    draft_response = generate_draft_response(db, ticket_id)

    ticket = ticket_summary["ticket"]

    customer_360 = get_customer_360(db, ticket.user_id)

    return {
        "ticket_summary": ticket_summary,
        "executive_summary": executive_summary,
        "customer_360": customer_360,
        "next_action": next_action,
        "draft_response": draft_response,
    }


@router.post("/assistant")
def ai_assistant(
    request: AIAssistantRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_support_user),
):

    response = SupportCopilot.assistant(db, request)

    return response

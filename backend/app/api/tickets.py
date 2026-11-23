from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.database.db import get_db

from app.models.ticket import Ticket
from app.models.user import User
from app.models.ticket_message import TicketMessage
from app.models.ticket_status_history import TicketStatusHistory

from app.schemas.ticket import TicketCreate, TicketStatusUpdate, TicketMessageCreate

from app.api.dependencies import get_current_user
from app.api.dependencies import get_current_support_user
from app.agents.tools import get_customer_tickets

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("/")
def create_ticket(
    request: TicketCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == "support":
        if request.customer_id is None:
            raise HTTPException(
                status_code=422,
                detail="A customer must be selected when support creates a ticket",
            )
        customer = (
            db.query(User)
            .filter(User.id == request.customer_id, User.role == "customer")
            .first()
        )
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        ticket_owner_id = customer.id
    else:
        if request.customer_id is not None:
            raise HTTPException(
                status_code=403,
                detail="Customers can only create tickets for themselves",
            )
        ticket_owner_id = current_user.id

    ticket = Ticket(
        user_id=ticket_owner_id,
        subject=request.subject,
        description=request.description,
        status="OPEN",
        priority=request.priority,
    )

    db.add(ticket)
    db.flush()
    ticket.ticket_number = f"TKT-{ticket.id:03d}"
    db.commit()
    db.refresh(ticket)

    return ticket


@router.get("/my")
def get_my_tickets(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    return db.query(Ticket).filter(Ticket.user_id == current_user.id).all()


@router.get("/")
def get_all_tickets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_support_user),
):
    return db.query(Ticket).all()


@router.put("/{ticket_id}/status")
def update_ticket_status(
    ticket_id: int,
    request: TicketStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_support_user),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    history = TicketStatusHistory(
        ticket_id=ticket.id,
        changed_by_user_id=current_user.id,
        old_status=ticket.status,
        new_status=request.status,
    )

    db.add(history)
    ticket.status = request.status

    db.commit()
    db.refresh(ticket)

    return ticket


@router.post("/{ticket_id}/messages")
def add_message(
    ticket_id: int,
    request: TicketMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if current_user.role != "support" and ticket.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    message = TicketMessage(
        ticket_id=ticket_id, user_id=current_user.id, message=request.message
    )

    db.add(message)
    db.commit()
    db.refresh(message)

    return message


@router.get("/{ticket_id}/messages")
def get_messages(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if current_user.role != "support" and ticket.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    messages = (
        db.query(TicketMessage).filter(TicketMessage.ticket_id == ticket_id).all()
    )

    return [
        {
            "id": message.id,
            "username": message.user.username,
            "role": message.user.role,
            "message": message.message,
            "created_at": message.created_at,
        }
        for message in messages
    ]


@router.get("/{ticket_id}/history")
def get_ticket_history(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if current_user.role != "support" and ticket.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return (
        db.query(TicketStatusHistory)
        .filter(TicketStatusHistory.ticket_id == ticket_id)
        .all()
    )


@router.get("/customer/{customer_id}")
def get_customer_ticket_dashboard(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_support_user),
):

    tickets = get_customer_tickets(db, customer_id)

    return [
        {
            "ticket_number": ticket.ticket_number,
            "subject": ticket.subject,
            "status": ticket.status,
            "description": ticket.description,
            "priority": ("HIGH" if ticket.status == "OPEN" else "LOW"),
        }
        for ticket in tickets
    ]

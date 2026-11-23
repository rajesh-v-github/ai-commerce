from collections import Counter
from datetime import datetime, time, timedelta, timezone

from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_support_user, get_current_user
from app.database.db import get_db
from app.models.order import Order
from app.models.ticket import Ticket
from app.models.ticket_message import TicketMessage
from app.models.ticket_status_history import TicketStatusHistory
from app.models.user import User

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/customer")
def customer_dashboard(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    total_orders = db.query(Order).filter(Order.customer_id == current_user.id).count()

    open_tickets = (
        db.query(Ticket)
        .filter(
            Ticket.user_id == current_user.id,
            Ticket.status.in_(["OPEN", "IN_PROGRESS"]),
        )
        .count()
    )

    resolved_tickets = (
        db.query(Ticket)
        .filter(Ticket.user_id == current_user.id, Ticket.status == "RESOLVED")
        .count()
    )

    return {
        "username": current_user.username,
        "orders": total_orders,
        "open_tickets": open_tickets,
        "resolved_tickets": resolved_tickets,
    }


@router.get("/support")
def support_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_support_user),
):
    total_orders = db.query(Order).count()

    total_tickets = db.query(Ticket).count()

    open_tickets = db.query(Ticket).filter(Ticket.status == "OPEN").count()

    in_progress_tickets = (
        db.query(Ticket).filter(Ticket.status == "IN_PROGRESS").count()
    )

    resolved_tickets = db.query(Ticket).filter(Ticket.status == "RESOLVED").count()

    recent_tickets = db.query(Ticket).order_by(Ticket.id.desc()).limit(5).all()

    return {
        "metrics": {
            "total_orders": total_orders,
            "total_tickets": total_tickets,
            "open_tickets": open_tickets,
            "in_progress_tickets": in_progress_tickets,
            "resolved_tickets": resolved_tickets,
        },
        "recent_tickets": recent_tickets,
    }


@router.get("/overview")
def get_dashboard_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_support_user),
):
    tickets = db.query(Ticket).order_by(Ticket.id.desc()).all()
    orders = db.query(Order).order_by(Order.id.desc()).all()
    tickets_by_id = {ticket.id: ticket for ticket in tickets}
    ticket_status_counts = Counter(
        (ticket.status or "UNKNOWN").upper() for ticket in tickets
    )
    order_status_counts = Counter(
        (order.status or "UNKNOWN").upper() for order in orders
    )

    message_activity = (
        db.query(TicketMessage.ticket_id, func.max(TicketMessage.created_at))
        .group_by(TicketMessage.ticket_id)
        .all()
    )
    status_activity = (
        db.query(
            TicketStatusHistory.ticket_id,
            func.max(TicketStatusHistory.changed_at),
        )
        .group_by(TicketStatusHistory.ticket_id)
        .all()
    )
    latest_activity_by_ticket = {}
    for ticket_id, occurred_at in message_activity + status_activity:
        if occurred_at is None:
            continue
        latest_activity_by_ticket[ticket_id] = max(
            latest_activity_by_ticket.get(ticket_id, occurred_at), occurred_at
        )

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    today = now.date()
    current_period_start = datetime.combine(today - timedelta(days=6), time.min)
    previous_period_start = current_period_start - timedelta(days=7)
    messages_for_trend = (
        db.query(TicketMessage.created_at)
        .filter(TicketMessage.created_at >= previous_period_start)
        .all()
    )
    history_for_trend = (
        db.query(TicketStatusHistory.changed_at)
        .filter(TicketStatusHistory.changed_at >= previous_period_start)
        .all()
    )
    activity_dates = [
        occurred_at.date()
        for (occurred_at,) in messages_for_trend + history_for_trend
        if occurred_at is not None
    ]
    daily_counts = Counter(
        occurred_on.isoformat()
        for occurred_on in activity_dates
        if current_period_start.date() <= occurred_on <= today
    )
    current_activity = sum(
        count
        for occurred_on, count in daily_counts.items()
        if occurred_on >= current_period_start.date().isoformat()
    )
    previous_activity = sum(
        1
        for occurred_on in activity_dates
        if previous_period_start.date() <= occurred_on < current_period_start.date()
    )
    change_percent = (
        round((current_activity - previous_activity) / previous_activity * 100)
        if previous_activity
        else None
    )
    daily_activity = [
        {
            "date": (today - timedelta(days=day_offset)).isoformat(),
            "count": daily_counts.get(
                (today - timedelta(days=day_offset)).isoformat(), 0
            ),
        }
        for day_offset in range(6, -1, -1)
    ]

    active_tickets = [
        ticket
        for ticket in tickets
        if (ticket.status or "").upper() in {"OPEN", "IN_PROGRESS"}
    ]
    priority_rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    active_tickets.sort(
        key=lambda ticket: (
            priority_rank.get((ticket.priority or "MEDIUM").upper(), 2),
            latest_activity_by_ticket.get(ticket.id, datetime.min),
        )
    )
    attention_tickets = []
    for ticket in active_tickets[:8]:
        last_activity = latest_activity_by_ticket.get(ticket.id)
        attention_tickets.append(
            {
                "id": ticket.id,
                "ticket_number": ticket.ticket_number,
                "subject": ticket.subject,
                "status": ticket.status,
                "priority": ticket.priority or "MEDIUM",
                "last_activity_at": last_activity.isoformat() if last_activity else None,
                "days_since_activity": (
                    max((now.date() - last_activity.date()).days, 0)
                    if last_activity
                    else None
                ),
            }
        )

    recent_activity = []
    recent_messages = (
        db.query(TicketMessage)
        .filter(TicketMessage.created_at.isnot(None))
        .order_by(TicketMessage.created_at.desc(), TicketMessage.id.desc())
        .limit(12)
        .all()
    )
    for message in recent_messages:
        ticket = tickets_by_id.get(message.ticket_id)
        if ticket:
            recent_activity.append(
                {
                    "type": "message",
                    "ticket_number": ticket.ticket_number,
                    "subject": ticket.subject,
                    "status": ticket.status,
                    "description": message.message,
                    "occurred_at": message.created_at.isoformat(),
                }
            )

    recent_history = (
        db.query(TicketStatusHistory)
        .filter(TicketStatusHistory.changed_at.isnot(None))
        .order_by(TicketStatusHistory.changed_at.desc(), TicketStatusHistory.id.desc())
        .limit(12)
        .all()
    )
    for history in recent_history:
        ticket = tickets_by_id.get(history.ticket_id)
        if ticket:
            recent_activity.append(
                {
                    "type": "status",
                    "ticket_number": ticket.ticket_number,
                    "subject": ticket.subject,
                    "status": history.new_status,
                    "description": f"{history.old_status} → {history.new_status}",
                    "occurred_at": history.changed_at.isoformat(),
                }
            )
    recent_activity.sort(key=lambda activity: activity["occurred_at"], reverse=True)

    return {
        "total_orders": len(orders),
        "total_tickets": len(tickets),
        "ticket_status_counts": {
            status: ticket_status_counts.get(status, 0)
            for status in ("OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED")
        },
        "order_status_counts": dict(sorted(order_status_counts.items())),
        "attention_tickets": attention_tickets,
        "recent_activity": recent_activity[:12],
        "recent_orders": [
            {
                "id": order.id,
                "order_number": order.order_number,
                "customer_name": order.customer_name,
                "status": order.status,
                "total_amount": float(order.total_amount or 0),
            }
            for order in orders[:6]
        ],
        "ticket_activity_trend": {
            "current_period_count": current_activity,
            "previous_period_count": previous_activity,
            "change_percent": change_percent,
            "daily": daily_activity,
        },
    }

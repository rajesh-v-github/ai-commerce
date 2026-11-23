from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models.user import User
from app.schemas.customer import CustomerSearchRequest
from app.api.dependencies import get_current_support_user
from app.models.order import Order
from app.models.ticket import Ticket

router = APIRouter(prefix="/customer", tags=["Customer"])


@router.post("/search")
def search_customer(request: CustomerSearchRequest, db: Session = Depends(get_db)):

    customer = db.query(User).filter(User.username.ilike(f"%{request.search}%")).first()

    if not customer:
        return {"error": "Customer not found"}

    return {
        "customer_id": customer.id,
        "username": customer.username,
        "role": customer.role,
    }


@router.get("/")
def get_all_customers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_support_user),
):

    customers = db.query(User).filter(User.role == "customer").all()

    results = []

    for customer in customers:

        order_count = db.query(Order).filter(Order.customer_id == customer.id).count()

        ticket_count = db.query(Ticket).filter(Ticket.user_id == customer.id).count()

        open_ticket_count = (
            db.query(Ticket)
            .filter(
                Ticket.user_id == customer.id,
                Ticket.status.in_(["OPEN", "IN_PROGRESS"]),
            )
            .count()
        )

        results.append(
            {
                "customer_id": customer.id,
                "username": customer.username,
                "role": customer.role,
                "total_orders": order_count,
                "total_tickets": ticket_count,
                "open_tickets": open_ticket_count,
            }
        )

    return results

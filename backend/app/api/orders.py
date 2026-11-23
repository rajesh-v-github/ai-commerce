from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException

from sqlalchemy.orm import Session
from app.database.db import get_db
from app.schemas.order import CheckoutRequest
from app.schemas.order import OrderDetailsResponse
from app.services.order_service import OrderService

from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.order import Order
from app.models.product import Product
from app.agents.tools import get_customer_orders
from app.api.dependencies import get_current_support_user
from app.models.user import User

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("/customer/{customer_id}")
def get_customer_orders_api(
    customer_id: int,
    db: Session = Depends(get_db),
):
    orders = get_customer_orders(db, customer_id)

    return [
        {
            "id": order.id,
            "order_number": order.order_number,
            "status": order.status,
            "total_amount": order.total_amount,
        }
        for order in orders
    ]


@router.post("/checkout")
def checkout(
    request: CheckoutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    return OrderService.create_order(db, request, current_user)


@router.get("/my")
def get_my_orders(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    return db.query(Order).filter(Order.customer_id == current_user.id).all()


@router.get("/")
def get_all_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_support_user),
):
    orders = db.query(Order).order_by(Order.id.desc()).all()

    return [
        {
            "id": order.id,
            "order_number": order.order_number,
            "customer_name": order.customer_name,
            "customer_id": order.customer_id,
            "status": order.status,
            "total_amount": order.total_amount,
        }
        for order in orders
    ]


@router.get("/customer/username/{username}")
def get_customer_orders_by_username(
    username: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_support_user),
):

    customer = db.query(User).filter(User.username == username).first()

    if not customer:
        return []

    orders = db.query(Order).filter(Order.customer_id == customer.id).all()

    return [
        {
            "id": order.id,
            "order_number": order.order_number,
            "status": order.status,
            "total_amount": order.total_amount,
            "customer_name": order.customer_name,
        }
        for order in orders
    ]


@router.get(
    "/number/{order_number}",
    response_model=OrderDetailsResponse,
)
def get_order_details(
    order_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_support_user),
):
    order = db.query(Order).filter(Order.order_number == order_number).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    product_ids = {
        item.product_id for item in order.items if item.product_id is not None
    }
    products_by_id = (
        {
            product.id: product
            for product in db.query(Product).filter(Product.id.in_(product_ids)).all()
        }
        if product_ids
        else {}
    )

    return {
        "id": order.id,
        "order_number": order.order_number,
        "customer_name": order.customer_name,
        "customer_id": order.customer_id,
        "status": order.status,
        "total_amount": float(order.total_amount or 0),
        "items": [
            {
                "product_id": item.product_id,
                "product_name": item.product_name,
                "quantity": item.quantity,
                "unit_price": float(item.unit_price or 0),
                "line_total": float((item.unit_price or 0) * (item.quantity or 0)),
                "product": (
                    {
                        "id": products_by_id[item.product_id].id,
                        "name": products_by_id[item.product_id].name,
                        "description": products_by_id[item.product_id].description,
                        "category": products_by_id[item.product_id].category,
                        "current_price": (
                            float(products_by_id[item.product_id].price)
                            if products_by_id[item.product_id].price is not None
                            else None
                        ),
                        "stock": products_by_id[item.product_id].stock,
                    }
                    if item.product_id in products_by_id
                    else None
                ),
            }
            for item in order.items
        ],
    }

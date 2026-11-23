from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.orders import get_order_details
from app.database.db import Base
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.user import User


@pytest.fixture
def order_database():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        yield db
    engine.dispose()


def test_order_details_include_customer_status_amount_and_items(order_database):
    customer = User(
        username="customer",
        password_hash="hash",
        role="customer",
    )
    order_database.add(customer)
    order_database.flush()
    product = Product(
        id=5,
        name="Notebook",
        description="A hardcover, ruled notebook.",
        category="Stationery",
        stock=8,
        price=Decimal("15.00"),
    )
    order_database.add(product)
    order_database.flush()
    order = Order(
        order_number="ORD-001",
        customer_id=customer.id,
        customer_name=customer.username,
        status="PROCESSING",
        total_amount=Decimal("25.00"),
        idempotency_key="order-001",
        items=[
            OrderItem(
                product_id=5,
                product_name="Notebook",
                quantity=2,
                unit_price=Decimal("12.50"),
            )
        ],
    )
    order_database.add(order)
    order_database.commit()

    details = get_order_details(
        "ORD-001", order_database, SimpleNamespace(role="support")
    )

    assert details == {
        "id": order.id,
        "order_number": "ORD-001",
        "customer_name": "customer",
        "customer_id": customer.id,
        "status": "PROCESSING",
        "total_amount": 25.0,
        "items": [
            {
                "product_id": 5,
                "product_name": "Notebook",
                "quantity": 2,
                "unit_price": 12.5,
                "line_total": 25.0,
                "product": {
                    "id": 5,
                    "name": "Notebook",
                    "description": "A hardcover, ruled notebook.",
                    "category": "Stationery",
                    "current_price": 15.0,
                    "stock": 8,
                },
            }
        ],
    }


def test_order_details_returns_not_found_for_unknown_number(order_database):
    with pytest.raises(HTTPException) as error:
        get_order_details(
            "ORD-MISSING", order_database, SimpleNamespace(role="support")
        )

    assert error.value.status_code == 404

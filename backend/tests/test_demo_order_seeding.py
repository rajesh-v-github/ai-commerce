import random
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.db import Base
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.user import User
from seed_orders_and_tickets import populate_missing_demo_order_items


@pytest.fixture
def seed_database():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        yield db
    engine.dispose()


def test_backfills_only_missing_seeded_orders_and_recalculates_totals(seed_database):
    customer = User(
        username="customer",
        password_hash="hash",
        role="customer",
    )
    seed_database.add(customer)
    seed_database.flush()
    seed_database.add_all(
        [
            Product(
                id=1,
                name="Keyboard",
                description="Mechanical keyboard",
                category="Accessories",
                stock=10,
                price=Decimal("25.00"),
            ),
            Product(
                id=2,
                name="Mouse",
                description="Wireless mouse",
                category="Accessories",
                stock=12,
                price=Decimal("10.00"),
            ),
        ]
    )
    seeded_order = Order(
        order_number="ORD-001",
        customer_id=customer.id,
        customer_name=customer.username,
        status="PROCESSING",
        total_amount=Decimal("999.00"),
        idempotency_key="seed-demo-order-001",
    )
    regular_order = Order(
        order_number="ORD-REAL",
        customer_id=customer.id,
        customer_name=customer.username,
        status="PROCESSING",
        total_amount=Decimal("50.00"),
        idempotency_key="checkout-key",
    )
    seed_database.add_all([seeded_order, regular_order])
    seed_database.commit()

    updated_count = populate_missing_demo_order_items(
        seed_database, random.Random(7)
    )
    seed_database.commit()

    assert updated_count == 1
    assert seeded_order.items
    assert all(item.product_id in {1, 2} for item in seeded_order.items)
    assert seeded_order.total_amount == sum(
        (
            Decimal(str(item.unit_price)) * item.quantity
            for item in seeded_order.items
        ),
        Decimal("0.00"),
    )
    assert regular_order.items == []
    assert regular_order.total_amount == Decimal("50.00")

    assert populate_missing_demo_order_items(seed_database, random.Random(7)) == 0
    assert seed_database.query(OrderItem).count() == len(seeded_order.items)


def test_backfill_requires_a_product_catalog(seed_database):
    customer = User(
        username="customer",
        password_hash="hash",
        role="customer",
    )
    seed_database.add(customer)
    seed_database.flush()
    seed_database.add(
        Order(
            order_number="ORD-001",
            customer_id=customer.id,
            customer_name=customer.username,
            status="PROCESSING",
            total_amount=Decimal("999.00"),
            idempotency_key="seed-demo-order-001",
        )
    )
    seed_database.commit()

    with pytest.raises(RuntimeError, match="product catalog is empty"):
        populate_missing_demo_order_items(seed_database, random.Random(7))

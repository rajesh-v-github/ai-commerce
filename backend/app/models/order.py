from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database.db import Base
from app.models.order_status_history import OrderStatusHistory  # noqa: F401
from app.models.user import User  # noqa: F401


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    order_number = Column(String, unique=True)
    customer_id = Column(Integer, ForeignKey("users.id"))
    customer = relationship("User")
    customer_name = Column(String)
    status = Column(String)
    total_amount = Column(Numeric(10, 2))
    idempotency_key = Column(String, unique=True, nullable=False)

    subtotal_amount = Column(Numeric(10, 2), nullable=True)
    shipping_amount = Column(Numeric(10, 2), nullable=True, default=0)
    tax_amount = Column(Numeric(10, 2), nullable=True, default=0)
    payment_method = Column(String, nullable=True)
    payment_status = Column(String, nullable=True, default="PAID")
    payment_reference = Column(String, nullable=True)
    shipping_full_name = Column(String, nullable=True)
    shipping_email = Column(String, nullable=True)
    shipping_phone = Column(String, nullable=True)
    shipping_address = Column(Text, nullable=True)
    billing_address = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=True, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=True,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    items = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
    )
    status_history = relationship(
        "OrderStatusHistory",
        back_populates="order",
        order_by="OrderStatusHistory.id.asc()",
        cascade="all, delete-orphan",
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_id = Column(Integer)
    product_name = Column(String)
    quantity = Column(Integer)
    unit_price = Column(Numeric(10, 2))

    order = relationship("Order", back_populates="items")

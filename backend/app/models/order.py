from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy import Numeric

from sqlalchemy.orm import relationship

from app.database.db import Base


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    order_number = Column(String, unique=True)
    customer_id = Column(
    Integer,
    ForeignKey("users.id")
)
    customer = relationship("User")
    customer_name = Column(String)
    status = Column(String)
    total_amount = Column(Numeric(10, 2))
    idempotency_key = Column(
        String,
        unique=True,
        nullable=False
    )
    items = relationship(
        "OrderItem",
        back_populates="order"
    )


class OrderItem(Base):

    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True)

    order_id = Column(
        Integer,
        ForeignKey("orders.id")
    )

    product_id = Column(Integer)

    product_name = Column(String)

    quantity = Column(Integer)

    unit_price = Column(Numeric(10, 2))

    order = relationship(
        "Order",
        back_populates="items"
    )
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    Numeric,
    String,
    Text,
    text,
    true,
)

from app.database.db import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    description = Column(String)
    category = Column(String)
    stock = Column(Integer)
    price = Column(Numeric(10, 2))

    brand = Column(String, nullable=True)
    sku = Column(String, nullable=True, unique=True)
    image_url = Column(String, nullable=True)
    low_stock_threshold = Column(
        Integer,
        nullable=False,
        default=10,
        server_default=text("10"),
    )
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
    )
    specifications = Column(Text, nullable=True)
    target_audience = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=True, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=True,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

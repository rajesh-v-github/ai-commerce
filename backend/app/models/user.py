from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, true

from app.database.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    password_hash = Column(String)
    role = Column(String)

    full_name = Column(String, nullable=True)
    email = Column(String, nullable=True, index=True)
    phone = Column(String, nullable=True)
    shipping_address = Column(Text, nullable=True)
    billing_address = Column(Text, nullable=True)
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
    )
    created_at = Column(DateTime, nullable=True, default=datetime.utcnow)

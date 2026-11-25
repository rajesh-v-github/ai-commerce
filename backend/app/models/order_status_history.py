from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database.db import Base
from app.models.user import User  # noqa: F401


class OrderStatusHistory(Base):
    __tablename__ = "order_status_history"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    changed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    old_status = Column(String, nullable=True)
    new_status = Column(String, nullable=False)
    note = Column(String, nullable=True)
    changed_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    order = relationship("Order", back_populates="status_history")
    changed_by = relationship("User")

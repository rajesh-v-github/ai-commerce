from app.database.db import Base, engine
from app.database.migrations import ensure_ticket_number_column

from app.models.user import User
from app.models.product import Product
from app.models.order import Order
from app.models.order import OrderItem
from app.models.ticket import Ticket
from app.models.ticket_message import TicketMessage
from app.models.ticket_status_history import TicketStatusHistory

Base.metadata.create_all(bind=engine)
ensure_ticket_number_column(engine)

print("Database initialized successfully.")

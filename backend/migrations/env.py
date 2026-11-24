from logging.config import fileConfig

from alembic import context

from app.database.db import Base, engine
from app.models.cart_item import CartItem
from app.models.order import Order, OrderItem
from app.models.order_status_history import OrderStatusHistory
from app.models.product import Product
from app.models.ticket import Ticket
from app.models.ticket_message import TicketMessage
from app.models.ticket_status_history import TicketStatusHistory
from app.models.user import User

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = engine.url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            render_as_batch=connection.dialect.name == "sqlite",
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

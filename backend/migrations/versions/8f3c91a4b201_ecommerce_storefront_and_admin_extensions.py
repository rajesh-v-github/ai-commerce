"""ecommerce storefront and admin extensions

Revision ID: 8f3c91a4b201
Revises: 2046a0fd4f04
Create Date: 2026-11-24 07:15:00.000000

"""
from datetime import datetime, timedelta
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.utils.product_catalog_defaults import resolve_product_defaults


# revision identifiers, used by Alembic.
revision: str = "8f3c91a4b201"
down_revision: Union[str, None] = "2046a0fd4f04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Extend users table non-destructively
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("full_name", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("email", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("phone", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("shipping_address", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("billing_address", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            )
        )
        batch_op.add_column(sa.Column("created_at", sa.DateTime(), nullable=True))
        batch_op.create_index("ix_users_email", ["email"], unique=False)

    # 2. Extend products table non-destructively
    with op.batch_alter_table("products") as batch_op:
        batch_op.add_column(sa.Column("brand", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("sku", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("image_url", sa.String(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "low_stock_threshold",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("10"),
            )
        )
        batch_op.add_column(
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            )
        )
        batch_op.add_column(sa.Column("specifications", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("target_audience", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("created_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(), nullable=True))
        batch_op.create_unique_constraint("uq_products_sku", ["sku"])

    # 3. Extend orders table non-destructively
    with op.batch_alter_table("orders") as batch_op:
        batch_op.add_column(
            sa.Column("subtotal_amount", sa.Numeric(10, 2), nullable=True)
        )
        batch_op.add_column(
            sa.Column("shipping_amount", sa.Numeric(10, 2), nullable=True)
        )
        batch_op.add_column(
            sa.Column("tax_amount", sa.Numeric(10, 2), nullable=True)
        )
        batch_op.add_column(sa.Column("payment_method", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("payment_status", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("payment_reference", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("shipping_full_name", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("shipping_email", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("shipping_phone", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("shipping_address", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("billing_address", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("notes", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("created_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(), nullable=True))
        batch_op.create_index("ix_orders_created_at", ["created_at"], unique=False)
        batch_op.create_index("ix_orders_status", ["status"], unique=False)

    # 4. Create order_status_history table
    op.create_table(
        "order_status_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("changed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("old_status", sa.String(), nullable=True),
        sa.Column("new_status", sa.String(), nullable=False),
        sa.Column("note", sa.String(), nullable=True),
        sa.Column("changed_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["changed_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_order_status_history_order_id",
        "order_status_history",
        ["order_id"],
        unique=False,
    )

    # 5. Create cart_items table
    op.create_table(
        "cart_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "product_id", name="uq_cart_items_user_product"),
    )
    op.create_index("ix_cart_items_user_id", "cart_items", ["user_id"], unique=False)

    # 6. Non-destructive data enrichment for existing PostgreSQL / SQLite records
    #    Skip during offline --sql generation mode.
    if op.get_context().as_sql:
        return

    connection = op.get_bind()
    now = datetime(2026, 11, 24, 6, 0, 0)

    products_table = sa.table(
        "products",
        sa.column("id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("category", sa.String),
        sa.column("brand", sa.String),
        sa.column("sku", sa.String),
        sa.column("image_url", sa.String),
        sa.column("low_stock_threshold", sa.Integer),
        sa.column("specifications", sa.Text),
        sa.column("target_audience", sa.String),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )

    existing_products = connection.execute(
        sa.select(
            products_table.c.id,
            products_table.c.name,
            products_table.c.category,
            products_table.c.brand,
            products_table.c.sku,
            products_table.c.image_url,
            products_table.c.specifications,
            products_table.c.target_audience,
            products_table.c.created_at,
        ).order_by(products_table.c.id)
    ).fetchall()

    used_skus = {
        row.sku for row in existing_products if row.sku and row.sku.strip()
    }

    for row in existing_products:
        defaults = resolve_product_defaults(row.name, row.category, row.id)
        candidate_sku = row.sku
        if not candidate_sku:
            proposed = defaults.get("sku")
            if proposed and proposed not in used_skus:
                candidate_sku = proposed
                used_skus.add(proposed)
            else:
                fallback_sku = f"SG-PRD-{row.id:04d}"
                candidate_sku = fallback_sku
                used_skus.add(fallback_sku)

        updates = {
            "brand": row.brand or defaults.get("brand"),
            "sku": candidate_sku,
            "image_url": (
                row.image_url
                if row.image_url and row.image_url.strip()
                else defaults.get("image_url")
            ),
            "low_stock_threshold": defaults.get("low_stock_threshold", 10),
            "specifications": row.specifications or defaults.get("specifications"),
            "target_audience": row.target_audience or defaults.get("target_audience"),
            "created_at": row.created_at or now,
            "updated_at": now,
        }
        connection.execute(
            products_table.update()
            .where(products_table.c.id == row.id)
            .values(**updates)
        )

    users_table = sa.table(
        "users",
        sa.column("id", sa.Integer),
        sa.column("username", sa.String),
        sa.column("role", sa.String),
        sa.column("full_name", sa.String),
        sa.column("email", sa.String),
        sa.column("created_at", sa.DateTime),
    )
    existing_users = connection.execute(
        sa.select(
            users_table.c.id,
            users_table.c.username,
            users_table.c.role,
            users_table.c.full_name,
            users_table.c.email,
            users_table.c.created_at,
        )
    ).fetchall()
    for urow in existing_users:
        default_name = urow.full_name
        if not default_name and urow.username:
            if urow.role == "support":
                default_name = f"Support Executive ({urow.username})"
            else:
                default_name = urow.username.replace("_", " ").title()
        default_email = urow.email or (
            f"{urow.username}@example.com" if urow.username else None
        )
        connection.execute(
            users_table.update()
            .where(users_table.c.id == urow.id)
            .values(
                full_name=default_name,
                email=default_email,
                created_at=urow.created_at or now - timedelta(days=30),
            )
        )

    orders_table = sa.table(
        "orders",
        sa.column("id", sa.Integer),
        sa.column("order_number", sa.String),
        sa.column("customer_name", sa.String),
        sa.column("status", sa.String),
        sa.column("total_amount", sa.Numeric(10, 2)),
        sa.column("subtotal_amount", sa.Numeric(10, 2)),
        sa.column("shipping_amount", sa.Numeric(10, 2)),
        sa.column("tax_amount", sa.Numeric(10, 2)),
        sa.column("payment_method", sa.String),
        sa.column("payment_status", sa.String),
        sa.column("payment_reference", sa.String),
        sa.column("shipping_full_name", sa.String),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )
    order_history_table = sa.table(
        "order_status_history",
        sa.column("order_id", sa.Integer),
        sa.column("old_status", sa.String),
        sa.column("new_status", sa.String),
        sa.column("note", sa.String),
        sa.column("changed_at", sa.DateTime),
    )

    existing_orders = connection.execute(
        sa.select(
            orders_table.c.id,
            orders_table.c.order_number,
            orders_table.c.customer_name,
            orders_table.c.status,
            orders_table.c.total_amount,
            orders_table.c.created_at,
        ).order_by(orders_table.c.id)
    ).fetchall()

    total_existing = max(len(existing_orders), 1)
    for idx, orow in enumerate(existing_orders):
        days_ago = int(((total_existing - 1 - idx) * 13) / total_existing)
        order_ts = orow.created_at or (
            now - timedelta(days=days_ago, hours=(idx * 3) % 12)
        )
        pay_status = "REFUNDED" if (orow.status or "").upper() == "CANCELLED" else "PAID"
        connection.execute(
            orders_table.update()
            .where(orders_table.c.id == orow.id)
            .values(
                subtotal_amount=orow.total_amount,
                shipping_amount=0,
                tax_amount=0,
                payment_method="MOCK_CARD",
                payment_status=pay_status,
                payment_reference=f"MOCK-MIG-{orow.id:04d}",
                shipping_full_name=orow.customer_name,
                created_at=order_ts,
                updated_at=order_ts,
            )
        )
        connection.execute(
            order_history_table.insert().values(
                order_id=orow.id,
                old_status=None,
                new_status=orow.status or "PROCESSING",
                note="Initial order record",
                changed_at=order_ts,
            )
        )


def downgrade() -> None:
    op.drop_index("ix_cart_items_user_id", table_name="cart_items")
    op.drop_table("cart_items")

    op.drop_index(
        "ix_order_status_history_order_id", table_name="order_status_history"
    )
    op.drop_table("order_status_history")

    with op.batch_alter_table("orders") as batch_op:
        batch_op.drop_index("ix_orders_status")
        batch_op.drop_index("ix_orders_created_at")
        batch_op.drop_column("updated_at")
        batch_op.drop_column("created_at")
        batch_op.drop_column("notes")
        batch_op.drop_column("billing_address")
        batch_op.drop_column("shipping_address")
        batch_op.drop_column("shipping_phone")
        batch_op.drop_column("shipping_email")
        batch_op.drop_column("shipping_full_name")
        batch_op.drop_column("payment_reference")
        batch_op.drop_column("payment_status")
        batch_op.drop_column("payment_method")
        batch_op.drop_column("tax_amount")
        batch_op.drop_column("shipping_amount")
        batch_op.drop_column("subtotal_amount")

    with op.batch_alter_table("products") as batch_op:
        batch_op.drop_constraint("uq_products_sku", type_="unique")
        batch_op.drop_column("updated_at")
        batch_op.drop_column("created_at")
        batch_op.drop_column("target_audience")
        batch_op.drop_column("specifications")
        batch_op.drop_column("is_active")
        batch_op.drop_column("low_stock_threshold")
        batch_op.drop_column("image_url")
        batch_op.drop_column("sku")
        batch_op.drop_column("brand")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_index("ix_users_email")
        batch_op.drop_column("created_at")
        batch_op.drop_column("is_active")
        batch_op.drop_column("billing_address")
        batch_op.drop_column("shipping_address")
        batch_op.drop_column("phone")
        batch_op.drop_column("email")
        batch_op.drop_column("full_name")

import uuid

from app.models.order import Order
from app.models.order import OrderItem

from app.models.product import Product


class OrderService:

    @staticmethod
    def create_order(
        db,
        request,
        current_user
    ):

        existing = (
            db.query(Order)
            .filter(
                Order.idempotency_key ==
                request.idempotency_key
            )
            .first()
        )

        if existing:
            return existing

        total = 0
        db_products = {}

        for item in request.items:

            product = (
                db.query(Product)
                .filter(
                    Product.id == item.product_id
                )
                .first()
            )

            if not product:
                raise ValueError("invalid product")

            if item.quantity <= 0:
                raise ValueError("invalid quantity")

            if product.stock < item.quantity:
                raise ValueError(
                    "insufficient stock"
                )

            db_products[item.product_id] = product

            total += (
                float(product.price)
                * item.quantity
            )

        order = Order()
        order.order_number = (
            f"ORD-{uuid.uuid4().hex[:8]}"
        )
        order.customer_name = (
            current_user.username
        )
        order.customer_id = (
            current_user.id
        )
        order.status = "PROCESSING"
        order.total_amount = total
        order.idempotency_key = (
            request.idempotency_key
        )
        db.add(order)
        db.flush()

        for item in request.items:
            product = db_products[
                item.product_id
            ]
            product.stock = (
                product.stock
                - item.quantity
            )
            db_item = OrderItem()
            db_item.order_id = order.id
            db_item.product_id = (
                product.id
            )
            db_item.product_name = (
                product.name
            )
            db_item.quantity = (
                item.quantity
            )
            db_item.unit_price = (
                product.price
            )
            db.add(db_item)

        db.commit()
        db.refresh(order)

        return order
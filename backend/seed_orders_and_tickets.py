import random
from decimal import Decimal

from app.database.db import SessionLocal, engine
from app.database.migrations import ensure_ticket_number_column
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.ticket import Ticket
from app.models.ticket_message import TicketMessage
from app.models.user import User

ORDER_COUNT = 30
CUSTOMER_USERNAMES = tuple(f"customer{number}" for number in range(1, 11))
ORDER_STATUSES = ("PROCESSING", "SHIPPED", "DELIVERED", "CANCELLED")
TICKET_STATUSES = ("OPEN", "IN_PROGRESS", "RESOLVED")

TICKET_SCENARIOS = (
    (
        "Order delayed",
        "My order has not arrived yet.",
        "Could you please check the delivery status?",
        "We are checking the delivery status and will update you.",
    ),
    (
        "Received damaged item",
        "The product arrived damaged.",
        "Please help me with the damaged item.",
        "Sorry about that. We will review the issue and help with next steps.",
    ),
    (
        "Refund request",
        "I would like to request a refund.",
        "Can you help me with the refund process?",
        "We will review your request and share an update.",
    ),
    (
        "Wrong product delivered",
        "I received a different product from the one I ordered.",
        "Please help me resolve this order issue.",
        "We are reviewing the order details and will assist you.",
    ),
    (
        "Payment issue",
        "I have a question about a payment for my order.",
        "Could you check the payment status?",
        "We will check the payment details and get back to you.",
    ),
    (
        "Address update request",
        "I need help updating my delivery address.",
        "Can you let me know whether the address can be changed?",
        "We will check whether the address can still be updated.",
    ),
    (
        "Delivery tracking issue",
        "The tracking information has not changed.",
        "Could you check the latest tracking update?",
        "We will review the tracking information and update you.",
    ),
    (
        "Return request",
        "I would like to return an item.",
        "Please tell me how to start a return.",
        "We will review the return request and share the next steps.",
    ),
    (
        "Discount not applied",
        "A discount was not applied to my order.",
        "Can you check whether the discount can be applied?",
        "We will review the order and discount details.",
    ),
    (
        "Package missing items",
        "An item is missing from my package.",
        "Please help me with the missing item.",
        "We will check the order contents and follow up with you.",
    ),
)


def get_seeded_order_count(db):
    legacy_order_keys = [f"seed-ORD-{1001 + number}" for number in range(10)]
    legacy_order_count = (
        db.query(Order)
        .filter(Order.idempotency_key.in_(legacy_order_keys))
        .count()
    )
    demo_order_count = (
        db.query(Order)
        .filter(Order.idempotency_key.like("seed-demo-order-%"))
        .count()
    )
    return legacy_order_count + demo_order_count


def populate_missing_demo_order_items(db, rng):
    demo_orders = (
        db.query(Order)
        .filter(Order.idempotency_key.like("seed-demo-order-%"))
        .all()
    )
    orders_without_items = [order for order in demo_orders if not order.items]
    if not orders_without_items:
        return 0

    products = (
        db.query(Product)
        .filter(Product.price.isnot(None))
        .order_by(Product.id)
        .all()
    )
    if not products:
        raise RuntimeError(
            "Cannot populate seeded order items because the product catalog is empty."
        )

    for order in orders_without_items:
        selected_products = rng.sample(
            products,
            k=min(len(products), rng.randint(1, 3)),
        )
        order_total = Decimal("0.00")
        for product in selected_products:
            quantity = rng.randint(1, 3)
            unit_price = Decimal(str(product.price))
            db.add(
                OrderItem(
                    order=order,
                    product_id=product.id,
                    product_name=product.name,
                    quantity=quantity,
                    unit_price=unit_price,
                )
            )
            order_total += unit_price * quantity
        order.total_amount = order_total

    print(
        f"Added product items to {len(orders_without_items)} seeded orders "
        "and recalculated their totals."
    )
    return len(orders_without_items)


def seed_orders(db, customers, rng):
    seeded_count = get_seeded_order_count(db)
    if seeded_count >= ORDER_COUNT:
        print(f"Found {seeded_count} seeded orders. Skipping order creation.")
        populate_missing_demo_order_items(db, rng)
        return 0

    orders_added = 0
    sequence = 1

    while seeded_count < ORDER_COUNT:
        idempotency_key = f"seed-demo-order-{sequence:03d}"
        order_number = f"ORD-{sequence:03d}"
        sequence += 1

        existing_key = (
            db.query(Order)
            .filter(Order.idempotency_key == idempotency_key)
            .first()
        )
        existing_number = (
            db.query(Order).filter(Order.order_number == order_number).first()
        )
        if existing_key or existing_number:
            continue

        customer = rng.choice(customers)
        db.add(
            Order(
                order_number=order_number,
                customer_name=customer.username,
                customer_id=customer.id,
                total_amount=Decimal("0.00"),
                status=rng.choice(ORDER_STATUSES),
                idempotency_key=idempotency_key,
            )
        )
        seeded_count += 1
        orders_added += 1

    populate_missing_demo_order_items(db, rng)
    print(f"Added {orders_added} orders; {ORDER_COUNT} seeded orders are present.")
    return orders_added


def seed_tickets(db, customers, support, rng):
    tickets_added = 0
    messages_added = 0
    scenario_subjects = tuple(scenario[0] for scenario in TICKET_SCENARIOS)

    for customer in customers:
        existing_demo_ticket = (
            db.query(Ticket)
            .filter(
                Ticket.user_id == customer.id,
                Ticket.subject.in_(scenario_subjects),
            )
            .first()
        )
        if existing_demo_ticket:
            continue

        scenario_count = rng.randint(1, 3)
        scenarios = rng.sample(TICKET_SCENARIOS, k=scenario_count)

        for subject, description, customer_message, support_message in scenarios:
            ticket = Ticket(
                user_id=customer.id,
                subject=subject,
                description=description,
                status=rng.choice(TICKET_STATUSES),
            )
            db.add(ticket)
            db.flush()
            ticket.ticket_number = f"TKT-{ticket.id:03d}"

            db.add_all(
                [
                    TicketMessage(
                        ticket_id=ticket.id,
                        user_id=customer.id,
                        message=customer_message,
                    ),
                    TicketMessage(
                        ticket_id=ticket.id,
                        user_id=support.id,
                        message=support_message,
                    ),
                ]
            )
            tickets_added += 1
            messages_added += 2

    print(f"Added {tickets_added} tickets and {messages_added} ticket messages.")
    return tickets_added


def seed_demo_data():
    ensure_ticket_number_column(engine)
    db = SessionLocal()
    rng = random.Random()

    try:
        users = (
            db.query(User)
            .filter(User.username.in_((*CUSTOMER_USERNAMES, "support1")))
            .all()
        )
        users_by_username = {user.username: user for user in users}
        missing_customers = [
            username
            for username in CUSTOMER_USERNAMES
            if username not in users_by_username
        ]
        support = users_by_username.get("support1")

        if missing_customers or not support:
            missing_users = missing_customers.copy()
            if not support:
                missing_users.append("support1")
            raise RuntimeError(
                "Required seed users were not found: " + ", ".join(missing_users)
            )

        customers = [users_by_username[name] for name in CUSTOMER_USERNAMES]
        invalid_customers = [
            customer.username
            for customer in customers
            if customer.role != "customer"
        ]
        if invalid_customers:
            raise RuntimeError(
                "These seed users are not customer accounts: "
                + ", ".join(invalid_customers)
            )
        if support.role != "support":
            raise RuntimeError("The support1 user is not a support account.")

        seed_orders(db, customers, rng)
        seed_tickets(db, customers, support, rng)
        db.commit()
        print("Demo data created successfully.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_data()

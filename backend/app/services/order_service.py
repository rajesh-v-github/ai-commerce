from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import re
import uuid
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models.cart_item import CartItem
from app.models.order import Order, OrderItem
from app.models.order_status_history import OrderStatusHistory
from app.models.product import Product
from app.models.user import User

FREE_SHIPPING_THRESHOLD = Decimal("1999.00")
STANDARD_SHIPPING_FEE = Decimal("99.00")
INCLUDED_GST_RATE = Decimal("0.18")

ALLOWED_ORDER_STATUSES = {
    "PROCESSING",
    "CONFIRMED",
    "SHIPPED",
    "DELIVERED",
    "CANCELLED",
}
ALLOWED_PAYMENT_METHODS = {
    "MOCK_CARD",
    "MOCK_UPI",
    "MOCK_COD",
}
ALLOWED_PAYMENT_STATUSES = {
    "PAID",
    "PENDING",
    "REFUNDED",
    "FAILED",
}


def _quantize_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _assign_serial_order_number(
    db: Session, order: Order, order_dt: datetime
) -> str:
    date_part = order_dt.strftime("%Y%m%d")
    max_serial = int(order.id or 1)
    rows = (
        db.query(Order.id, Order.order_number)
        .filter(Order.id != order.id)
        .all()
    )
    for existing_id, existing_num in rows:
        if existing_id is not None and int(existing_id) >= max_serial:
            max_serial = int(existing_id) + 1
        if existing_num:
            # Match either ORD-001..ORD-030 or ORD-YYYYMMDD-0031 serial suffixes
            m = re.match(r"^ORD-(?:\d{8}-)?(\d+)$", existing_num.strip())
            if m:
                parsed_serial = int(m.group(1))
                if parsed_serial >= max_serial:
                    max_serial = parsed_serial + 1

    serial = max(int(order.id or 1), max_serial)
    while True:
        candidate = f"ORD-{date_part}-{serial:04d}"
        conflict = (
            db.query(Order)
            .filter(Order.order_number == candidate, Order.id != order.id)
            .first()
        )
        if not conflict:
            order.order_number = candidate
            return candidate
        serial += 1


def _consolidate_items(items) -> list[tuple[int, int]]:
    if not items:
        raise HTTPException(status_code=422, detail="Order must include at least one item.")
    merged: dict[int, int] = {}
    for item in items:
        if item.quantity <= 0:
            raise HTTPException(status_code=422, detail="Item quantity must be greater than zero.")
        merged[item.product_id] = merged.get(item.product_id, 0) + int(item.quantity)
    return sorted(merged.items(), key=lambda pair: pair[0])


def _lock_and_decrement_stock(
    db: Session, consolidated_items: list[tuple[int, int]]
) -> dict[int, Product]:
    is_postgres = (
        db.bind is not None and getattr(db.bind.dialect, "name", "") == "postgresql"
    )
    products_by_id: dict[int, Product] = {}

    for product_id, quantity in consolidated_items:
        query = db.query(Product).filter(Product.id == product_id)
        if is_postgres:
            query = query.with_for_update()
        product = query.first()

        if not product or getattr(product, "is_active", True) is False:
            raise HTTPException(
                status_code=404,
                detail=f"Product ID {product_id} is unavailable.",
            )

        available_stock = int(product.stock or 0)
        if available_stock < quantity:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Insufficient stock for '{product.name}'. "
                    f"Requested {quantity}, available {available_stock}."
                ),
            )

        # Atomic conditional stock decrement safe under concurrency on both PostgreSQL & SQLite
        stmt = (
            update(Product)
            .where(
                Product.id == product_id,
                Product.stock >= quantity,
                Product.is_active.is_(True),
            )
            .values(
                stock=Product.stock - quantity,
                updated_at=datetime.utcnow(),
            )
        )
        result = db.execute(stmt)
        if result.rowcount != 1:
            raise HTTPException(
                status_code=409,
                detail=f"Stock changed concurrently for '{product.name}'. Please review your cart.",
            )
        db.refresh(product)
        products_by_id[product_id] = product

    return products_by_id


def _resolve_checkout_customer(
    db: Session,
    *,
    current_user: Optional[User],
    full_name: str,
    email: str,
    phone: str,
    shipping_address: str,
    billing_address: str,
) -> User:
    normalized_email = email.strip().lower()
    clean_name = full_name.strip()
    clean_phone = phone.strip()

    if current_user is not None:
        if not current_user.full_name and clean_name:
            current_user.full_name = clean_name
        if not current_user.phone and clean_phone:
            current_user.phone = clean_phone
        if not current_user.shipping_address and shipping_address:
            current_user.shipping_address = shipping_address
        if not current_user.billing_address and billing_address:
            current_user.billing_address = billing_address
        if not current_user.email and normalized_email:
            email_taken = (
                db.query(User)
                .filter(User.email.ilike(normalized_email), User.id != current_user.id)
                .first()
            )
            if not email_taken:
                current_user.email = normalized_email
        return current_user

    # Guest checkout: reuse existing guest customer record by email to prevent duplicates,
    # while protecting password-registered accounts from unauthenticated spoofing.
    existing_by_email = (
        db.query(User).filter(User.email.ilike(normalized_email)).first()
    )
    if existing_by_email:
        if existing_by_email.password_hash:
            raise HTTPException(
                status_code=409,
                detail=(
                    "An account already exists with this email address. "
                    "Please sign in to place your order under your account."
                ),
            )
        existing_by_email.full_name = clean_name or existing_by_email.full_name
        existing_by_email.phone = clean_phone or existing_by_email.phone
        existing_by_email.shipping_address = shipping_address
        existing_by_email.billing_address = billing_address
        return existing_by_email

    email_prefix = re.sub(r"[^a-z0-9_]", "", normalized_email.split("@")[0])[:18] or "guest"
    candidate_username = email_prefix
    suffix = 1
    while db.query(User).filter(User.username == candidate_username).first():
        candidate_username = f"{email_prefix}_{suffix}"
        suffix += 1

    guest_customer = User(
        username=candidate_username,
        password_hash=None,
        role="customer",
        full_name=clean_name,
        email=normalized_email,
        phone=clean_phone,
        shipping_address=shipping_address,
        billing_address=billing_address,
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db.add(guest_customer)
    db.flush()
    return guest_customer


class OrderService:
    @staticmethod
    def serialize_order_summary(order: Order) -> dict[str, Any]:
        return {
            "id": order.id,
            "order_number": order.order_number,
            "customer_id": order.customer_id,
            "customer_name": order.customer_name,
            "shipping_full_name": order.shipping_full_name or order.customer_name,
            "shipping_email": order.shipping_email,
            "status": order.status,
            "payment_method": order.payment_method or "MOCK_CARD",
            "payment_status": order.payment_status or "PAID",
            "payment_reference": order.payment_reference,
            "subtotal_amount": float(
                order.subtotal_amount
                if order.subtotal_amount is not None
                else (order.total_amount or 0)
            ),
            "shipping_amount": float(order.shipping_amount or 0),
            "tax_amount": float(order.tax_amount or 0),
            "total_amount": float(order.total_amount or 0),
            "item_count": sum(int(i.quantity or 0) for i in (order.items or [])),
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "updated_at": order.updated_at.isoformat() if order.updated_at else None,
        }

    @staticmethod
    def serialize_order_full(db: Session, order: Order) -> dict[str, Any]:
        product_ids = {
            item.product_id for item in (order.items or []) if item.product_id is not None
        }
        products_by_id = (
            {
                p.id: p
                for p in db.query(Product).filter(Product.id.in_(product_ids)).all()
            }
            if product_ids
            else {}
        )

        items_payload = []
        for item in order.items or []:
            prod = products_by_id.get(item.product_id)
            qty = int(item.quantity or 0)
            unit = float(item.unit_price or 0)
            items_payload.append(
                {
                    "id": item.id,
                    "product_id": item.product_id,
                    "product_name": item.product_name,
                    "quantity": qty,
                    "unit_price": unit,
                    "line_total": round(unit * qty, 2),
                    "image_url": prod.image_url if prod else None,
                    "category": prod.category if prod else None,
                    "sku": prod.sku if prod else None,
                }
            )

        history_payload = [
            {
                "id": h.id,
                "old_status": h.old_status,
                "new_status": h.new_status,
                "note": h.note,
                "changed_by": h.changed_by.username if h.changed_by else "system",
                "changed_at": h.changed_at.isoformat() if h.changed_at else None,
            }
            for h in (order.status_history or [])
        ]

        customer_info = None
        if order.customer:
            customer_info = {
                "id": order.customer.id,
                "username": order.customer.username,
                "full_name": order.customer.full_name,
                "email": order.customer.email,
                "phone": order.customer.phone,
            }

        return {
            **OrderService.serialize_order_summary(order),
            "shipping_phone": order.shipping_phone,
            "shipping_address": order.shipping_address,
            "billing_address": order.billing_address,
            "notes": order.notes,
            "customer": customer_info,
            "items": items_payload,
            "status_history": history_payload,
        }

    @staticmethod
    def create_order(db: Session, request, current_user: User) -> Order:
        """Backward-compatible checkout service for POST /api/orders/checkout with safe concurrency."""
        existing = (
            db.query(Order)
            .filter(Order.idempotency_key == request.idempotency_key)
            .first()
        )
        if existing:
            return existing

        try:
            consolidated = _consolidate_items(request.items)
            products_by_id = _lock_and_decrement_stock(db, consolidated)

            subtotal = Decimal("0.00")
            for product_id, quantity in consolidated:
                product = products_by_id[product_id]
                subtotal += Decimal(str(product.price)) * quantity
            subtotal = _quantize_money(subtotal)
            included_tax = _quantize_money(
                subtotal * INCLUDED_GST_RATE / (Decimal("1.00") + INCLUDED_GST_RATE)
            )

            now = datetime.utcnow()
            order = Order(
                order_number=f"ORD-PENDING-{uuid.uuid4().hex}",
                customer_name=current_user.username,
                customer_id=current_user.id,
                status="PROCESSING",
                subtotal_amount=subtotal,
                shipping_amount=Decimal("0.00"),
                tax_amount=included_tax,
                total_amount=subtotal,
                payment_method="MOCK_CARD",
                payment_status="PAID",
                payment_reference=f"MOCK-TXN-{uuid.uuid4().hex[:8].upper()}",
                shipping_full_name=current_user.full_name or current_user.username,
                shipping_email=current_user.email,
                shipping_phone=current_user.phone,
                shipping_address=current_user.shipping_address,
                billing_address=current_user.billing_address,
                idempotency_key=request.idempotency_key,
                created_at=now,
                updated_at=now,
            )
            db.add(order)
            db.flush()
            _assign_serial_order_number(db, order, now)

            for product_id, quantity in consolidated:
                product = products_by_id[product_id]
                db.add(
                    OrderItem(
                        order_id=order.id,
                        product_id=product.id,
                        product_name=product.name,
                        quantity=quantity,
                        unit_price=product.price,
                    )
                )

            db.add(
                OrderStatusHistory(
                    order_id=order.id,
                    changed_by_user_id=current_user.id,
                    old_status=None,
                    new_status="PROCESSING",
                    note="Order placed",
                    changed_at=now,
                )
            )
            db.commit()
            db.refresh(order)
            return order
        except HTTPException:
            db.rollback()
            raise
        except Exception as exc:
            db.rollback()
            raise HTTPException(
                status_code=400, detail=f"Unable to place order: {exc}"
            ) from exc

    @staticmethod
    def place_storefront_order(
        db: Session, payload, current_user: Optional[User] = None
    ) -> dict[str, Any]:
        """Full storefront POC checkout workflow with stock locking, customer deduplication, and mock payment."""
        existing = (
            db.query(Order)
            .filter(Order.idempotency_key == payload.idempotency_key)
            .first()
        )
        if existing:
            return OrderService.serialize_order_full(db, existing)

        payment_method = (payload.payment_method or "MOCK_CARD").strip().upper()
        if payment_method not in ALLOWED_PAYMENT_METHODS:
            raise HTTPException(
                status_code=422,
                detail=f"Unsupported POC payment method '{payment_method}'.",
            )

        shipping_addr_str = payload.format_shipping_address()
        billing_addr_str = payload.format_billing_address()

        try:
            consolidated = _consolidate_items(payload.items)
            products_by_id = _lock_and_decrement_stock(db, consolidated)

            customer = _resolve_checkout_customer(
                db,
                current_user=current_user,
                full_name=payload.customer_full_name,
                email=payload.customer_email,
                phone=payload.customer_phone,
                shipping_address=shipping_addr_str,
                billing_address=billing_addr_str,
            )

            subtotal = Decimal("0.00")
            for product_id, quantity in consolidated:
                product = products_by_id[product_id]
                subtotal += Decimal(str(product.price)) * quantity
            subtotal = _quantize_money(subtotal)

            shipping_fee = (
                Decimal("0.00")
                if subtotal >= FREE_SHIPPING_THRESHOLD
                else STANDARD_SHIPPING_FEE
            )
            included_gst = _quantize_money(
                subtotal * INCLUDED_GST_RATE / (Decimal("1.00") + INCLUDED_GST_RATE)
            )
            grand_total = _quantize_money(subtotal + shipping_fee)

            payment_status = "PENDING" if payment_method == "MOCK_COD" else "PAID"
            payment_ref = f"{payment_method.replace('_', '-')}-{uuid.uuid4().hex[:8].upper()}"
            now = datetime.utcnow()

            order = Order(
                order_number=f"ORD-PENDING-{uuid.uuid4().hex}",
                customer_id=customer.id,
                customer_name=customer.username,
                status="PROCESSING",
                subtotal_amount=subtotal,
                shipping_amount=shipping_fee,
                tax_amount=included_gst,
                total_amount=grand_total,
                payment_method=payment_method,
                payment_status=payment_status,
                payment_reference=payment_ref,
                shipping_full_name=payload.customer_full_name.strip(),
                shipping_email=payload.customer_email.strip().lower(),
                shipping_phone=payload.customer_phone.strip(),
                shipping_address=shipping_addr_str,
                billing_address=billing_addr_str,
                notes=(payload.notes or "").strip() or None,
                idempotency_key=payload.idempotency_key.strip(),
                created_at=now,
                updated_at=now,
            )
            db.add(order)
            db.flush()
            _assign_serial_order_number(db, order, now)

            for product_id, quantity in consolidated:
                product = products_by_id[product_id]
                db.add(
                    OrderItem(
                        order_id=order.id,
                        product_id=product.id,
                        product_name=product.name,
                        quantity=quantity,
                        unit_price=product.price,
                    )
                )

            db.add(
                OrderStatusHistory(
                    order_id=order.id,
                    changed_by_user_id=customer.id,
                    old_status=None,
                    new_status="PROCESSING",
                    note=f"Order submitted via storefront ({payment_method} - POC simulation)",
                    changed_at=now,
                )
            )

            # Clear server-saved cart for authenticated customer
            if current_user is not None:
                db.query(CartItem).filter(CartItem.user_id == current_user.id).delete()

            db.commit()
            db.refresh(order)
            return OrderService.serialize_order_full(db, order)
        except HTTPException:
            db.rollback()
            raise
        except Exception as exc:
            db.rollback()
            raise HTTPException(
                status_code=400,
                detail=f"Checkout failed: {exc}",
            ) from exc

    @staticmethod
    def update_order_status(
        db: Session,
        *,
        order_id: int,
        new_status: Optional[str],
        payment_status: Optional[str],
        note: Optional[str],
        changed_by: User,
    ) -> dict[str, Any]:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        now = datetime.utcnow()
        previous_status = (order.status or "PROCESSING").upper()

        try:
            if new_status is not None:
                normalized_status = new_status.strip().upper()
                if normalized_status not in ALLOWED_ORDER_STATUSES:
                    raise HTTPException(
                        status_code=422,
                        detail=f"Unsupported order status '{normalized_status}'.",
                    )

                if normalized_status != previous_status:
                    # Restore product stock if cancelling an active order
                    if normalized_status == "CANCELLED" and previous_status != "CANCELLED":
                        for item in order.items or []:
                            if item.product_id is not None and (item.quantity or 0) > 0:
                                prod = (
                                    db.query(Product)
                                    .filter(Product.id == item.product_id)
                                    .first()
                                )
                                if prod:
                                    prod.stock = int(prod.stock or 0) + int(item.quantity)
                                    prod.updated_at = now
                        if (order.payment_status or "").upper() == "PAID" and not payment_status:
                            order.payment_status = "REFUNDED"
                    elif previous_status == "CANCELLED" and normalized_status != "CANCELLED":
                        # Re-opening a cancelled order must re-validate and deduct stock safely
                        consolidated = [
                            (int(i.product_id), int(i.quantity))
                            for i in (order.items or [])
                            if i.product_id is not None and (i.quantity or 0) > 0
                        ]
                        if consolidated:
                            _lock_and_decrement_stock(
                                db, sorted(consolidated, key=lambda pair: pair[0])
                            )

                    order.status = normalized_status
                    db.add(
                        OrderStatusHistory(
                            order_id=order.id,
                            changed_by_user_id=changed_by.id,
                            old_status=previous_status,
                            new_status=normalized_status,
                            note=(note or "").strip() or f"Status updated to {normalized_status}",
                            changed_at=now,
                        )
                    )

            if payment_status is not None:
                normalized_pay = payment_status.strip().upper()
                if normalized_pay not in ALLOWED_PAYMENT_STATUSES:
                    raise HTTPException(
                        status_code=422,
                        detail=f"Unsupported payment status '{normalized_pay}'.",
                    )
                order.payment_status = normalized_pay

            order.updated_at = now
            db.commit()
            db.refresh(order)
            return OrderService.serialize_order_full(db, order)
        except HTTPException:
            db.rollback()
            raise
        except Exception as exc:
            db.rollback()
            raise HTTPException(
                status_code=400, detail=f"Unable to update order: {exc}"
            ) from exc

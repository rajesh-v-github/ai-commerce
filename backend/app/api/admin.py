from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
import re
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_support_user
from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import hash_password
from app.database.db import get_db
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.admin import (
    AdminCustomerCreate,
    AdminCustomerUpdate,
    AdminOrderStatusUpdate,
    AdminProductCreate,
    AdminProductUpdate,
    GenerateDescriptionRequest,
    InventoryAdjustmentRequest,
)
from app.services.ollama_service import (
    AIServiceUnavailableError,
    check_ai_service_status,
    generate_product_description,
)
from app.services.order_service import OrderService
from app.services.product_service import ProductService

logger = get_logger("ai_commerce.admin")

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(get_current_support_user)],
)

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".svg"}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB


@router.get("/dashboard")
def get_admin_dashboard(
    days: int = Query(default=14, ge=7, le=90),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_support_user),
):
    ProductService.ensure_catalog_defaults(db)

    all_products = db.query(Product).order_by(Product.id.asc()).all()
    all_orders = db.query(Order).order_by(Order.id.desc()).all()
    all_customers = db.query(User).filter(User.role == "customer").all()

    non_cancelled_orders = [
        o for o in all_orders if (o.status or "").upper() != "CANCELLED"
    ]
    cancelled_orders = [
        o for o in all_orders if (o.status or "").upper() == "CANCELLED"
    ]

    total_revenue = sum(
        (Decimal(str(o.total_amount or 0)) for o in non_cancelled_orders),
        Decimal("0.00"),
    )
    gross_revenue = sum(
        (Decimal(str(o.total_amount or 0)) for o in all_orders),
        Decimal("0.00"),
    )
    avg_order_value = (
        total_revenue / len(non_cancelled_orders)
        if non_cancelled_orders
        else Decimal("0.00")
    )

    active_products = [
        p for p in all_products if bool(True if p.is_active is None else p.is_active)
    ]
    out_of_stock_products = [
        ProductService.serialize_product(p)
        for p in active_products
        if int(p.stock or 0) <= 0
    ]
    low_stock_products = [
        ProductService.serialize_product(p)
        for p in active_products
        if 0
        < int(p.stock or 0)
        <= int(p.low_stock_threshold if p.low_stock_threshold is not None else 10)
    ]

    # Daily revenue & order volume trend from actual DB timestamps
    today = datetime.utcnow().date()
    # Anchor window to include most recent order date if dataset timestamps are earlier/later
    dated_orders = [o.created_at.date() for o in all_orders if o.created_at is not None]
    anchor_date = max([today, *dated_orders]) if dated_orders else today
    window_start = anchor_date - timedelta(days=days - 1)

    revenue_by_day: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
    orders_by_day: Counter[str] = Counter()
    for order in non_cancelled_orders:
        if order.created_at is None:
            continue
        order_day = order.created_at.date()
        if window_start <= order_day <= anchor_date:
            key = order_day.isoformat()
            revenue_by_day[key] += Decimal(str(order.total_amount or 0))
            orders_by_day[key] += 1

    revenue_trend = []
    for offset in range(days - 1, -1, -1):
        d = (anchor_date - timedelta(days=offset)).isoformat()
        revenue_trend.append(
            {
                "date": d,
                "revenue": round(float(revenue_by_day[d]), 2),
                "orders": orders_by_day[d],
            }
        )

    # Order status distribution
    status_counts: Counter[str] = Counter()
    status_revenue: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
    for order in all_orders:
        st = (order.status or "PROCESSING").upper()
        status_counts[st] += 1
        status_revenue[st] += Decimal(str(order.total_amount or 0))

    order_status_breakdown = [
        {
            "status": st,
            "count": status_counts[st],
            "amount": round(float(status_revenue[st]), 2),
        }
        for st in sorted(status_counts.keys())
    ]

    # Best-selling products & category sales performance from actual non-cancelled order items
    products_by_id = {p.id: p for p in all_products}
    valid_order_ids = {o.id for o in non_cancelled_orders}
    order_items = (
        db.query(OrderItem).filter(OrderItem.order_id.in_(valid_order_ids)).all()
        if valid_order_ids
        else []
    )

    product_units: Counter[int | str] = Counter()
    product_revenue: dict[int | str, Decimal] = defaultdict(lambda: Decimal("0.00"))
    product_labels: dict[int | str, str] = {}
    category_revenue: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
    category_units: Counter[str] = Counter()

    for item in order_items:
        qty = int(item.quantity or 0)
        line_rev = Decimal(str(item.unit_price or 0)) * qty
        key = item.product_id if item.product_id is not None else (item.product_name or "unknown")
        product_units[key] += qty
        product_revenue[key] += line_rev

        catalog_prod = (
            products_by_id.get(item.product_id) if item.product_id is not None else None
        )
        product_labels[key] = (
            catalog_prod.name if catalog_prod else (item.product_name or f"Product #{key}")
        )
        category_name = (
            catalog_prod.category if catalog_prod and catalog_prod.category else "Uncategorized"
        )
        category_revenue[category_name] += line_rev
        category_units[category_name] += qty

    best_selling = []
    for key, units_sold in sorted(
        product_units.items(),
        key=lambda kv: (kv[1], product_revenue[kv[0]]),
        reverse=True,
    )[:8]:
        catalog_prod = products_by_id.get(key) if isinstance(key, int) else None
        serialized_prod = (
            ProductService.serialize_product(catalog_prod) if catalog_prod else None
        )
        best_selling.append(
            {
                "product_id": key if isinstance(key, int) else None,
                "name": product_labels[key],
                "category": serialized_prod["category"] if serialized_prod else "Catalog Archive",
                "image_url": serialized_prod["image_url"] if serialized_prod else None,
                "current_stock": serialized_prod["stock"] if serialized_prod else None,
                "units_sold": units_sold,
                "revenue": round(float(product_revenue[key]), 2),
            }
        )

    category_performance = [
        {
            "category": cat,
            "units_sold": category_units[cat],
            "revenue": round(float(rev), 2),
        }
        for cat, rev in sorted(
            category_revenue.items(), key=lambda kv: kv[1], reverse=True
        )
    ]

    customers_with_orders = len(
        {o.customer_id for o in all_orders if o.customer_id is not None}
    )

    return {
        "kpis": {
            "total_revenue": round(float(total_revenue), 2),
            "gross_revenue": round(float(gross_revenue), 2),
            "average_order_value": round(float(avg_order_value), 2),
            "total_orders": len(all_orders),
            "active_orders": sum(
                1
                for o in all_orders
                if (o.status or "").upper() in {"PROCESSING", "CONFIRMED", "SHIPPED"}
            ),
            "delivered_orders": status_counts.get("DELIVERED", 0),
            "cancelled_orders": len(cancelled_orders),
            "total_customers": len(all_customers),
            "customers_with_orders": customers_with_orders,
            "total_products": len(all_products),
            "active_products": len(active_products),
            "inactive_products": len(all_products) - len(active_products),
            "low_stock_count": len(low_stock_products),
            "out_of_stock_count": len(out_of_stock_products),
        },
        "low_stock_products": low_stock_products,
        "out_of_stock_products": out_of_stock_products,
        "recent_orders": [
            OrderService.serialize_order_summary(o) for o in all_orders[:8]
        ],
        "latest_order_id": all_orders[0].id if all_orders else 0,
        "revenue_trend": revenue_trend,
        "order_status_breakdown": order_status_breakdown,
        "category_performance": category_performance,
        "best_selling_products": best_selling,
    }


# ==========================================
# PRODUCT & INVENTORY MANAGEMENT + AI
# ==========================================


@router.get("/products")
def admin_list_products(
    search: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    stock_filter: str = Query(default="all"),
    sort: str = Query(default="id_asc"),
    db: Session = Depends(get_db),
):
    products = ProductService.get_products(db, include_inactive=True)
    categories = sorted({p["category"] for p in products if p.get("category")})

    if search and search.strip():
        needle = search.strip().lower()
        products = [
            p
            for p in products
            if needle in (p["name"] or "").lower()
            or needle in (p["category"] or "").lower()
            or needle in (p["brand"] or "").lower()
            or needle in (p.get("sku") or "").lower()
            or needle in (p["description"] or "").lower()
        ]

    if category and category.strip() and category.strip().lower() != "all":
        target_cat = category.strip().lower()
        products = [
            p for p in products if (p["category"] or "").lower() == target_cat
        ]

    if stock_filter == "low_stock":
        products = [p for p in products if p["is_active"] and p["is_low_stock"]]
    elif stock_filter == "out_of_stock":
        products = [p for p in products if p["is_active"] and p["is_out_of_stock"]]
    elif stock_filter == "in_stock":
        products = [
            p
            for p in products
            if p["is_active"] and not p["is_out_of_stock"] and not p["is_low_stock"]
        ]
    elif stock_filter == "inactive":
        products = [p for p in products if not p["is_active"]]

    if sort == "price_asc":
        products.sort(key=lambda p: p["price"])
    elif sort == "price_desc":
        products.sort(key=lambda p: -p["price"])
    elif sort == "stock_asc":
        products.sort(key=lambda p: p["stock"])
    elif sort == "stock_desc":
        products.sort(key=lambda p: -p["stock"])
    elif sort == "name_asc":
        products.sort(key=lambda p: p["name"].lower())
    elif sort == "newest":
        products.sort(key=lambda p: -p["id"])
    else:
        products.sort(key=lambda p: p["id"])

    return {
        "products": products,
        "total": len(products),
        "categories": categories,
        "next_sku_serial": ProductService.get_next_sku_serial(db),
    }


@router.post("/products")
def admin_create_product(
    request: AdminProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_support_user),
):
    product = ProductService.create_product(db, request)
    logger.info("Product '%s' (id=%s) created by %s", product.name, product.id, current_user.username)
    return ProductService.serialize_product(product)


@router.put("/products/{product_id}")
def admin_update_product(
    product_id: int,
    request: AdminProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_support_user),
):
    product = ProductService.update_product(db, product_id, request)
    logger.info("Product '%s' (id=%s) updated by %s", product.name, product.id, current_user.username)
    return ProductService.serialize_product(product)


@router.patch("/products/{product_id}/inventory")
def admin_adjust_inventory(
    product_id: int,
    request: InventoryAdjustmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_support_user),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    product.stock = int(request.stock)
    if request.low_stock_threshold is not None:
        product.low_stock_threshold = int(request.low_stock_threshold)
    product.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(product)
    logger.info(
        "Inventory updated for product id=%s (stock=%s) by %s",
        product.id,
        product.stock,
        current_user.username,
    )
    return ProductService.serialize_product(product)


@router.delete("/products/{product_id}")
def admin_delete_or_deactivate_product(
    product_id: int,
    deactivate_only: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_support_user),
):
    result = ProductService.delete_or_deactivate_product(
        db, product_id, force_deactivate=deactivate_only
    )
    logger.info(
        "Product id=%s %s by %s",
        product_id,
        result["action"],
        current_user.username,
    )
    return result


@router.post("/products/upload-image")
async def admin_upload_product_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_support_user),
):
    filename = file.filename or ""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail="Unsupported image format. Upload a JPG, PNG, WebP, or SVG image.",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="Uploaded image file is empty.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Image exceeds the 5 MB maximum upload size.",
        )

    upload_dir = Path(settings.UPLOAD_DIR).resolve() / "products"
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"prod-{uuid.uuid4().hex[:12]}{ext}"
    destination = upload_dir / safe_name
    destination.write_bytes(content)

    logger.info("Uploaded product image '%s' by %s", safe_name, current_user.username)
    return {"image_url": f"/api/uploads/products/{safe_name}"}


@router.get("/ai/status")
def admin_ai_status():
    return check_ai_service_status()


@router.post("/products/generate-description")
def admin_generate_product_description(
    request: GenerateDescriptionRequest,
    current_user: User = Depends(get_current_support_user),
):
    try:
        result = generate_product_description(
            name=request.name,
            category=request.category,
            brand=request.brand,
            attributes=request.attributes,
            specifications=request.specifications,
            features=request.features,
            target_audience=request.target_audience,
            tone=request.tone,
        )
        return result
    except AIServiceUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


# ==========================================
# ORDER MANAGEMENT
# ==========================================


@router.get("/orders")
def admin_list_orders(
    status: Optional[str] = Query(default=None),
    payment_status: Optional[str] = Query(default=None),
    customer_id: Optional[int] = Query(default=None),
    search: Optional[str] = Query(default=None),
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    since_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(Order)

    if status and status.strip() and status.strip().upper() != "ALL":
        query = query.filter(Order.status == status.strip().upper())

    if (
        payment_status
        and payment_status.strip()
        and payment_status.strip().upper() != "ALL"
    ):
        query = query.filter(Order.payment_status == payment_status.strip().upper())

    if customer_id is not None:
        query = query.filter(Order.customer_id == customer_id)

    if date_from is not None:
        query = query.filter(
            Order.created_at >= datetime.combine(date_from, time.min)
        )

    if date_to is not None:
        query = query.filter(
            Order.created_at <= datetime.combine(date_to, time.max)
        )

    if search and search.strip():
        needle = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Order.order_number.ilike(needle),
                Order.customer_name.ilike(needle),
                Order.shipping_full_name.ilike(needle),
                Order.shipping_email.ilike(needle),
            )
        )

    orders = query.order_by(Order.id.desc()).all()
    latest_id_row = db.query(Order.id).order_by(Order.id.desc()).first()
    latest_order_id = latest_id_row[0] if latest_id_row else 0

    new_orders_count = (
        sum(1 for o in orders if o.id > since_id) if since_id is not None else 0
    )

    return {
        "orders": [OrderService.serialize_order_summary(o) for o in orders],
        "total": len(orders),
        "latest_order_id": latest_order_id,
        "new_orders_count": new_orders_count,
    }


@router.get("/orders/{order_id}")
def admin_get_order_detail(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return OrderService.serialize_order_full(db, order)


@router.patch("/orders/{order_id}/status")
def admin_update_order_status(
    order_id: int,
    request: AdminOrderStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_support_user),
):
    updated = OrderService.update_order_status(
        db,
        order_id=order_id,
        new_status=request.status,
        payment_status=request.payment_status,
        note=request.note,
        changed_by=current_user,
    )
    logger.info(
        "Order id=%s updated (status=%s, payment=%s) by %s",
        order_id,
        updated["status"],
        updated["payment_status"],
        current_user.username,
    )
    return updated


# ==========================================
# CUSTOMER MANAGEMENT
# ==========================================


def _serialize_admin_customer(
    customer: User,
    orders: list[Order],
    tickets: list[Ticket],
) -> dict:
    non_cancelled = [o for o in orders if (o.status or "").upper() != "CANCELLED"]
    lifetime_spend = sum(
        (Decimal(str(o.total_amount or 0)) for o in non_cancelled),
        Decimal("0.00"),
    )
    dated = [o.created_at for o in orders if o.created_at is not None]
    last_order_at = max(dated).isoformat() if dated else None
    open_tickets = sum(
        1 for t in tickets if (t.status or "").upper() in {"OPEN", "IN_PROGRESS"}
    )
    return {
        "id": customer.id,
        "customer_id": customer.id,
        "username": customer.username,
        "full_name": customer.full_name or customer.username,
        "email": customer.email,
        "phone": customer.phone,
        "shipping_address": customer.shipping_address,
        "billing_address": customer.billing_address,
        "is_active": bool(True if customer.is_active is None else customer.is_active),
        "has_password": bool(customer.password_hash),
        "created_at": customer.created_at.isoformat() if customer.created_at else None,
        "total_orders": len(orders),
        "completed_orders": sum(
            1 for o in orders if (o.status or "").upper() == "DELIVERED"
        ),
        "lifetime_spend": round(float(lifetime_spend), 2),
        "last_order_at": last_order_at,
        "total_tickets": len(tickets),
        "open_tickets": open_tickets,
    }


@router.get("/customers")
def admin_list_customers(
    search: Optional[str] = Query(default=None),
    filter_by: str = Query(default="all"),
    db: Session = Depends(get_db),
):
    customers = (
        db.query(User).filter(User.role == "customer").order_by(User.id.desc()).all()
    )
    all_orders = db.query(Order).order_by(Order.id.desc()).all()
    all_tickets = db.query(Ticket).all()

    orders_by_customer: dict[int, list[Order]] = defaultdict(list)
    for o in all_orders:
        if o.customer_id is not None:
            orders_by_customer[o.customer_id].append(o)

    tickets_by_customer: dict[int, list[Ticket]] = defaultdict(list)
    for t in all_tickets:
        if t.user_id is not None:
            tickets_by_customer[t.user_id].append(t)

    serialized = [
        _serialize_admin_customer(
            c, orders_by_customer[c.id], tickets_by_customer[c.id]
        )
        for c in customers
    ]

    if search and search.strip():
        needle = search.strip().lower()
        serialized = [
            c
            for c in serialized
            if needle in (c["username"] or "").lower()
            or needle in (c["full_name"] or "").lower()
            or needle in (c["email"] or "").lower()
            or needle in (c["phone"] or "").lower()
        ]

    if filter_by == "with_orders":
        serialized = [c for c in serialized if c["total_orders"] > 0]
    elif filter_by == "open_tickets":
        serialized = [c for c in serialized if c["open_tickets"] > 0]
    elif filter_by == "active":
        serialized = [c for c in serialized if c["is_active"]]
    elif filter_by == "inactive":
        serialized = [c for c in serialized if not c["is_active"]]

    return {
        "customers": serialized,
        "total": len(serialized),
    }


@router.post("/customers")
def admin_create_customer(
    request: AdminCustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_support_user),
):
    username = request.username.strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,40}", username):
        raise HTTPException(
            status_code=422,
            detail="Username must be 3-40 characters (letters, numbers, _, ., -).",
        )
    email = request.email.strip().lower()

    if db.query(User).filter(User.username == username).first():
        raise HTTPException(
            status_code=409,
            detail=f"Customer username '{username}' already exists.",
        )
    if db.query(User).filter(User.email.ilike(email)).first():
        raise HTTPException(
            status_code=409,
            detail=f"A customer with email '{email}' already exists.",
        )

    customer = User(
        username=username,
        password_hash=hash_password(request.password) if request.password else None,
        role="customer",
        full_name=request.full_name.strip(),
        email=email,
        phone=(request.phone or "").strip() or None,
        shipping_address=(request.shipping_address or "").strip() or None,
        billing_address=(request.billing_address or "").strip() or None,
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    logger.info("Customer '%s' created by %s", customer.username, current_user.username)
    return _serialize_admin_customer(customer, [], [])


@router.get("/customers/{customer_id}")
def admin_get_customer_profile(customer_id: int, db: Session = Depends(get_db)):
    customer = (
        db.query(User)
        .filter(User.id == customer_id, User.role == "customer")
        .first()
    )
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    orders = (
        db.query(Order)
        .filter(Order.customer_id == customer.id)
        .order_by(Order.id.desc())
        .all()
    )
    tickets = (
        db.query(Ticket)
        .filter(Ticket.user_id == customer.id)
        .order_by(Ticket.id.desc())
        .all()
    )

    summary = _serialize_admin_customer(customer, orders, tickets)
    return {
        "customer": summary,
        "orders": [OrderService.serialize_order_full(db, o) for o in orders],
        "tickets": [
            {
                "id": t.id,
                "ticket_number": t.ticket_number,
                "subject": t.subject,
                "status": t.status,
                "priority": t.priority or "MEDIUM",
            }
            for t in tickets
        ],
    }


@router.put("/customers/{customer_id}")
def admin_update_customer(
    customer_id: int,
    request: AdminCustomerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_support_user),
):
    customer = (
        db.query(User)
        .filter(User.id == customer_id, User.role == "customer")
        .first()
    )
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    if request.email is not None:
        normalized_email = request.email.strip().lower()
        conflict = (
            db.query(User)
            .filter(User.email.ilike(normalized_email), User.id != customer.id)
            .first()
        )
        if conflict:
            raise HTTPException(
                status_code=409,
                detail=f"Email '{normalized_email}' is already used by another account.",
            )
        customer.email = normalized_email

    if request.full_name is not None:
        customer.full_name = request.full_name.strip()
    if request.phone is not None:
        customer.phone = request.phone.strip() or None
    if request.shipping_address is not None:
        customer.shipping_address = request.shipping_address.strip() or None
    if request.billing_address is not None:
        customer.billing_address = request.billing_address.strip() or None
    if request.password is not None and request.password.strip():
        customer.password_hash = hash_password(request.password.strip())
    if request.is_active is not None:
        customer.is_active = bool(request.is_active)

    db.commit()
    db.refresh(customer)

    orders = db.query(Order).filter(Order.customer_id == customer.id).all()
    tickets = db.query(Ticket).filter(Ticket.user_id == customer.id).all()
    logger.info("Customer '%s' updated by %s", customer.username, current_user.username)
    return _serialize_admin_customer(customer, orders, tickets)

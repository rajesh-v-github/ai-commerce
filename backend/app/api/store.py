from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_optional_current_user
from app.database.db import get_db
from app.models.cart_item import CartItem
from app.models.order import Order
from app.models.product import Product
from app.models.user import User
from app.schemas.store import CartSyncRequest, StorefrontCheckoutRequest
from app.services.order_service import (
    FREE_SHIPPING_THRESHOLD,
    INCLUDED_GST_RATE,
    STANDARD_SHIPPING_FEE,
    OrderService,
)
from app.services.product_service import ProductService

router = APIRouter(prefix="/store", tags=["Storefront"])


@router.get("/products")
def browse_store_products(
    q: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    brand: Optional[str] = Query(default=None),
    min_price: Optional[float] = Query(default=None, ge=0),
    max_price: Optional[float] = Query(default=None, ge=0),
    in_stock: bool = Query(default=False),
    sort: str = Query(default="featured"),
    db: Session = Depends(get_db),
):
    all_active = ProductService.get_products(db, include_inactive=False)

    categories = sorted(
        {p["category"] for p in all_active if p.get("category")}
    )
    brands = sorted({p["brand"] for p in all_active if p.get("brand")})

    filtered = all_active
    if q and q.strip():
        needle = q.strip().lower()
        filtered = [
            p
            for p in filtered
            if needle in (p["name"] or "").lower()
            or needle in (p["description"] or "").lower()
            or needle in (p["category"] or "").lower()
            or needle in (p["brand"] or "").lower()
            or needle in (p.get("specifications") or "").lower()
            or needle in (p.get("sku") or "").lower()
        ]

    if category and category.strip() and category.strip().lower() != "all":
        target_cat = category.strip().lower()
        filtered = [
            p for p in filtered if (p["category"] or "").lower() == target_cat
        ]

    if brand and brand.strip() and brand.strip().lower() != "all":
        target_brand = brand.strip().lower()
        filtered = [
            p for p in filtered if (p["brand"] or "").lower() == target_brand
        ]

    if min_price is not None:
        filtered = [p for p in filtered if p["price"] >= min_price]

    if max_price is not None:
        filtered = [p for p in filtered if p["price"] <= max_price]

    if in_stock:
        filtered = [p for p in filtered if p["stock"] > 0]

    if sort == "price_asc":
        filtered.sort(key=lambda p: (p["price"], p["name"].lower()))
    elif sort == "price_desc":
        filtered.sort(key=lambda p: (-p["price"], p["name"].lower()))
    elif sort == "name_asc":
        filtered.sort(key=lambda p: p["name"].lower())
    elif sort == "stock_desc":
        filtered.sort(key=lambda p: (-p["stock"], p["id"]))
    else:
        # Featured: in-stock first, then by catalog ID
        filtered.sort(key=lambda p: (p["stock"] <= 0, p["id"]))

    return {
        "products": filtered,
        "total": len(filtered),
        "categories": categories,
        "brands": brands,
    }


@router.get("/categories")
def list_store_categories(db: Session = Depends(get_db)):
    all_active = ProductService.get_products(db, include_inactive=False)
    grouped: dict[str, dict] = {}
    for product in all_active:
        cat = product["category"] or "Uncategorized"
        if cat not in grouped:
            grouped[cat] = {
                "name": cat,
                "product_count": 0,
                "in_stock_count": 0,
                "image_url": product["image_url"],
                "starting_price": product["price"],
            }
        grouped[cat]["product_count"] += 1
        if product["stock"] > 0:
            grouped[cat]["in_stock_count"] += 1
        grouped[cat]["starting_price"] = min(
            grouped[cat]["starting_price"], product["price"]
        )

    return sorted(grouped.values(), key=lambda c: c["name"].lower())


@router.get("/products/{product_id}")
def get_store_product_detail(product_id: int, db: Session = Depends(get_db)):
    ProductService.ensure_catalog_defaults(db)
    product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.is_active.is_(True))
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    serialized = ProductService.serialize_product(product)
    related = (
        db.query(Product)
        .filter(
            Product.is_active.is_(True),
            Product.category == product.category,
            Product.id != product.id,
        )
        .order_by(Product.id.asc())
        .limit(4)
        .all()
    )
    if len(related) < 4:
        existing_ids = {product.id, *(r.id for r in related)}
        filler = (
            db.query(Product)
            .filter(
                Product.is_active.is_(True),
                Product.id.notin_(existing_ids),
                Product.stock > 0,
            )
            .order_by(Product.id.asc())
            .limit(4 - len(related))
            .all()
        )
        related.extend(filler)

    return {
        "product": serialized,
        "related_products": [ProductService.serialize_product(r) for r in related],
    }


def _evaluate_cart_lines(db: Session, items) -> dict:
    ProductService.ensure_catalog_defaults(db)
    consolidated: dict[int, int] = {}
    for item in items:
        consolidated[item.product_id] = consolidated.get(item.product_id, 0) + int(
            item.quantity
        )

    product_ids = list(consolidated.keys())
    products_by_id = (
        {
            p.id: p
            for p in db.query(Product).filter(Product.id.in_(product_ids)).all()
        }
        if product_ids
        else {}
    )

    lines = []
    warnings = []
    subtotal = Decimal("0.00")

    for pid, requested_qty in consolidated.items():
        product = products_by_id.get(pid)
        if not product or getattr(product, "is_active", True) is False:
            warnings.append(f"A product (ID #{pid}) is no longer available and was removed.")
            continue

        available = int(product.stock or 0)
        if available <= 0:
            warnings.append(f"'{product.name}' is currently out of stock.")
            effective_qty = 0
        elif requested_qty > available:
            warnings.append(
                f"Only {available} unit(s) of '{product.name}' are available; quantity adjusted."
            )
            effective_qty = available
        else:
            effective_qty = requested_qty

        serialized = ProductService.serialize_product(product)
        unit_price = Decimal(str(product.price or 0))
        line_total = unit_price * effective_qty
        subtotal += line_total
        lines.append(
            {
                "product_id": product.id,
                "product": serialized,
                "requested_quantity": requested_qty,
                "quantity": effective_qty,
                "available_stock": available,
                "unit_price": float(unit_price),
                "line_total": float(line_total),
            }
        )

    shipping_fee = (
        Decimal("0.00")
        if subtotal == 0 or subtotal >= FREE_SHIPPING_THRESHOLD
        else STANDARD_SHIPPING_FEE
    )
    included_gst = (
        subtotal * INCLUDED_GST_RATE / (Decimal("1.00") + INCLUDED_GST_RATE)
    )
    grand_total = subtotal + shipping_fee
    remaining_for_free_shipping = max(
        Decimal("0.00"), FREE_SHIPPING_THRESHOLD - subtotal
    )

    return {
        "items": lines,
        "item_count": sum(line["quantity"] for line in lines),
        "subtotal_amount": round(float(subtotal), 2),
        "shipping_amount": round(float(shipping_fee), 2),
        "included_gst_amount": round(float(included_gst), 2),
        "total_amount": round(float(grand_total), 2),
        "free_shipping_threshold": float(FREE_SHIPPING_THRESHOLD),
        "amount_to_free_shipping": round(float(remaining_for_free_shipping), 2),
        "warnings": warnings,
        "valid_for_checkout": len(lines) > 0
        and all(line["quantity"] > 0 for line in lines)
        and len(warnings) == 0,
    }


@router.post("/cart/validate")
def validate_cart(request: CartSyncRequest, db: Session = Depends(get_db)):
    return _evaluate_cart_lines(db, request.items)


@router.get("/cart")
def get_saved_cart(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = (
        db.query(CartItem)
        .filter(CartItem.user_id == current_user.id)
        .order_by(CartItem.id.asc())
        .all()
    )
    return _evaluate_cart_lines(db, rows)


@router.put("/cart")
def sync_saved_cart(
    request: CartSyncRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db.query(CartItem).filter(CartItem.user_id == current_user.id).delete()
    now = datetime.utcnow()
    merged: dict[int, int] = {}
    for item in request.items:
        merged[item.product_id] = merged.get(item.product_id, 0) + int(item.quantity)

    for pid, qty in merged.items():
        product = (
            db.query(Product)
            .filter(Product.id == pid, Product.is_active.is_(True))
            .first()
        )
        if product and (product.stock or 0) > 0:
            clamped = min(qty, int(product.stock))
            db.add(
                CartItem(
                    user_id=current_user.id,
                    product_id=pid,
                    quantity=clamped,
                    updated_at=now,
                )
            )
    db.commit()
    rows = (
        db.query(CartItem)
        .filter(CartItem.user_id == current_user.id)
        .order_by(CartItem.id.asc())
        .all()
    )
    return _evaluate_cart_lines(db, rows)


@router.delete("/cart")
def clear_saved_cart(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db.query(CartItem).filter(CartItem.user_id == current_user.id).delete()
    db.commit()
    return {"status": "cleared"}


@router.post("/checkout")
def storefront_checkout(
    request: StorefrontCheckoutRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    return OrderService.place_storefront_order(db, request, current_user)


@router.get("/orders/confirmation/{order_number}")
def get_order_confirmation(
    order_number: str,
    ref: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    order = db.query(Order).filter(Order.order_number == order_number).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Enforce strict authorization: owner, support executive, or matching payment reference from checkout session
    authorized = False
    if current_user is not None:
        if current_user.role == "support" or order.customer_id == current_user.id:
            authorized = True
    if not authorized and ref and order.payment_reference and ref == order.payment_reference:
        authorized = True

    if not authorized:
        raise HTTPException(status_code=403, detail="Access denied")

    return OrderService.serialize_order_full(db, order)

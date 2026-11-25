from datetime import datetime
from decimal import Decimal
import re
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.cart_item import CartItem
from app.models.order import OrderItem
from app.models.product import Product
from app.repositories.product_repository import ProductRepository
from app.utils.product_catalog_defaults import (
    DEFAULT_FALLBACK_IMAGE,
    derive_sku_category_code,
    format_serial_sku,
    resolve_product_defaults,
)


class ProductService:
    @staticmethod
    def get_next_sku_serial(db: Session) -> int:
        max_serial = 0
        rows = db.query(Product.id, Product.sku).all()
        for prod_id, sku in rows:
            if prod_id is not None and int(prod_id) > max_serial:
                max_serial = int(prod_id)
            if sku:
                match = re.search(r"(\d+)$", sku.strip())
                if match:
                    val = int(match.group(1))
                    # Ignore synthetic 900+ test SKUs if regular catalog serials exist,
                    # unless it's a sequential catalog SKU
                    if val < 900 and val > max_serial:
                        max_serial = val
        return max_serial + 1

    @staticmethod
    def generate_unique_serial_sku(
        db: Session,
        *,
        category: str | None,
        name: str | None,
        preferred_serial: int | None = None,
        exclude_product_id: int | None = None,
    ) -> str:
        serial = (
            int(preferred_serial)
            if preferred_serial is not None and int(preferred_serial) > 0
            else ProductService.get_next_sku_serial(db)
        )
        while True:
            candidate = format_serial_sku(category, name, serial)
            q = db.query(Product).filter(Product.sku == candidate)
            if exclude_product_id is not None:
                q = q.filter(Product.id != exclude_product_id)
            if not q.first():
                return candidate
            serial += 1
    @staticmethod
    def ensure_catalog_defaults(db: Session) -> None:
        """Populate missing visual/catalog metadata on existing rows without overwriting valid data."""
        products_missing_meta = (
            db.query(Product)
            .filter((Product.image_url.is_(None)) | (Product.image_url == ""))
            .all()
        )
        if not products_missing_meta:
            return

        existing_skus = {
            row[0]
            for row in db.query(Product.sku).filter(Product.sku.isnot(None)).all()
            if row[0]
        }
        now = datetime.utcnow()
        for product in products_missing_meta:
            defaults = resolve_product_defaults(
                product.name, product.category, product.id
            )
            if not product.image_url or not product.image_url.strip():
                product.image_url = defaults.get("image_url") or DEFAULT_FALLBACK_IMAGE
            if not product.brand:
                product.brand = defaults.get("brand")
            if not product.sku:
                candidate = defaults.get("sku")
                if candidate and candidate not in existing_skus:
                    product.sku = candidate
                    existing_skus.add(candidate)
                elif product.id is not None:
                    fallback_sku = f"SG-PRD-{product.id:04d}"
                    if fallback_sku not in existing_skus:
                        product.sku = fallback_sku
                        existing_skus.add(fallback_sku)
            if not product.specifications and defaults.get("specifications"):
                product.specifications = defaults["specifications"]
            if not product.target_audience and defaults.get("target_audience"):
                product.target_audience = defaults["target_audience"]
            if product.low_stock_threshold is None:
                product.low_stock_threshold = defaults.get("low_stock_threshold", 10)
            if product.created_at is None:
                product.created_at = now
            if product.updated_at is None:
                product.updated_at = now

        db.commit()

    @staticmethod
    def serialize_product(product: Product) -> dict[str, Any]:
        defaults = resolve_product_defaults(product.name, product.category, product.id)
        stock = int(product.stock or 0)
        threshold = (
            int(product.low_stock_threshold)
            if product.low_stock_threshold is not None
            else 10
        )
        image_url = (
            product.image_url.strip()
            if product.image_url and product.image_url.strip()
            else defaults.get("image_url") or DEFAULT_FALLBACK_IMAGE
        )
        is_active = bool(True if product.is_active is None else product.is_active)
        return {
            "id": product.id,
            "name": product.name,
            "description": product.description or "",
            "category": product.category or "Uncategorized",
            "brand": product.brand or defaults.get("brand") or "SoranoGear",
            "sku": product.sku,
            "price": float(product.price or 0),
            "stock": stock,
            "low_stock_threshold": threshold,
            "is_active": is_active,
            "is_out_of_stock": stock <= 0,
            "is_low_stock": 0 < stock <= threshold,
            "image_url": image_url,
            "specifications": product.specifications,
            "target_audience": product.target_audience,
            "created_at": (
                product.created_at.isoformat() if product.created_at else None
            ),
            "updated_at": (
                product.updated_at.isoformat() if product.updated_at else None
            ),
        }

    @staticmethod
    def get_products(db: Session, *, include_inactive: bool = False):
        ProductService.ensure_catalog_defaults(db)
        query = db.query(Product)
        if not include_inactive:
            query = query.filter(Product.is_active.is_(True))
        products = query.order_by(Product.id.asc()).all()
        return [ProductService.serialize_product(p) for p in products]

    @staticmethod
    def get_product(db: Session, product_id: int):
        ProductService.ensure_catalog_defaults(db)
        return ProductRepository.get_by_id(db, product_id)

    @staticmethod
    def create_product(db: Session, payload) -> Product:
        name = payload.name.strip()
        category = payload.category.strip()
        if not name:
            raise HTTPException(status_code=422, detail="Product name is required")
        if not category:
            raise HTTPException(status_code=422, detail="Product category is required")

        sku = (
            payload.sku.strip().upper()
            if getattr(payload, "sku", None) and payload.sku.strip()
            else None
        )
        if not sku:
            sku = ProductService.generate_unique_serial_sku(
                db, category=category, name=name
            )
        else:
            duplicate_sku = db.query(Product).filter(Product.sku == sku).first()
            if duplicate_sku:
                raise HTTPException(
                    status_code=409,
                    detail=f"A product with SKU '{sku}' already exists.",
                )

        defaults = resolve_product_defaults(name, category, None)
        image_url = (
            payload.image_url.strip()
            if getattr(payload, "image_url", None) and payload.image_url.strip()
            else defaults.get("image_url") or DEFAULT_FALLBACK_IMAGE
        )
        now = datetime.utcnow()
        product = Product(
            name=name,
            description=(payload.description or "").strip(),
            category=category,
            brand=(payload.brand.strip() if getattr(payload, "brand", None) and payload.brand.strip() else defaults.get("brand") or "SoranoGear"),
            sku=sku,
            price=Decimal(str(round(float(payload.price), 2))),
            stock=int(payload.stock),
            low_stock_threshold=int(getattr(payload, "low_stock_threshold", 10)),
            is_active=bool(getattr(payload, "is_active", True)),
            image_url=image_url,
            specifications=(
                payload.specifications.strip()
                if getattr(payload, "specifications", None) and payload.specifications.strip()
                else None
            ),
            target_audience=(
                payload.target_audience.strip()
                if getattr(payload, "target_audience", None) and payload.target_audience.strip()
                else None
            ),
            created_at=now,
            updated_at=now,
        )
        db.add(product)
        db.flush()
        if not product.sku:
            product.sku = ProductService.generate_unique_serial_sku(
                db,
                category=category,
                name=name,
                preferred_serial=product.id,
                exclude_product_id=product.id,
            )
        db.commit()
        db.refresh(product)
        return product

    @staticmethod
    def update_product(db: Session, product_id: int, payload) -> Product:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        category_or_name_changed = False
        if payload.name is not None:
            if not payload.name.strip():
                raise HTTPException(status_code=422, detail="Product name cannot be empty")
            if payload.name.strip() != product.name:
                category_or_name_changed = True
            product.name = payload.name.strip()

        if payload.description is not None:
            product.description = payload.description.strip()

        if payload.category is not None:
            if not payload.category.strip():
                raise HTTPException(status_code=422, detail="Category cannot be empty")
            if payload.category.strip() != product.category:
                category_or_name_changed = True
            product.category = payload.category.strip()

        if payload.brand is not None:
            product.brand = payload.brand.strip() or "SoranoGear"

        # Keep serial SKU synchronized with category/product naming convention
        existing_serial_match = (
            re.search(r"(\d+)$", product.sku.strip()) if product.sku else None
        )
        preserved_serial = (
            int(existing_serial_match.group(1))
            if existing_serial_match
            else product.id
        )
        if not product.sku or category_or_name_changed:
            expected_code = derive_sku_category_code(product.category, product.name)
            current_code_match = (
                re.match(r"^SG-([A-Z0-9]{3})-\d+$", product.sku or "")
            )
            if not current_code_match or current_code_match.group(1) != expected_code:
                product.sku = ProductService.generate_unique_serial_sku(
                    db,
                    category=product.category,
                    name=product.name,
                    preferred_serial=preserved_serial,
                    exclude_product_id=product_id,
                )
        elif payload.sku is not None and payload.sku.strip():
            normalized_sku = payload.sku.strip().upper()
            if normalized_sku != product.sku:
                existing = (
                    db.query(Product)
                    .filter(Product.sku == normalized_sku, Product.id != product_id)
                    .first()
                )
                if existing:
                    raise HTTPException(
                        status_code=409,
                        detail=f"SKU '{normalized_sku}' is already assigned to another product.",
                    )
                product.sku = normalized_sku

        if payload.price is not None:
            product.price = Decimal(str(round(float(payload.price), 2)))

        if payload.stock is not None:
            product.stock = int(payload.stock)

        if payload.low_stock_threshold is not None:
            product.low_stock_threshold = int(payload.low_stock_threshold)

        if payload.is_active is not None:
            product.is_active = bool(payload.is_active)

        if payload.image_url is not None and payload.image_url.strip():
            product.image_url = payload.image_url.strip()

        if payload.specifications is not None:
            product.specifications = payload.specifications.strip() or None

        if payload.target_audience is not None:
            product.target_audience = payload.target_audience.strip() or None

        product.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(product)
        return product

    @staticmethod
    def delete_or_deactivate_product(
        db: Session, product_id: int, *, force_deactivate: bool = False
    ) -> dict[str, Any]:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        referenced_in_orders = (
            db.query(OrderItem).filter(OrderItem.product_id == product_id).count() > 0
        )
        db.query(CartItem).filter(CartItem.product_id == product_id).delete()

        if referenced_in_orders or force_deactivate:
            product.is_active = False
            product.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(product)
            return {
                "action": "deactivated",
                "message": (
                    "Product has historical order records and was safely deactivated "
                    "to preserve order history."
                    if referenced_in_orders
                    else "Product deactivated."
                ),
                "product": ProductService.serialize_product(product),
            }

        serialized = ProductService.serialize_product(product)
        db.delete(product)
        db.commit()
        return {
            "action": "deleted",
            "message": "Product deleted permanently.",
            "product": serialized,
        }

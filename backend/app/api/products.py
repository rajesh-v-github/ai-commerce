from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models.product import Product

from app.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["products"])


@router.get("")
def list_products(db: Session = Depends(get_db)):
    return ProductService.get_products(db)


@router.post("/products")
def create_product(product: dict, db: Session = Depends(get_db)):
    new_product = Product(
        name=product["name"],
        description=product["description"],
        category=product["category"],
        stock=product["stock"],
        price=product["price"],
    )

    db.add(new_product)
    db.commit()
    db.refresh(new_product)

    return new_product

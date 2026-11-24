from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_support_user
from app.database.db import get_db
from app.models.user import User
from app.schemas.admin import AdminProductCreate
from app.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["products"])


@router.get("")
def list_products(db: Session = Depends(get_db)):
    return ProductService.get_products(db, include_inactive=False)


@router.post("/products")
def create_product(
    product: AdminProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_support_user),
):
    created = ProductService.create_product(db, product)
    return ProductService.serialize_product(created)

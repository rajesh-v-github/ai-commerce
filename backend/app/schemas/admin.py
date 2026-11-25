from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class AdminProductCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=160)
    description: str = Field(default="", max_length=4000)
    category: str = Field(..., min_length=2, max_length=100)
    brand: Optional[str] = Field(default=None, max_length=100)
    sku: Optional[str] = Field(default=None, max_length=60)
    price: float = Field(..., ge=0)
    stock: int = Field(..., ge=0)
    low_stock_threshold: int = Field(default=10, ge=0, le=10000)
    is_active: bool = True
    image_url: Optional[str] = Field(default=None, max_length=500)
    specifications: Optional[str] = Field(default=None, max_length=2000)
    target_audience: Optional[str] = Field(default=None, max_length=300)


class AdminProductUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=160)
    description: Optional[str] = Field(default=None, max_length=4000)
    category: Optional[str] = Field(default=None, min_length=2, max_length=100)
    brand: Optional[str] = Field(default=None, max_length=100)
    sku: Optional[str] = Field(default=None, max_length=60)
    price: Optional[float] = Field(default=None, ge=0)
    stock: Optional[int] = Field(default=None, ge=0)
    low_stock_threshold: Optional[int] = Field(default=None, ge=0, le=10000)
    is_active: Optional[bool] = None
    image_url: Optional[str] = Field(default=None, max_length=500)
    specifications: Optional[str] = Field(default=None, max_length=2000)
    target_audience: Optional[str] = Field(default=None, max_length=300)


class InventoryAdjustmentRequest(BaseModel):
    stock: int = Field(..., ge=0)
    low_stock_threshold: Optional[int] = Field(default=None, ge=0, le=10000)


class GenerateDescriptionRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=160)
    category: Optional[str] = Field(default=None, max_length=100)
    brand: Optional[str] = Field(default=None, max_length=100)
    attributes: Optional[str] = Field(default=None, max_length=1000)
    specifications: Optional[str] = Field(default=None, max_length=2000)
    features: Optional[str] = Field(default=None, max_length=1000)
    target_audience: Optional[str] = Field(default=None, max_length=300)
    tone: str = Field(default="professional", max_length=40)


class AdminOrderStatusUpdate(BaseModel):
    status: Optional[str] = None
    payment_status: Optional[str] = None
    note: Optional[str] = Field(default=None, max_length=300)


class AdminCustomerCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=40)
    full_name: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    phone: Optional[str] = Field(default=None, max_length=30)
    shipping_address: Optional[str] = Field(default=None, max_length=500)
    billing_address: Optional[str] = Field(default=None, max_length=500)
    password: Optional[str] = Field(default=None, min_length=8, max_length=72)


class AdminCustomerUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=30)
    shipping_address: Optional[str] = Field(default=None, max_length=500)
    billing_address: Optional[str] = Field(default=None, max_length=500)
    password: Optional[str] = Field(default=None, min_length=8, max_length=72)
    is_active: Optional[bool] = None

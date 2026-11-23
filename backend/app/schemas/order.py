from typing import List
from typing import Optional

from pydantic import BaseModel


class CheckoutItem(BaseModel):

    product_id: int

    quantity: int


class CheckoutRequest(BaseModel):

    items: List[CheckoutItem]

    customer_name: str

    idempotency_key: str


class CheckoutResponse(BaseModel):

    order_number: str

    total_amount: float

    status: str


class OrderProductDetails(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    current_price: Optional[float] = None
    stock: Optional[int] = None


class OrderItemDetails(BaseModel):
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    quantity: Optional[int] = None
    unit_price: Optional[float] = None
    line_total: float
    product: Optional[OrderProductDetails] = None


class OrderDetailsResponse(BaseModel):
    id: int
    order_number: str
    customer_name: Optional[str] = None
    customer_id: Optional[int] = None
    status: Optional[str] = None
    total_amount: float
    items: List[OrderItemDetails]
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class CartLineInput(BaseModel):
    product_id: int
    quantity: int = Field(..., ge=1, le=999)


class CartSyncRequest(BaseModel):
    items: List[CartLineInput]


class AddressInput(BaseModel):
    line1: str = Field(..., min_length=3, max_length=200)
    line2: Optional[str] = Field(default="", max_length=200)
    city: str = Field(..., min_length=2, max_length=100)
    state: str = Field(..., min_length=2, max_length=100)
    postal_code: str = Field(..., min_length=4, max_length=20)
    country: str = Field(default="India", min_length=2, max_length=80)

    def to_formatted_string(self) -> str:
        parts = [self.line1.strip()]
        if self.line2 and self.line2.strip():
            parts.append(self.line2.strip())
        parts.append(
            f"{self.city.strip()}, {self.state.strip()} {self.postal_code.strip()}"
        )
        parts.append(self.country.strip())
        return ", ".join(parts)


class StorefrontCheckoutRequest(BaseModel):
    items: List[CartLineInput] = Field(..., min_length=1)
    customer_full_name: str = Field(..., min_length=2, max_length=120)
    customer_email: EmailStr
    customer_phone: str = Field(..., min_length=7, max_length=25)
    shipping_address: AddressInput
    same_as_shipping: bool = True
    billing_address: Optional[AddressInput] = None
    payment_method: str = Field(default="MOCK_CARD")
    notes: Optional[str] = Field(default=None, max_length=500)
    idempotency_key: str = Field(..., min_length=6, max_length=120)

    def format_shipping_address(self) -> str:
        return self.shipping_address.to_formatted_string()

    def format_billing_address(self) -> str:
        if self.same_as_shipping or self.billing_address is None:
            return self.shipping_address.to_formatted_string()
        return self.billing_address.to_formatted_string()

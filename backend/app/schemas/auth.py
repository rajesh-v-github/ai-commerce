from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: Optional[str] = None
    full_name: Optional[str] = None


class CustomerRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=40)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=72)
    full_name: str = Field(..., min_length=2, max_length=100)
    phone: Optional[str] = Field(default=None, max_length=30)
    shipping_address: Optional[str] = Field(default=None, max_length=500)


class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(default=None, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=30)
    shipping_address: Optional[str] = Field(default=None, max_length=500)
    billing_address: Optional[str] = Field(default=None, max_length=500)

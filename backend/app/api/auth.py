from datetime import datetime
import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_support_user, get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.database.db import get_db
from app.models.user import User
from app.schemas.auth import (
    CustomerRegisterRequest,
    LoginRequest,
    LoginResponse,
    ProfileUpdateRequest,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _serialize_user_profile(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "full_name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "shipping_address": user.shipping_address,
        "billing_address": user.billing_address,
        "is_active": bool(True if user.is_active is None else user.is_active),
    }


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return _serialize_user_profile(current_user)


@router.put("/me")
def update_me(
    request: ProfileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if request.email is not None:
        normalized_email = request.email.strip().lower()
        conflict = (
            db.query(User)
            .filter(User.email.ilike(normalized_email), User.id != current_user.id)
            .first()
        )
        if conflict:
            raise HTTPException(
                status_code=409,
                detail="That email address is already linked to another account.",
            )
        current_user.email = normalized_email

    if request.full_name is not None:
        current_user.full_name = request.full_name.strip() or current_user.full_name
    if request.phone is not None:
        current_user.phone = request.phone.strip() or None
    if request.shipping_address is not None:
        current_user.shipping_address = request.shipping_address.strip() or None
    if request.billing_address is not None:
        current_user.billing_address = request.billing_address.strip() or None

    db.commit()
    db.refresh(current_user)
    return _serialize_user_profile(current_user)


@router.get("/support-test")
def support_test(current_user: User = Depends(get_current_support_user)):
    return {"message": "Support access granted", "user": current_user.username}


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    identifier = request.username.strip()
    user = (
        db.query(User)
        .filter(
            or_(
                User.username == identifier,
                User.email.ilike(identifier),
            )
        )
        .first()
    )

    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if getattr(user, "is_active", True) is False:
        raise HTTPException(status_code=403, detail="This account has been deactivated")

    if not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token({"sub": user.username, "role": user.role})

    return LoginResponse(
        access_token=token,
        role=user.role,
        username=user.username,
        full_name=user.full_name,
    )


@router.post("/register", response_model=LoginResponse)
def register_customer(request: CustomerRegisterRequest, db: Session = Depends(get_db)):
    """Public registration strictly provisions role='customer' accounts only."""
    username = request.username.strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,40}", username):
        raise HTTPException(
            status_code=422,
            detail="Username must be 3-40 characters using letters, numbers, dots, underscores, or hyphens.",
        )

    email = request.email.strip().lower()

    existing_email_user = db.query(User).filter(User.email.ilike(email)).first()
    if existing_email_user and existing_email_user.password_hash:
        raise HTTPException(
            status_code=409,
            detail="An account with this email address already exists.",
        )

    existing_username_user = db.query(User).filter(User.username == username).first()
    if existing_username_user and (
        existing_email_user is None or existing_username_user.id != existing_email_user.id
    ):
        raise HTTPException(
            status_code=409,
            detail="That username is already taken.",
        )

    hashed = hash_password(request.password)

    # Upgrade prior guest customer record if matching email exists without password
    if existing_email_user and not existing_email_user.password_hash:
        existing_email_user.username = username
        existing_email_user.password_hash = hashed
        existing_email_user.role = "customer"
        existing_email_user.full_name = request.full_name.strip()
        existing_email_user.phone = (request.phone or "").strip() or existing_email_user.phone
        existing_email_user.shipping_address = (
            (request.shipping_address or "").strip() or existing_email_user.shipping_address
        )
        existing_email_user.is_active = True
        user = existing_email_user
    else:
        user = User(
            username=username,
            password_hash=hashed,
            role="customer",
            full_name=request.full_name.strip(),
            email=email,
            phone=(request.phone or "").strip() or None,
            shipping_address=(request.shipping_address or "").strip() or None,
            is_active=True,
            created_at=datetime.utcnow(),
        )
        db.add(user)

    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.username, "role": user.role})
    return LoginResponse(
        access_token=token,
        role=user.role,
        username=user.username,
        full_name=user.full_name,
    )

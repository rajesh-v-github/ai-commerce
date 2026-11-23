from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest
from app.schemas.auth import LoginResponse
from app.core.security import verify_password
from app.core.security import create_access_token

from app.api.dependencies import get_current_user, get_current_support_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "role": current_user.role,
    }


@router.get("/support-test")
def support_test(current_user: User = Depends(get_current_support_user)):
    return {"message": "Support access granted", "user": current_user.username}


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.username == request.username).first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token({"sub": user.username, "role": user.role})

    return LoginResponse(access_token=token, role=user.role)

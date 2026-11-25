from typing import Optional

from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.db import get_db
from app.models.user import User

optional_security = HTTPBearer(auto_error=False)


def _extract_raw_token(
    credentials: Optional[HTTPAuthorizationCredentials],
    x_auth_token: Optional[str],
) -> Optional[str]:
    if x_auth_token and x_auth_token.strip():
        cleaned = x_auth_token.strip()
        if cleaned.lower().startswith("bearer "):
            cleaned = cleaned[7:].strip()
        if cleaned and cleaned not in {"null", "undefined"}:
            return cleaned
    if credentials and credentials.credentials:
        cleaned = credentials.credentials.strip()
        if cleaned and cleaned not in {"null", "undefined"}:
            return cleaned
    return None


def _decode_user_from_token(token: str, db: Session) -> User:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if getattr(user, "is_active", True) is False:
        raise HTTPException(status_code=403, detail="Account is deactivated")
    return user


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
    db: Session = Depends(get_db),
) -> User:
    token = _extract_raw_token(credentials, x_auth_token)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return _decode_user_from_token(token, db)


def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
    db: Session = Depends(get_db),
) -> Optional[User]:
    token = _extract_raw_token(credentials, x_auth_token)
    if not token:
        return None
    return _decode_user_from_token(token, db)


def get_current_support_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != "support":
        raise HTTPException(status_code=403, detail="Support access required")
    return current_user

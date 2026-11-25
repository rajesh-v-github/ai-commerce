import argparse
import getpass
import os
import re
import sys

from app.core.security import hash_password
from app.database.db import SessionLocal
from app.models.user import User


def validate_executive_password(password: str) -> None:
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter.")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter.")
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit.")
    if not re.search(r"[^A-Za-z0-9]", password):
        raise ValueError("Password must contain at least one special character.")


def provision_executive(
    username: str,
    password: str,
    email: str | None = None,
    full_name: str | None = None,
    update_existing_password: bool = False,
) -> User:
    username = username.strip()
    if not username or len(username) < 3:
        raise ValueError("Username must be at least 3 characters long.")

    validate_executive_password(password)

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            if existing.role != "support":
                raise RuntimeError(
                    f"User '{username}' already exists with role '{existing.role}'. "
                    "Refusing to elevate a non-support account automatically."
                )
            if update_existing_password:
                existing.password_hash = hash_password(password)
            if email:
                existing.email = email.strip().lower()
            if full_name:
                existing.full_name = full_name.strip()
            existing.is_active = True
            db.commit()
            db.refresh(existing)
            return existing

        user = User(
            username=username,
            password_hash=hash_password(password),
            role="support",
            email=email.strip().lower() if email else None,
            full_name=full_name.strip() if full_name else f"Executive ({username})",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Securely provision or update a Support/Admin Executive account."
    )
    parser.add_argument(
        "--username",
        default=os.environ.get("EXECUTIVE_USERNAME", ""),
        help="Executive username (or set EXECUTIVE_USERNAME env var).",
    )
    parser.add_argument(
        "--email",
        default=os.environ.get("EXECUTIVE_EMAIL", ""),
        help="Optional executive email address.",
    )
    parser.add_argument(
        "--full-name",
        default=os.environ.get("EXECUTIVE_FULL_NAME", ""),
        help="Optional executive full name.",
    )
    parser.add_argument(
        "--update-password",
        action="store_true",
        help="Update password if the support executive account already exists.",
    )
    args = parser.parse_args()

    username = args.username.strip()
    if not username:
        username = input("Executive username: ").strip()

    password = os.environ.get("EXECUTIVE_PASSWORD", "")
    if not password:
        password = getpass.getpass("Executive password: ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("Error: Passwords do not match.", file=sys.stderr)
            sys.exit(1)

    try:
        user = provision_executive(
            username=username,
            password=password,
            email=args.email or None,
            full_name=args.full_name or None,
            update_existing_password=args.update_password,
        )
        print(
            f"Executive account '{user.username}' (id={user.id}, role={user.role}) "
            "is ready."
        )
    except Exception as exc:
        print(f"Error provisioning executive account: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

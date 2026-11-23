from passlib.context import CryptContext

from app.database.db import SessionLocal
from app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def seed_users():
    db = SessionLocal()

    users = [
        {
            "username": "customer1",
            "password": "Password123!",
            "role": "customer",
        },
        {
            "username": "customer2",
            "password": "Password123!",
            "role": "customer",
        },
        {
            "username": "customer3",
            "password": "Password123!",
            "role": "customer",
        },
        {
            "username": "customer4",
            "password": "Password123!",
            "role": "customer",
        },
        {
            "username": "customer5",
            "password": "Password123!",
            "role": "customer",
        },
        {
            "username": "customer6",
            "password": "Password123!",
            "role": "customer",
        },
        {
            "username": "customer7",
            "password": "Password123!",
            "role": "customer",
        },
        {
            "username": "customer8",
            "password": "Password123!",
            "role": "customer",
        },
        {
            "username": "customer9",
            "password": "Password123!",
            "role": "customer",
        },
        {
            "username": "customer10",
            "password": "Password123!",
            "role": "customer",
        },
        {
            "username": "support1",
            "password": "Password123!",
            "role": "support",
        },
    ]

    for user_data in users:
        existing = db.query(User).filter(User.username == user_data["username"]).first()

        if not existing:
            user = User(
                username=user_data["username"],
                password_hash=hash_password(user_data["password"]),
                role=user_data["role"],
            )
            db.add(user)
            print(f"Created user: {user.username}")
        else:
            print(f"User already exists: {existing.username}")

    db.commit()
    db.close()


if __name__ == "__main__":
    seed_users()

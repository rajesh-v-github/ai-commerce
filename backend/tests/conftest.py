from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token, hash_password
from app.database.db import Base, get_db
from app.main import app
from app.models.product import Product
from app.models.ticket import Ticket
from app.models.user import User


@pytest.fixture
def api_env(tmp_path, monkeypatch):
    """Isolated FastAPI TestClient + SQLite test database with seeded roles and products."""
    monkeypatch.setattr("app.core.config.settings.UPLOAD_DIR", str(tmp_path / "uploads"))

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    support_user = User(
        username="exec_support",
        password_hash=hash_password("SupportPass123!"),
        role="support",
        full_name="Support Executive",
        email="exec@example.com",
        phone="+919999900001",
        is_active=True,
    )
    customer_user = User(
        username="aarav_cust",
        password_hash=hash_password("CustomerPass123!"),
        role="customer",
        full_name="Aarav Sharma",
        email="aarav@example.com",
        phone="+919999900002",
        shipping_address="Plot 10, HITEC City, Hyderabad, Telangana 500081, India",
        is_active=True,
    )
    other_customer = User(
        username="meera_cust",
        password_hash=hash_password("CustomerPass123!"),
        role="customer",
        full_name="Meera Patel",
        email="meera@example.com",
        phone="+919999900003",
        is_active=True,
    )
    db.add_all([support_user, customer_user, other_customer])
    db.flush()

    p1 = Product(
        name="Wireless Earbuds",
        description="Compact ANC Bluetooth 5.3 wireless earbuds.",
        category="Audio",
        brand="SoranoSound",
        sku="SG-AUD-001",
        price=Decimal("2499.00"),
        stock=12,
        low_stock_threshold=5,
        is_active=True,
        image_url="/product-images/wireless-earbuds.jpg",
    )
    p2 = Product(
        name="Mechanical Keyboard",
        description="Tactile RGB hot-swappable mechanical keyboard.",
        category="Gaming Accessories",
        brand="SoranoForge",
        sku="SG-GAM-002",
        price=Decimal("3499.00"),
        stock=3,
        low_stock_threshold=5,
        is_active=True,
        image_url="/product-images/mechanical-keyboard.jpg",
    )
    p3 = Product(
        name="Gaming Laptop X",
        description="High-refresh QHD gaming laptop.",
        category="Laptops",
        brand="SoranoBook",
        sku="SG-LAP-003",
        price=Decimal("79999.00"),
        stock=0,
        low_stock_threshold=3,
        is_active=True,
        image_url="/product-images/gaming-laptop-x.svg",
    )
    p4 = Product(
        name="Archived Adapter",
        description="Discontinued legacy adapter.",
        category="Computer Accessories",
        brand="SoranoLink",
        sku="SG-ACC-004",
        price=Decimal("799.00"),
        stock=10,
        low_stock_threshold=5,
        is_active=False,
        image_url="/product-images/usb-c-hub.jpg",
    )
    db.add_all([p1, p2, p3, p4])
    db.flush()

    t1 = Ticket(
        ticket_number="TKT-001",
        user_id=customer_user.id,
        subject="Earbuds pairing question",
        description="Need help pairing Wireless Earbuds with laptop.",
        status="OPEN",
        priority="MEDIUM",
    )
    db.add(t1)
    db.commit()

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db

    support_token = create_access_token(
        {"sub": support_user.username, "role": "support", "uid": support_user.id}
    )
    customer_token = create_access_token(
        {"sub": customer_user.username, "role": "customer", "uid": customer_user.id}
    )
    other_customer_token = create_access_token(
        {"sub": other_customer.username, "role": "customer", "uid": other_customer.id}
    )

    with TestClient(app) as client:
        yield {
            "client": client,
            "db_factory": TestingSessionLocal,
            "support_user": support_user,
            "customer_user": customer_user,
            "other_customer": other_customer,
            "support_headers": {"Authorization": f"Bearer {support_token}"},
            "customer_headers": {"Authorization": f"Bearer {customer_token}"},
            "other_customer_headers": {"Authorization": f"Bearer {other_customer_token}"},
            "products": {"earbuds": p1, "keyboard": p2, "laptop_oos": p3, "inactive": p4},
        }

    app.dependency_overrides.pop(get_db, None)
    db.close()
    engine.dispose()

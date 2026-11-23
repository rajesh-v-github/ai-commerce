from fastapi import FastAPI

from app.database.db import Base, engine
from app.database.migrations import ensure_ticket_number_column

# Import models
from app.models.product import Product

from app.api.health import router as health_router
from app.api.products import router as product_router
from app.api.orders import router as order_router
from app.api.auth import router as auth_router
from app.api.tickets import router as ticket_router
from app.api.dashboard import router as dashboard_router
from app.api.copilot import router as copilot_router
from app.api.customer import router as customer_router

from fastapi.middleware.cors import CORSMiddleware

# Create tables
Base.metadata.create_all(bind=engine)
ensure_ticket_number_column(engine)

app = FastAPI(title="AI Commerce Support")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
app.include_router(product_router, prefix="/api")
app.include_router(order_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(ticket_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(copilot_router, prefix="/api")
app.include_router(customer_router, prefix="/api")

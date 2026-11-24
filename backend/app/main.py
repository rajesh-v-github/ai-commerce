from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.copilot import router as copilot_router
from app.api.customer import router as customer_router
from app.api.dashboard import router as dashboard_router
from app.api.health import router as health_router
from app.api.orders import router as order_router
from app.api.products import router as product_router
from app.api.store import router as store_router
from app.api.tickets import router as ticket_router
from app.core.config import settings


def _build_cors_origins() -> list[str]:
    configured = [
        origin.strip()
        for origin in (settings.CORS_ORIGINS or "").split(",")
        if origin.strip()
    ]
    defaults = ["http://localhost:5173", "http://127.0.0.1:5173"]
    merged: list[str] = []
    for origin in [*configured, *defaults]:
        if origin not in merged:
            merged.append(origin)
    return merged


app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_build_cors_origins(),
    allow_origin_regex=r"https://.*\.e2b\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

uploads_path = Path(settings.UPLOAD_DIR).resolve()
uploads_path.mkdir(parents=True, exist_ok=True)
app.mount("/api/uploads", StaticFiles(directory=str(uploads_path)), name="uploads")


@app.get("/", tags=["Health"])
def api_root():
    return {
        "service": settings.APP_NAME,
        "status": "ok",
        "docs": "/docs",
    }


app.include_router(health_router, prefix="/api")
app.include_router(product_router, prefix="/api")
app.include_router(order_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(ticket_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(copilot_router, prefix="/api")
app.include_router(customer_router, prefix="/api")
app.include_router(store_router, prefix="/api")
app.include_router(admin_router, prefix="/api")

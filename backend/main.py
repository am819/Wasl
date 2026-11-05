"""
WASL FastAPI application entry point.
"""

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import check_db_connection
import models  # noqa: F401 — register all ORM models with Base.metadata
from routers import auth as auth_router
from routers import merchants as merchants_router
from security.permissions import require_admin, require_driver, require_merchant

app = FastAPI(
    title="WASL API",
    description=(
        "B2B last-mile delivery management platform "
        "for merchants in Alexandria, Egypt."
    ),
    version="0.1.0",
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url="/redoc" if settings.docs_enabled else None,
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth_router.router)
app.include_router(merchants_router.router)

# ---------------------------------------------------------------------------
# Health check (public)
# ---------------------------------------------------------------------------


@app.get("/health", tags=["system"])
def health():
    """Returns the application status and database connectivity."""
    db_ok = check_db_connection()
    return {
        "status": "ok" if db_ok else "degraded",
        "environment": settings.environment,
        "database": "connected" if db_ok else "unreachable",
    }


# ---------------------------------------------------------------------------
# Role-guarded stub endpoints (Task 1.3 / 1.4 verification)
# ---------------------------------------------------------------------------


@app.get("/api/v1/merchants/me", tags=["merchants"])
def merchant_me(user=Depends(require_merchant)):
    """Merchant-only protected endpoint — verifies RBAC."""
    return {"success": True, "data": {"user_id": user.id, "role": user.role}}


@app.get("/api/v1/drivers/me", tags=["drivers"])
def driver_me(user=Depends(require_driver)):
    """Driver-only protected endpoint — verifies RBAC."""
    return {"success": True, "data": {"user_id": user.id, "role": user.role}}


@app.get("/api/v1/admin/me", tags=["admin"])
def admin_me(user=Depends(require_admin)):
    """Admin-only protected endpoint — verifies RBAC."""
    return {"success": True, "data": {"user_id": user.id, "role": user.role}}

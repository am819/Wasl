"""
WASL FastAPI application entry point.

This is the skeleton for Phase 0. No business routes are registered yet.
Routes will be added in Phase 1 onwards (auth, merchants, drivers, admin).
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import check_db_connection

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
# Health check (public — no auth required)
# ---------------------------------------------------------------------------


@app.get("/health", tags=["system"])
def health():
    """
    Returns the application status and database connectivity.
    Used by deployment platforms and uptime monitors.
    """
    db_ok = check_db_connection()
    return {
        "status": "ok" if db_ok else "degraded",
        "environment": settings.environment,
        "database": "connected" if db_ok else "unreachable",
    }


# ---------------------------------------------------------------------------
# Routers — registered here as they are built in Phase 1+
# ---------------------------------------------------------------------------
# from routers import auth, merchants, drivers, admin, public
# app.include_router(auth.router,      prefix="/api/v1")
# app.include_router(merchants.router, prefix="/api/v1")
# app.include_router(drivers.router,   prefix="/api/v1")
# app.include_router(admin.router,     prefix="/api/v1")
# app.include_router(public.router,    prefix="/api/v1")

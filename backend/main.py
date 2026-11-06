"""
WASL FastAPI application entry point.

Middleware registration order matters in Starlette/FastAPI:
middleware is executed in REVERSE registration order (last-added = outermost).

Desired request pipeline (outermost → innermost):
  CORSMiddleware          — must be outermost so preflight OPTIONS are answered
                            before any other middleware touches the request
  add_security_headers    — adds response headers
  SlowAPIMiddleware       — rate limiting (OPTIONS bypass handled below)
  route handler / auth

To get CORSMiddleware outermost we add it LAST (Starlette reverses order).
"""

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from config import settings
from database import check_db_connection
import models  # noqa: F401 — register all ORM models with Base.metadata
from middleware.rate_limit import limiter
from routers import auth as auth_router
from routers import merchants as merchants_router
from routers import drivers as drivers_router
from routers import admin as admin_router
from routers import public as public_router
from security.permissions import require_admin, require_driver, require_merchant

logger = logging.getLogger(__name__)

# Compute the allowed origins list once at startup — used by both the
# lifespan log and the CORSMiddleware registration.
_allowed_origins = settings.allowed_origins_list()


@asynccontextmanager
async def lifespan(app_instance):
    """Log the parsed CORS origins at startup for easy verification."""
    logger.warning(
        "CORS allowed origins (%d): %s",
        len(_allowed_origins),
        _allowed_origins,
    )
    yield


app = FastAPI(
    title="WASL API",
    description=(
        "B2B last-mile delivery management platform "
        "for merchants in Alexandria, Egypt."
    ),
    version="0.1.0",
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url="/redoc" if settings.docs_enabled else None,
    lifespan=lifespan,
)

# Attach limiter state and error handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ---------------------------------------------------------------------------
# Middleware (added in INSIDE-OUT order — Starlette reverses on execution)
# ---------------------------------------------------------------------------

# 1. Rate limiting — innermost middleware layer
app.add_middleware(SlowAPIMiddleware)


# 2. Security headers — added as @app.middleware so it runs after CORS
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to every response.

    OPTIONS preflight requests pass through untouched so CORSMiddleware
    (outermost) can write the correct Access-Control-* headers.
    """
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains"
        )
    return response


# 3. CORS — must be OUTERMOST so it intercepts OPTIONS preflights first.
#    Added last so Starlette puts it at the front of the middleware stack.
#    allow_credentials=True requires explicit origins (never "*").
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth_router.router)
app.include_router(merchants_router.router)
app.include_router(drivers_router.router)
app.include_router(admin_router.router)
app.include_router(public_router.router)


# ---------------------------------------------------------------------------
# Health check (public — no auth, no rate limit decorator needed)
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
# Role-guarded stub endpoints (RBAC verification — Tasks 1.3 / 1.4)
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

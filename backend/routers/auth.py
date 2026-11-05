"""
Authentication router.

Endpoints:
  POST /api/v1/auth/register
  POST /api/v1/auth/login
  POST /api/v1/auth/refresh
  POST /api/v1/auth/logout
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from database import get_db
from middleware.rate_limit import AUTH_LIMIT, limiter
from schemas.auth_schema import (
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RefreshResponse,
    RegisterRequest,
    RegisterResponse,
)
from security.jwt_utils import ACCESS_TOKEN_EXPIRE_MINUTES
from security.permissions import get_current_user
from services.auth_service import AuthError, login, logout, refresh_tokens
from services.user_service import RegistrationError, register_user

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


# ---------------------------------------------------------------------------
# POST /api/v1/auth/register
# ---------------------------------------------------------------------------

@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=None,
    summary="Register a new merchant or driver",
)
@limiter.limit(AUTH_LIMIT)
def register(
    req: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        user = register_user(db, req)
    except RegistrationError as exc:
        raise HTTPException(status_code=exc.http_status, detail={
            "code": exc.code,
            "message": exc.message,
        })

    return {
        "success": True,
        "data": RegisterResponse(
            user_id=user.id,
            email=user.email,
            role=user.role,
            status=user.status,
        ).model_dump(),
        "error": None,
    }


# ---------------------------------------------------------------------------
# POST /api/v1/auth/login
# ---------------------------------------------------------------------------

@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    response_model=None,
    summary="Login and receive JWT tokens",
)
@limiter.limit(AUTH_LIMIT)
def login_endpoint(
    req: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        access_token, refresh_token = login(
            db,
            email=req.email,
            password=req.password,
            ip=_client_ip(request),
            ua=request.headers.get("User-Agent"),
        )
    except AuthError as exc:
        raise HTTPException(status_code=exc.http_status, detail={
            "code": exc.code,
            "message": exc.message,
        })

    # Load user for response (already in session cache)
    from models.user import User
    user = db.query(User).filter(User.email == req.email).first()

    return {
        "success": True,
        "data": LoginResponse(
            user_id=user.id,
            email=user.email,
            role=user.role,
            token=access_token,
            refresh_token=refresh_token,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        ).model_dump(),
        "error": None,
    }


# ---------------------------------------------------------------------------
# POST /api/v1/auth/refresh
# ---------------------------------------------------------------------------

@router.post(
    "/refresh",
    status_code=status.HTTP_200_OK,
    response_model=None,
    summary="Rotate refresh token",
)
@limiter.limit(AUTH_LIMIT)
def refresh_endpoint(
    req: RefreshRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        new_access, new_refresh = refresh_tokens(
            db,
            refresh_token_plain=req.refresh_token,
            ip=_client_ip(request),
            ua=request.headers.get("User-Agent"),
        )
    except AuthError as exc:
        raise HTTPException(status_code=exc.http_status, detail={
            "code": exc.code,
            "message": exc.message,
        })

    return {
        "success": True,
        "data": RefreshResponse(
            token=new_access,
            refresh_token=new_refresh,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        ).model_dump(),
        "error": None,
    }


# ---------------------------------------------------------------------------
# POST /api/v1/auth/logout
# ---------------------------------------------------------------------------

@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout and revoke refresh token",
)
def logout_endpoint(
    req: RefreshRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    logout(
        db,
        refresh_token_plain=req.refresh_token,
        user_id=current_user.id,
        ip=_client_ip(request),
        ua=request.headers.get("User-Agent"),
    )

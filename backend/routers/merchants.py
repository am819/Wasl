"""Merchant router — profile, orders, analytics."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from schemas.merchant_schema import MerchantRegisterRequest, MerchantUpdateRequest
from schemas.order_schema import OrderCreateRequest
from security.permissions import require_merchant
from services.merchant_service import (
    MerchantError,
    _merchant_to_dict,
    create_merchant_profile,
    require_merchant_profile,
    update_merchant_profile,
)
from services.order_service import (
    OrderError, create_order, get_order_detail, list_orders,
)

router = APIRouter(prefix="/api/v1/merchants", tags=["merchants"])


@router.post(
    "/profile",
    status_code=status.HTTP_201_CREATED,
    summary="Create merchant profile",
)
def create_profile(
    req: MerchantRegisterRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_merchant),
):
    try:
        merchant = create_merchant_profile(db, current_user, req)
    except MerchantError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": exc.message},
        )
    return {
        "success": True,
        "data": _merchant_to_dict(merchant, current_user.status),
    }


@router.get("/profile", summary="Get merchant profile")
def get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_merchant),
):
    try:
        merchant = require_merchant_profile(db, current_user.id)
    except MerchantError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": exc.message},
        )
    return {
        "success": True,
        "data": _merchant_to_dict(merchant, current_user.status),
    }


@router.put("/profile", summary="Update merchant profile")
def update_profile(
    req: MerchantUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_merchant),
):
    try:
        merchant = require_merchant_profile(db, current_user.id)
    except MerchantError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": exc.message},
        )
    updated = update_merchant_profile(db, merchant, req)
    return {
        "success": True,
        "data": _merchant_to_dict(updated, current_user.status),
    }


# ---------------------------------------------------------------------------
# Order endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/orders",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new delivery order",
)
def create_order_endpoint(
    req: OrderCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_merchant),
):
    try:
        merchant = require_merchant_profile(db, current_user.id)
        result = create_order(db, merchant, current_user, req)
    except (MerchantError, OrderError) as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": exc.message},
        )
    return {"success": True, "data": result}


@router.get("/orders", summary="List merchant orders")
def list_orders_endpoint(
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_merchant),
):
    try:
        merchant = require_merchant_profile(db, current_user.id)
    except MerchantError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": exc.message},
        )
    result = list_orders(db, merchant.id, status_filter, limit, offset)
    return {"success": True, "data": result}


@router.get("/orders/{order_id}", summary="Get order detail")
def get_order_endpoint(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_merchant),
):
    try:
        merchant = require_merchant_profile(db, current_user.id)
        result = get_order_detail(db, merchant.id, order_id)
    except MerchantError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": exc.message},
        )
    except OrderError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": exc.message},
        )
    return {"success": True, "data": result}


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

@router.get("/analytics", summary="Merchant analytics")
def get_analytics(
    period: str = Query("week", regex="^(today|week|month)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_merchant),
):
    from services.analytics_service import merchant_analytics
    from services.merchant_service import require_merchant_profile
    try:
        merchant = require_merchant_profile(db, current_user.id)
    except MerchantError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": exc.message},
        )
    result = merchant_analytics(db, merchant.id, period)
    return {"success": True, "data": result}

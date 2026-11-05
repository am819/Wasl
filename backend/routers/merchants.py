"""Merchant router — profile, orders, analytics."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from schemas.merchant_schema import MerchantRegisterRequest, MerchantUpdateRequest
from security.permissions import require_merchant
from services.merchant_service import (
    MerchantError,
    _merchant_to_dict,
    create_merchant_profile,
    require_merchant_profile,
    update_merchant_profile,
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

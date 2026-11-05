"""Driver router — profile, availability, tasks, earnings."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from schemas.driver_schema import DriverRegisterRequest, DriverUpdateRequest
from security.permissions import require_driver
from services.driver_service import (
    DriverError,
    _driver_to_dict,
    create_driver_profile,
    require_driver_profile,
    update_driver_profile,
)

router = APIRouter(prefix="/api/v1/drivers", tags=["drivers"])


@router.post(
    "/profile",
    status_code=status.HTTP_201_CREATED,
    summary="Create driver profile",
)
def create_driver_profile_endpoint(
    req: DriverRegisterRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_driver),
):
    try:
        driver = create_driver_profile(db, current_user, req)
    except DriverError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": exc.message},
        )
    return {
        "success": True,
        "data": _driver_to_dict(driver, current_user.status),
    }


@router.get("/profile", summary="Get driver profile")
def get_driver_profile_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_driver),
):
    try:
        driver = require_driver_profile(db, current_user.id)
    except DriverError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": exc.message},
        )
    return {
        "success": True,
        "data": _driver_to_dict(driver, current_user.status),
    }


@router.put("/profile", summary="Update driver profile")
def update_driver_profile_endpoint(
    req: DriverUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_driver),
):
    try:
        driver = require_driver_profile(db, current_user.id)
    except DriverError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": exc.message},
        )
    updated = update_driver_profile(db, driver, req)
    return {
        "success": True,
        "data": _driver_to_dict(updated, current_user.status),
    }

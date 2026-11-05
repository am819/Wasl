"""Driver router — profile, availability, tasks, earnings."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
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


# ---------------------------------------------------------------------------
# Availability
# ---------------------------------------------------------------------------

@router.post("/availability", summary="Toggle online/offline")
def toggle_availability(
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_driver),
):
    from services.driver_service import require_driver_profile
    try:
        driver = require_driver_profile(db, current_user.id)
    except DriverError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": exc.message},
        )
    if current_user.status != "approved":
        raise HTTPException(
            status_code=403,
            detail={
                "code": "DRIVER_NOT_APPROVED",
                "message": "Your account must be approved first",
            },
        )
    is_online = bool(body.get("is_online", False))
    driver.is_online = is_online
    db.commit()
    return {
        "success": True,
        "data": {
            "driver_id": driver.id,
            "is_online": is_online,
        },
    }


# ---------------------------------------------------------------------------
# Task Queue
# ---------------------------------------------------------------------------

@router.get("/tasks", summary="Get driver task queue")
def get_tasks(
    status_filter: str | None = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_driver),
):
    from services.assignment_service import get_driver_tasks
    from services.driver_service import require_driver_profile
    try:
        driver = require_driver_profile(db, current_user.id)
    except DriverError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": exc.message},
        )
    tasks = get_driver_tasks(db, driver.id, status_filter)
    return {"success": True, "data": {"tasks": tasks, "count": len(tasks)}}


# ---------------------------------------------------------------------------
# Accept / Reject
# ---------------------------------------------------------------------------

@router.post("/tasks/{order_id}/accept", summary="Accept a task")
def accept_task_endpoint(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_driver),
):
    from services.assignment_service import AssignmentError, accept_task
    from services.driver_service import require_driver_profile
    try:
        driver = require_driver_profile(db, current_user.id)
        result = accept_task(db, driver.id, order_id)
    except (DriverError, AssignmentError) as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": exc.message},
        )
    return {"success": True, "data": result}


@router.post("/tasks/{order_id}/reject", summary="Reject a task")
def reject_task_endpoint(
    order_id: int,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_driver),
):
    from services.assignment_service import AssignmentError, reject_task
    from services.driver_service import require_driver_profile
    try:
        driver = require_driver_profile(db, current_user.id)
        result = reject_task(
            db, driver.id, order_id,
            body.get("reason", "No reason provided"),
        )
    except (DriverError, AssignmentError) as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": exc.message},
        )
    return {"success": True, "data": result}


# ---------------------------------------------------------------------------
# Status Updates
# ---------------------------------------------------------------------------

@router.put("/tasks/{order_id}/status", summary="Update delivery status")
def update_status_endpoint(
    order_id: int,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_driver),
):
    from services.assignment_service import AssignmentError
    from services.assignment_service import update_delivery_status
    from services.driver_service import require_driver_profile
    try:
        driver = require_driver_profile(db, current_user.id)
        result = update_delivery_status(
            db, driver.id, order_id, body.get("status", "")
        )
    except (DriverError, AssignmentError) as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": exc.message},
        )
    return {"success": True, "data": result}


# ---------------------------------------------------------------------------
# Earnings
# ---------------------------------------------------------------------------

@router.get("/earnings", summary="Get driver earnings")
def get_earnings(
    period: str = Query("week", pattern="^(today|week|month)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_driver),
):
    from services.driver_service import require_driver_profile
    from sqlalchemy import func as sql_func
    from models.financial_transaction import FinancialTransaction

    try:
        driver = require_driver_profile(db, current_user.id)
    except DriverError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": exc.message},
        )

    total = (
        db.query(
            sql_func.count(FinancialTransaction.id),
            sql_func.sum(FinancialTransaction.amount_egp),
        )
        .filter(
            FinancialTransaction.transaction_type == "driver_payout",
            FinancialTransaction.related_driver_id == driver.id,
        )
        .first()
    )
    pending = (
        db.query(
            sql_func.sum(FinancialTransaction.amount_egp)
        )
        .filter(
            FinancialTransaction.transaction_type == "driver_payout",
            FinancialTransaction.related_driver_id == driver.id,
            FinancialTransaction.status == "pending",
        )
        .scalar()
    ) or 0

    order_count = total[0] or 0
    total_earnings = float(total[1] or 0)

    return {
        "success": True,
        "data": {
            "period": period,
            "total_earnings_egp": total_earnings,
            "order_count": order_count,
            "pending_payout_egp": float(pending),
        },
    }

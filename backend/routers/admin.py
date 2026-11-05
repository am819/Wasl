"""Admin router — approvals, assignments, analytics, settlements, audit."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from security.permissions import require_admin

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Merchant Management
# ---------------------------------------------------------------------------

@router.get("/merchants", summary="List merchants")
def list_merchants(
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    from models.merchant import Merchant

    q = db.query(Merchant, User).join(User, Merchant.user_id == User.id)
    if status_filter:
        q = q.filter(User.status == status_filter)

    total = q.count()
    results = q.order_by(Merchant.created_at.desc()).offset(offset).limit(limit).all()

    merchants = []
    for m, u in results:
        merchants.append({
            "id": m.id,
            "user_id": m.user_id,
            "business_name": m.business_name,
            "business_phone": m.business_phone,
            "address_line1": m.address_line1,
            "city": m.city,
            "contact_person_name": m.contact_person_name,
            "status": u.status,
            "created_at": m.created_at.isoformat(),
        })
    return {
        "success": True,
        "data": {"merchants": merchants, "total_count": total},
    }


@router.post(
    "/merchants/{merchant_id}/approve",
    summary="Approve a merchant",
)
def approve_merchant(
    merchant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    from datetime import datetime, timezone
    from models.audit_log import AuditLog
    from models.merchant import Merchant

    m = db.get(Merchant, merchant_id)
    if m is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "MERCHANT_NOT_FOUND", "message": "Merchant not found"},
        )
    u = db.get(User, m.user_id)
    u.status = "approved"
    m.approved_at = datetime.now(timezone.utc)

    log = AuditLog(
        user_id=current_user.id,
        action="approve_merchant",
        entity_type="merchant",
        entity_id=merchant_id,
        new_values={"status": "approved"},
    )
    db.add(log)
    db.commit()

    return {
        "success": True,
        "data": {"id": merchant_id, "status": "approved"},
    }


@router.post(
    "/merchants/{merchant_id}/reject",
    summary="Reject a merchant",
)
def reject_merchant(
    merchant_id: int,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    from models.audit_log import AuditLog
    from models.merchant import Merchant

    m = db.get(Merchant, merchant_id)
    if m is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "MERCHANT_NOT_FOUND", "message": "Merchant not found"},
        )
    u = db.get(User, m.user_id)
    u.status = "rejected"
    reason = body.get("rejection_reason", "")

    log = AuditLog(
        user_id=current_user.id,
        action="reject_merchant",
        entity_type="merchant",
        entity_id=merchant_id,
        new_values={"status": "rejected", "reason": reason},
    )
    db.add(log)
    db.commit()

    return {
        "success": True,
        "data": {"id": merchant_id, "status": "rejected"},
    }


# ---------------------------------------------------------------------------
# Driver Management
# ---------------------------------------------------------------------------

@router.get("/drivers", summary="List drivers")
def list_drivers(
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    from models.driver import Driver

    q = db.query(Driver, User).join(User, Driver.user_id == User.id)
    if status_filter:
        q = q.filter(User.status == status_filter)

    total = q.count()
    results = q.order_by(Driver.created_at.desc()).offset(offset).limit(limit).all()

    drivers = []
    for d, u in results:
        drivers.append({
            "id": d.id,
            "user_id": d.user_id,
            "full_name": d.full_name,
            "vehicle_type": d.vehicle_type,
            "vehicle_plate_number": d.vehicle_plate_number,
            "status": u.status,
            "created_at": d.created_at.isoformat(),
        })
    return {
        "success": True,
        "data": {"drivers": drivers, "total_count": total},
    }


@router.post("/drivers/{driver_id}/approve", summary="Approve a driver")
def approve_driver(
    driver_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    from datetime import datetime, timezone
    from models.audit_log import AuditLog
    from models.driver import Driver

    d = db.get(Driver, driver_id)
    if d is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "DRIVER_NOT_FOUND", "message": "Driver not found"},
        )
    u = db.get(User, d.user_id)
    u.status = "approved"
    d.approved_at = datetime.now(timezone.utc)

    log = AuditLog(
        user_id=current_user.id,
        action="approve_driver",
        entity_type="driver",
        entity_id=driver_id,
        new_values={"status": "approved"},
    )
    db.add(log)
    db.commit()
    return {"success": True, "data": {"id": driver_id, "status": "approved"}}


@router.post("/drivers/{driver_id}/reject", summary="Reject a driver")
def reject_driver(
    driver_id: int,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    from models.audit_log import AuditLog
    from models.driver import Driver

    d = db.get(Driver, driver_id)
    if d is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "DRIVER_NOT_FOUND", "message": "Driver not found"},
        )
    u = db.get(User, d.user_id)
    u.status = "rejected"
    reason = body.get("rejection_reason", "")

    log = AuditLog(
        user_id=current_user.id,
        action="reject_driver",
        entity_type="driver",
        entity_id=driver_id,
        new_values={"status": "rejected", "reason": reason},
    )
    db.add(log)
    db.commit()
    return {"success": True, "data": {"id": driver_id, "status": "rejected"}}


# ---------------------------------------------------------------------------
# Order Management — Manual Assignment
# ---------------------------------------------------------------------------

@router.get("/orders", summary="List all orders (platform-wide)")
def list_all_orders(
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    from models.order import Order

    q = db.query(Order)
    if status_filter:
        q = q.filter(Order.status == status_filter)
    total = q.count()
    orders = q.order_by(Order.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "success": True,
        "data": {
            "orders": [
                {
                    "id": o.id,
                    "order_number": o.order_number,
                    "merchant_id": o.merchant_id,
                    "status": o.status,
                    "total_egp": float(o.total_egp),
                    "assigned_driver_id": o.assigned_driver_id,
                    "created_at": o.created_at.isoformat(),
                }
                for o in orders
            ],
            "total_count": total,
        },
    }


@router.post("/orders/{order_id}/assign", summary="Assign order to driver")
def assign_order(
    order_id: int,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    from models.audit_log import AuditLog
    from models.driver import Driver
    from models.driver_assignment import DriverAssignment
    from models.order import Order
    from models.order_status_history import OrderStatusHistory

    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "ORDER_NOT_FOUND", "message": "Order not found"},
        )
    driver_id = body.get("driver_id")
    driver = db.get(Driver, driver_id)
    if driver is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "DRIVER_NOT_FOUND", "message": "Driver not found"},
        )
    u = db.get(User, driver.user_id)
    if u.status != "approved":
        raise HTTPException(
            status_code=403,
            detail={"code": "DRIVER_NOT_APPROVED",
                    "message": "Driver is not approved"},
        )

    old_status = order.status
    order.assigned_driver_id = driver_id
    order.status = "assigned"

    assignment = DriverAssignment(
        order_id=order_id,
        driver_id=driver_id,
        assigned_by_user_id=current_user.id,
        assignment_status="assigned",
    )
    db.add(assignment)

    history = OrderStatusHistory(
        order_id=order_id,
        previous_status=old_status,
        new_status="assigned",
        changed_by_user_id=current_user.id,
    )
    db.add(history)

    log = AuditLog(
        user_id=current_user.id,
        action="assign_driver",
        entity_type="order",
        entity_id=order_id,
        new_values={"driver_id": driver_id},
    )
    db.add(log)
    db.commit()
    return {
        "success": True,
        "data": {
            "order_id": order_id,
            "status": "assigned",
            "driver_id": driver_id,
        },
    }


@router.post("/orders/{order_id}/reassign", summary="Reassign order")
def reassign_order(
    order_id: int,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    from models.audit_log import AuditLog
    from models.driver_assignment import DriverAssignment
    from models.order import Order

    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail={"code": "ORDER_NOT_FOUND"})

    new_driver_id = body.get("driver_id")
    reason = body.get("reason", "Reassigned by admin")

    old_assignment = (
        db.query(DriverAssignment)
        .filter(
            DriverAssignment.order_id == order_id,
            DriverAssignment.assignment_status == "assigned",
        )
        .first()
    )
    if old_assignment:
        old_assignment.assignment_status = "cancelled"

    order.assigned_driver_id = new_driver_id
    new_assignment = DriverAssignment(
        order_id=order_id,
        driver_id=new_driver_id,
        assigned_by_user_id=current_user.id,
        assignment_status="assigned",
    )
    db.add(new_assignment)

    log = AuditLog(
        user_id=current_user.id,
        action="reassign_driver",
        entity_type="order",
        entity_id=order_id,
        new_values={"driver_id": new_driver_id, "reason": reason},
    )
    db.add(log)
    db.commit()
    return {"success": True, "data": {"order_id": order_id, "driver_id": new_driver_id}}


# ---------------------------------------------------------------------------
# Settlements (Task 4.5)
# Roadmap: admin creates a settlement_record for a driver or merchant
# for a date range, total = sum of matching financial_transactions.
# POST /admin/settlements/{id}/process marks the record completed.
# ---------------------------------------------------------------------------

@router.get("/settlements", summary="List settlement records")
def list_settlements(
    status_filter: str | None = Query(None, alias="status"),
    settlement_type: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    from models.settlement_record import SettlementRecord

    q = db.query(SettlementRecord)
    if status_filter:
        q = q.filter(SettlementRecord.status == status_filter)
    if settlement_type:
        q = q.filter(SettlementRecord.settlement_type == settlement_type)

    records = q.order_by(SettlementRecord.created_at.desc()).all()
    return {
        "success": True,
        "data": {
            "settlements": [
                {
                    "id": r.id,
                    "settlement_type": r.settlement_type,
                    "recipient_id": r.recipient_id,
                    "period_start": str(r.period_start),
                    "period_end": str(r.period_end),
                    "total_amount_egp": float(r.total_amount_egp),
                    "status": r.status,
                    "created_at": r.created_at.isoformat(),
                }
                for r in records
            ],
            "total_count": len(records),
        },
    }


@router.post("/settlements", summary="Create a settlement record")
def create_settlement(
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    from services.settlement_service import SettlementError, create_settlement
    from datetime import date

    try:
        settlement_type = body["settlement_type"]
        recipient_id = body["recipient_id"]
        period_start = date.fromisoformat(body["period_start"])
        period_end = date.fromisoformat(body["period_end"])
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": "VALIDATION_ERROR", "message": str(exc)},
        )

    try:
        record = create_settlement(
            db,
            settlement_type=settlement_type,
            recipient_id=recipient_id,
            period_start=period_start,
            period_end=period_end,
            created_by_user_id=current_user.id,
        )
    except SettlementError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": exc.message},
        )

    return {
        "success": True,
        "data": {
            "id": record.id,
            "settlement_type": record.settlement_type,
            "recipient_id": record.recipient_id,
            "period_start": str(record.period_start),
            "period_end": str(record.period_end),
            "total_amount_egp": float(record.total_amount_egp),
            "status": record.status,
        },
    }


@router.post(
    "/settlements/{settlement_id}/process",
    summary="Process (complete) a settlement record",
)
def process_settlement(
    settlement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    from services.settlement_service import SettlementError, process_settlement

    try:
        record = process_settlement(db, settlement_id, current_user.id)
    except SettlementError as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": exc.message},
        )

    return {
        "success": True,
        "data": {
            "id": record.id,
            "status": record.status,
            "total_amount_egp": float(record.total_amount_egp),
            "processed_at": (
                record.processed_at.isoformat()
                if record.processed_at
                else None
            ),
        },
    }


# ---------------------------------------------------------------------------
# Platform Analytics
# ---------------------------------------------------------------------------

@router.get("/analytics", summary="Platform-wide analytics")
def platform_analytics(
    period: str = Query("week", pattern="^(today|week|month)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    from models.driver import Driver
    from models.merchant import Merchant
    from models.order import Order
    from datetime import datetime, timedelta, timezone

    delta_map = {"today": 1, "week": 7, "month": 30}
    days = delta_map.get(period, 7)
    since = datetime.now(timezone.utc) - timedelta(days=days)

    total_orders = db.query(Order).filter(Order.created_at >= since).count()
    delivered = db.query(Order).filter(
        Order.status == "delivered", Order.created_at >= since
    ).count()
    cancelled = db.query(Order).filter(
        Order.status == "cancelled", Order.created_at >= since
    ).count()
    active_merchants = db.query(Merchant).count()
    active_drivers = db.query(Driver).filter(Driver.is_online.is_(True)).count()
    completion_rate = delivered / total_orders if total_orders > 0 else 0

    return {
        "success": True,
        "data": {
            "period": period,
            "total_orders": total_orders,
            "delivered_orders": delivered,
            "cancelled_orders": cancelled,
            "active_merchants": active_merchants,
            "active_drivers": active_drivers,
            "completion_rate": round(completion_rate, 3),
        },
    }


# ---------------------------------------------------------------------------
# Audit Logs
# ---------------------------------------------------------------------------

@router.get("/audit-logs", summary="View audit logs")
def list_audit_logs(
    user_id: int | None = Query(None),
    action: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    from models.audit_log import AuditLog

    q = db.query(AuditLog)
    if user_id:
        q = q.filter(AuditLog.user_id == user_id)
    if action:
        q = q.filter(AuditLog.action == action)

    total = q.count()
    logs = q.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "success": True,
        "data": {
            "logs": [
                {
                    "id": log_entry.id,
                    "user_id": log_entry.user_id,
                    "action": log_entry.action,
                    "entity_type": log_entry.entity_type,
                    "entity_id": log_entry.entity_id,
                    "created_at": log_entry.created_at.isoformat(),
                }
                for log_entry in logs
            ],
            "total_count": total,
        },
    }

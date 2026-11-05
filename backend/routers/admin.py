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

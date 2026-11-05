"""Public tracking router — no authentication required."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db

router = APIRouter(prefix="/api/v1/tracking", tags=["public"])


@router.get("/{token}", summary="Track an order by tracking token")
def track_order(token: str, db: Session = Depends(get_db)):
    from models.tracking_token import TrackingToken
    from models.order import Order
    from models.driver import Driver

    tt = (
        db.query(TrackingToken)
        .filter(TrackingToken.token == token)
        .first()
    )
    if tt is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "TRACKING_TOKEN_INVALID",
                    "message": "This tracking link is no longer valid"},
        )
    # Check expiry
    if tt.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=404,
            detail={"code": "TRACKING_TOKEN_INVALID",
                    "message": "This tracking link has expired"},
        )

    # Increment access count
    tt.access_count += 1
    tt.accessed_at = datetime.now(timezone.utc)

    order = db.get(Order, tt.order_id)
    if order is None:
        raise HTTPException(status_code=404, detail={"code": "TRACKING_TOKEN_INVALID"})

    # Get driver first name only (no phone, no full name)
    driver_first_name = None
    if order.assigned_driver_id:
        d = db.get(Driver, order.assigned_driver_id)
        if d:
            driver_first_name = d.full_name.split()[0] if d.full_name else None

    db.commit()

    # Return ONLY public-safe data — no phone, no merchant details,
    # no financial amounts, no internal IDs
    return {
        "success": True,
        "data": {
            "order_number": order.order_number,
            "status": order.status,
            "customer_name": order.customer_name,
            "delivery_address_line1": order.delivery_address_line1,
            "driver_first_name": driver_first_name,
            "estimated_delivery_at": (
                order.estimated_delivery_at.isoformat()
                if order.estimated_delivery_at
                else None
            ),
            "actual_delivery_at": (
                order.actual_delivery_at.isoformat()
                if order.actual_delivery_at
                else None
            ),
        },
    }

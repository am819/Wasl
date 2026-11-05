"""Order creation and management service."""

import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from config import settings
from models.merchant import Merchant
from models.order import Order
from models.order_item import OrderItem
from models.order_status_history import OrderStatusHistory
from models.tracking_token import TrackingToken
from models.user import User
from schemas.order_schema import OrderCreateRequest

TRACKING_TOKEN_EXPIRY_DAYS = 7


class OrderError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400):
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


def _generate_order_number(db: Session) -> str:
    """Generate WAS-YYYYMMDD-NNN, sequential within the current day.

    If two concurrent requests generate the same number, the DB UNIQUE
    constraint will reject the insert.  The caller (create_order) wraps
    the entire creation in a retry loop to handle this.
    """
    today_prefix = datetime.now(timezone.utc).strftime("WAS-%Y%m%d-")
    count = (
        db.query(Order)
        .filter(Order.order_number.like(f"{today_prefix}%"))
        .count()
    )
    return f"{today_prefix}{count + 1:03d}"


def create_order(
    db: Session,
    merchant: Merchant,
    user: User,
    req: OrderCreateRequest,
) -> dict:
    """Create an order with items, status history, and tracking token.

    Returns a dict suitable for the API response.
    """
    # Merchant must be approved to create orders
    if user.status != "approved":
        raise OrderError(
            code="MERCHANT_NOT_APPROVED",
            message="Your account must be approved before creating orders",
            http_status=403,
        )

    # Calculate totals
    subtotal = sum(
        item.quantity * item.unit_price_egp for item in req.items
    )
    delivery_fee = Decimal(str(settings.delivery_fee_egp))
    total = subtotal + delivery_fee

    # Generate order number and create order — retry on unique
    # constraint violation (handles concurrent requests generating
    # the same sequential order_number on the same day)
    from sqlalchemy.exc import IntegrityError

    MAX_RETRIES = 3
    for attempt in range(MAX_RETRIES):
        order_number = _generate_order_number(db)
        order = Order(
            merchant_id=merchant.id,
            order_number=order_number,
            customer_name=req.customer_name,
            customer_phone=req.customer_phone,
            customer_email=req.customer_email,
            pickup_address_line1=req.pickup_address_line1,
            pickup_address_line2=req.pickup_address_line2,
            delivery_address_line1=req.delivery_address_line1,
            delivery_address_line2=req.delivery_address_line2,
            delivery_notes=req.delivery_notes,
            subtotal_egp=subtotal,
            delivery_fee_egp=delivery_fee,
            total_egp=total,
            status="pending",
        )
        db.add(order)
        try:
            db.flush()  # get order.id, check unique constraint
            break
        except IntegrityError:
            db.rollback()
            if attempt == MAX_RETRIES - 1:
                raise OrderError(
                    code="INTERNAL_ERROR",
                    message="Failed to generate unique order number",
                    http_status=500,
                )

    # Create order items
    for item in req.items:
        oi = OrderItem(
            order_id=order.id,
            item_name=item.item_name,
            quantity=item.quantity,
            unit_price_egp=item.unit_price_egp,
            subtotal_egp=item.quantity * item.unit_price_egp,
        )
        db.add(oi)

    # Create initial status history
    history = OrderStatusHistory(
        order_id=order.id,
        previous_status=None,
        new_status="pending",
        changed_by_user_id=user.id,
    )
    db.add(history)

    # Create tracking token
    token = secrets.token_urlsafe(32)
    tracking = TrackingToken(
        order_id=order.id,
        token=token,
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=TRACKING_TOKEN_EXPIRY_DAYS),
    )
    db.add(tracking)

    db.commit()
    db.refresh(order)

    return {
        "order_id": order.id,
        "order_number": order.order_number,
        "status": order.status,
        "subtotal_egp": float(order.subtotal_egp),
        "delivery_fee_egp": float(order.delivery_fee_egp),
        "total_egp": float(order.total_egp),
        "tracking_token": token,
        "tracking_link": f"/tracking/{token}",
        "created_at": order.created_at.isoformat(),
    }


def list_orders(
    db: Session,
    merchant_id: int,
    status_filter: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """Return paginated list of orders for a merchant."""
    limit = min(max(limit, 1), 100)
    offset = max(offset, 0)

    q = db.query(Order).filter(Order.merchant_id == merchant_id)
    if status_filter:
        q = q.filter(Order.status == status_filter)

    total = q.count()
    orders = q.order_by(Order.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "orders": [
            {
                "id": o.id,
                "order_number": o.order_number,
                "customer_name": o.customer_name,
                "status": o.status,
                "total_egp": float(o.total_egp),
                "created_at": o.created_at.isoformat(),
            }
            for o in orders
        ],
        "total_count": total,
        "limit": limit,
        "offset": offset,
    }


def get_order_detail(
    db: Session, merchant_id: int, order_id: int
) -> dict:
    """Return order detail including items, history, and driver info.

    If the order does not belong to this merchant, return 403 (not 404).
    """
    order = db.get(Order, order_id)
    if order is None:
        raise OrderError(
            code="ORDER_NOT_FOUND",
            message="Order not found",
            http_status=404,
        )
    if order.merchant_id != merchant_id:
        raise OrderError(
            code="FORBIDDEN",
            message="You do not have access to this order",
            http_status=403,
        )

    items = (
        db.query(OrderItem)
        .filter(OrderItem.order_id == order_id)
        .all()
    )
    history = (
        db.query(OrderStatusHistory)
        .filter(OrderStatusHistory.order_id == order_id)
        .order_by(OrderStatusHistory.created_at.asc())
        .all()
    )

    # Get driver info if assigned
    from models.driver import Driver
    driver = None
    if order.assigned_driver_id:
        d = db.get(Driver, order.assigned_driver_id)
        if d:
            driver = {
                "full_name": d.full_name,
                "vehicle_type": d.vehicle_type,
            }

    return {
        "order": {
            "id": order.id,
            "order_number": order.order_number,
            "customer_name": order.customer_name,
            "customer_phone": order.customer_phone,
            "pickup_address_line1": order.pickup_address_line1,
            "delivery_address_line1": order.delivery_address_line1,
            "status": order.status,
            "subtotal_egp": float(order.subtotal_egp),
            "delivery_fee_egp": float(order.delivery_fee_egp),
            "total_egp": float(order.total_egp),
            "created_at": order.created_at.isoformat(),
        },
        "items": [
            {
                "id": i.id,
                "item_name": i.item_name,
                "quantity": i.quantity,
                "unit_price_egp": float(i.unit_price_egp),
                "subtotal_egp": float(i.subtotal_egp),
            }
            for i in items
        ],
        "status_history": [
            {
                "id": h.id,
                "previous_status": h.previous_status,
                "new_status": h.new_status,
                "reason": h.reason,
                "created_at": h.created_at.isoformat(),
            }
            for h in history
        ],
        "driver": driver,
    }

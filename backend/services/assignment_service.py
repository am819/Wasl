"""Assignment and delivery status service.

Handles driver task queue, accept/reject, and status transitions.
Financial transactions are created on delivery using config amounts.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from config import settings
from models.driver import Driver
from models.driver_assignment import DriverAssignment
from models.financial_transaction import FinancialTransaction
from models.merchant import Merchant
from models.order import Order
from models.order_status_history import OrderStatusHistory

# Valid status transitions for order status updates by driver
_VALID_TRANSITIONS = {
    "assigned": "picked_up",
    "picked_up": "in_transit",
    "in_transit": "delivered",
}


class AssignmentError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400):
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


def get_driver_tasks(
    db: Session, driver_id: int, status_filter: str | None = None
) -> list[dict]:
    """Return orders assigned to this driver."""
    q = (
        db.query(DriverAssignment, Order)
        .join(Order, DriverAssignment.order_id == Order.id)
        .filter(DriverAssignment.driver_id == driver_id)
    )
    if status_filter:
        q = q.filter(DriverAssignment.assignment_status == status_filter)

    results = q.order_by(DriverAssignment.assigned_at.desc()).all()

    tasks = []
    for assignment, order in results:
        merchant = db.get(Merchant, order.merchant_id)
        tasks.append({
            "order_id": order.id,
            "order_number": order.order_number,
            "merchant_name": (
                merchant.business_name if merchant else "Unknown"
            ),
            "customer_name": order.customer_name,
            "pickup_address_line1": order.pickup_address_line1,
            "delivery_address_line1": order.delivery_address_line1,
            "total_egp": float(order.total_egp),
            "scheduled_pickup_at": (
                order.scheduled_pickup_at.isoformat()
                if order.scheduled_pickup_at
                else None
            ),
            "delivery_notes": order.delivery_notes,
            "assignment_status": assignment.assignment_status,
            "assigned_at": assignment.assigned_at.isoformat(),
        })
    return tasks


def accept_task(
    db: Session, driver_id: int, order_id: int
) -> dict:
    assignment = (
        db.query(DriverAssignment)
        .filter(
            DriverAssignment.order_id == order_id,
            DriverAssignment.driver_id == driver_id,
            DriverAssignment.assignment_status == "assigned",
        )
        .first()
    )
    if assignment is None:
        raise AssignmentError(
            code="FORBIDDEN",
            message="This task is not assigned to you",
            http_status=403,
        )

    assignment.assignment_status = "accepted"
    assignment.accepted_at = datetime.now(timezone.utc)

    # Update order status
    order = db.get(Order, order_id)
    old_status = order.status
    order.status = "assigned"

    # Create status history
    history = OrderStatusHistory(
        order_id=order_id,
        previous_status=old_status,
        new_status="assigned",
        changed_by_user_id=driver_id,
        reason="Driver accepted task",
    )
    db.add(history)

    driver = db.get(Driver, driver_id)
    if driver:
        driver.is_on_delivery = True

    db.commit()

    return {
        "order_id": order_id,
        "order_number": order.order_number,
        "assignment_status": "accepted",
        "accepted_at": assignment.accepted_at.isoformat(),
    }


def reject_task(
    db: Session, driver_id: int, order_id: int, reason: str
) -> dict:
    assignment = (
        db.query(DriverAssignment)
        .filter(
            DriverAssignment.order_id == order_id,
            DriverAssignment.driver_id == driver_id,
            DriverAssignment.assignment_status == "assigned",
        )
        .first()
    )
    if assignment is None:
        raise AssignmentError(
            code="FORBIDDEN",
            message="This task is not assigned to you",
            http_status=403,
        )

    assignment.assignment_status = "rejected"
    assignment.rejected_at = datetime.now(timezone.utc)
    assignment.rejection_reason = reason

    # Return order to pending
    order = db.get(Order, order_id)
    old_status = order.status
    order.status = "pending"
    order.assigned_driver_id = None

    history = OrderStatusHistory(
        order_id=order_id,
        previous_status=old_status,
        new_status="pending",
        changed_by_user_id=driver_id,
        reason=f"Driver rejected: {reason}",
    )
    db.add(history)
    db.commit()

    return {
        "order_id": order_id,
        "assignment_status": "rejected",
        "rejected_at": assignment.rejected_at.isoformat(),
    }


def update_delivery_status(
    db: Session, driver_id: int, order_id: int, new_status: str
) -> dict:
    """Update order status with state machine validation."""
    order = db.get(Order, order_id)
    if order is None:
        raise AssignmentError(
            code="ORDER_NOT_FOUND",
            message="Order not found",
            http_status=404,
        )

    # Verify driver owns this assignment
    assignment = (
        db.query(DriverAssignment)
        .filter(
            DriverAssignment.order_id == order_id,
            DriverAssignment.driver_id == driver_id,
            DriverAssignment.assignment_status == "accepted",
        )
        .first()
    )
    if assignment is None:
        raise AssignmentError(
            code="FORBIDDEN",
            message="You can only update orders assigned to you",
            http_status=403,
        )

    current = order.status
    expected_next = _VALID_TRANSITIONS.get(current)

    if expected_next is None:
        raise AssignmentError(
            code="INVALID_STATUS_TRANSITION",
            message=f"Cannot transition from '{current}'",
            http_status=400,
        )
    if new_status != expected_next:
        raise AssignmentError(
            code="INVALID_STATUS_TRANSITION",
            message=(
                f"Invalid transition: '{current}' -> '{new_status}'. "
                f"Expected '{expected_next}'."
            ),
            http_status=400,
        )

    old_status = order.status
    order.status = new_status

    # Update timestamps
    now = datetime.now(timezone.utc)
    if new_status == "picked_up":
        order.actual_pickup_at = now
    elif new_status == "in_transit":
        pass  # no specific timestamp
    elif new_status == "delivered":
        order.actual_delivery_at = now

    # Create status history
    history = OrderStatusHistory(
        order_id=order_id,
        previous_status=old_status,
        new_status=new_status,
        changed_by_user_id=driver_id,
    )
    db.add(history)

    # On delivery: create financial transactions and clear delivery flag
    if new_status == "delivered":
        commission = FinancialTransaction(
            transaction_type="order_commission",
            related_order_id=order.id,
            related_merchant_id=order.merchant_id,
            amount_egp=settings.platform_commission_egp,
            status="pending",
        )
        payout = FinancialTransaction(
            transaction_type="driver_payout",
            related_order_id=order.id,
            related_driver_id=driver_id,
            amount_egp=settings.driver_payout_egp,
            status="pending",
        )
        db.add(commission)
        db.add(payout)

        driver = db.get(Driver, driver_id)
        if driver:
            driver.is_on_delivery = False

    db.commit()

    return {
        "order_id": order_id,
        "order_number": order.order_number,
        "status": new_status,
        "updated_at": now.isoformat(),
    }

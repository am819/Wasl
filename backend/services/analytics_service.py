"""Analytics service — live queries from the database."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.financial_transaction import FinancialTransaction
from models.order import Order

_PERIOD_MAP = {
    "today": timedelta(days=1),
    "week": timedelta(days=7),
    "month": timedelta(days=30),
}


def merchant_analytics(
    db: Session, merchant_id: int, period: str = "week"
) -> dict:
    """Calculate merchant metrics from live data."""
    delta = _PERIOD_MAP.get(period, _PERIOD_MAP["week"])
    since = datetime.now(timezone.utc) - delta

    orders = (
        db.query(Order)
        .filter(
            Order.merchant_id == merchant_id,
            Order.created_at >= since,
        )
        .all()
    )

    total_orders = len(orders)
    delivered = [o for o in orders if o.status == "delivered"]
    cancelled = [o for o in orders if o.status == "cancelled"]

    # Financial metrics from financial_transactions (source of truth)
    commission = (
        db.query(func.sum(FinancialTransaction.amount_egp))
        .filter(
            FinancialTransaction.transaction_type == "order_commission",
            FinancialTransaction.related_merchant_id == merchant_id,
            FinancialTransaction.created_at >= since,
        )
        .scalar()
    ) or Decimal("0")

    delivery_fees = sum(
        (o.delivery_fee_egp for o in delivered), Decimal("0")
    )

    ratings = [o.customer_rating for o in orders if o.customer_rating]
    avg_rating = (
        sum(ratings) / len(ratings) if ratings else 0
    )

    return {
        "period": period,
        "total_orders": total_orders,
        "total_delivery_fees_egp": float(delivery_fees),
        "total_platform_commission_egp": float(commission),
        "delivered_orders": len(delivered),
        "cancelled_orders": len(cancelled),
        "average_rating": round(avg_rating, 2),
        "_note": (
            "Figures are display aggregates. For invoicing or "
            "disputes query financial_transactions directly."
        ),
    }

"""SQLAlchemy ORM model for the orders table."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint, DateTime, ForeignKey,
    Numeric, SmallInteger, String, Text, func,
)
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    merchant_id: Mapped[int] = mapped_column(
        ForeignKey("merchants.id", ondelete="RESTRICT"), nullable=False
    )
    order_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    customer_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pickup_address_line1: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    pickup_address_line2: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    delivery_address_line1: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    delivery_address_line2: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    delivery_city: Mapped[str] = mapped_column(
        String(100), nullable=False, server_default="Alexandria"
    )
    delivery_notes: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    subtotal_egp: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )
    delivery_fee_egp: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )
    total_egp: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="pending"
    )
    payment_method: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="cash"
    )
    payment_status: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="pending"
    )
    assigned_driver_id: Mapped[int | None] = mapped_column(
        ForeignKey("drivers.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(),
        onupdate=func.now(),
    )
    scheduled_pickup_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    actual_pickup_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    estimated_delivery_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    actual_delivery_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    customer_rating: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True
    )

    __table_args__ = (
        CheckConstraint("subtotal_egp >= 0", name="orders_positive_subtotal"),
        CheckConstraint("delivery_fee_egp > 0", name="orders_positive_fee"),
        CheckConstraint("total_egp > 0", name="orders_positive_total"),
        CheckConstraint(
            "status IN ('pending','assigned','picked_up',"
            "'in_transit','delivered','cancelled')",
            name="orders_status_check",
        ),
        CheckConstraint(
            "payment_method IN ('cash')",
            name="orders_payment_method_check",
        ),
        CheckConstraint(
            "payment_status IN ('pending','collected','settled')",
            name="orders_payment_status_check",
        ),
        CheckConstraint(
            "customer_rating IS NULL "
            "OR customer_rating BETWEEN 1 AND 5",
            name="orders_valid_rating",
        ),
    )

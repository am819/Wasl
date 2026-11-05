"""SQLAlchemy ORM model for the drivers table."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, CheckConstraint, Date, DateTime, ForeignKey,
    Integer, Numeric, String, func,
)
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Driver(Base):
    __tablename__ = "drivers"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    national_id_number: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )  # stored encrypted
    vehicle_type: Mapped[str] = mapped_column(String(50), nullable=False)
    vehicle_plate_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    license_expiry: Mapped[date | None] = mapped_column(Date, nullable=True)

    is_online: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    is_on_delivery: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )

    total_deliveries: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    total_earnings_egp: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, server_default="0"
    )
    average_rating: Mapped[Decimal] = mapped_column(
        Numeric(3, 2), nullable=False, server_default="0"
    )
    cancellation_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False, server_default="0"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "vehicle_type IN ('motorcycle', 'car', 'van')",
            name="drivers_vehicle_check",
        ),
        CheckConstraint(
            "total_deliveries >= 0", name="drivers_positive_deliveries"
        ),
        CheckConstraint(
            "total_earnings_egp >= 0", name="drivers_positive_earnings"
        ),
        CheckConstraint(
            "average_rating BETWEEN 0 AND 5", name="drivers_valid_rating"
        ),
        CheckConstraint(
            "cancellation_rate BETWEEN 0 AND 1", name="drivers_valid_cancel_rate"
        ),
    )

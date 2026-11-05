"""SQLAlchemy ORM model for settlement_records."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint, Date, DateTime, Integer, Numeric, String, func,
)
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class SettlementRecord(Base):
    __tablename__ = "settlement_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    settlement_type: Mapped[str] = mapped_column(String(50), nullable=False)
    recipient_id: Mapped[int] = mapped_column(Integer, nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    total_amount_egp: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )
    commissions_egp: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    fees_egp: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    refunds_egp: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="pending"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "settlement_type IN ('merchant', 'driver')",
            name="sr_type_check",
        ),
        CheckConstraint(
            "status IN ('pending', 'processed', 'completed', 'failed')",
            name="sr_status_check",
        ),
        CheckConstraint(
            "period_end >= period_start",
            name="sr_valid_period",
        ),
    )

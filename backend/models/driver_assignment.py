"""SQLAlchemy ORM model for driver_assignments."""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint, DateTime, ForeignKey, String, Text, func,
)
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class DriverAssignment(Base):
    __tablename__ = "driver_assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    driver_id: Mapped[int] = mapped_column(
        ForeignKey("drivers.id", ondelete="RESTRICT"), nullable=False
    )
    assigned_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=False
    )
    assignment_status: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="assigned"
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "assignment_status IN ('assigned','accepted','rejected','cancelled')",
            name="da_status_check",
        ),
    )

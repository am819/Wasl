"""SQLAlchemy ORM model for the merchants table."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint, DateTime, ForeignKey, Integer,
    Numeric, String, func,
)
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Merchant(Base):
    __tablename__ = "merchants"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    business_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    address_line1: Mapped[str] = mapped_column(String(255), nullable=False)
    address_line2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(
        String(100), nullable=False, server_default="Alexandria"
    )
    postal_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    business_registration_number: Mapped[str | None] = mapped_column(
        String(50), unique=True, nullable=True
    )
    tax_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # stored encrypted
    contact_person_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Display-only stats (recalculated daily — ADR-005)
    total_orders: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    total_delivery_fees_egp: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, server_default="0"
    )
    total_platform_commission_egp: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, server_default="0"
    )
    average_rating: Mapped[Decimal] = mapped_column(
        Numeric(3, 2), nullable=False, server_default="0"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint("total_orders >= 0", name="merchants_positive_orders"),
        CheckConstraint(
            "total_delivery_fees_egp >= 0", name="merchants_positive_fees"
        ),
        CheckConstraint(
            "total_platform_commission_egp >= 0",
            name="merchants_positive_commission",
        ),
        CheckConstraint(
            "average_rating BETWEEN 0 AND 5", name="merchants_valid_rating"
        ),
    )

    def __repr__(self) -> str:
        return f"<Merchant id={self.id} name={self.business_name!r}>"

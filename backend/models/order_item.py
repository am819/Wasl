"""SQLAlchemy ORM model for the order_items table."""

from decimal import Decimal

from sqlalchemy import (
    CheckConstraint, ForeignKey, Integer, Numeric, String,
)
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    unit_price_egp: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    subtotal_egp: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    __table_args__ = (
        CheckConstraint("quantity > 0", name="order_items_positive_qty"),
        CheckConstraint("unit_price_egp > 0", name="order_items_positive_price"),
        CheckConstraint("subtotal_egp >= 0", name="order_items_positive_subtotal"),
    )

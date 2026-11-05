"""Pydantic schemas for order endpoints."""

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class OrderItemRequest(BaseModel):
    item_name: str = Field(..., min_length=1, max_length=255)
    quantity: int = Field(..., gt=0)
    unit_price_egp: Decimal = Field(..., gt=0)


class OrderCreateRequest(BaseModel):
    customer_name: str = Field(..., min_length=1, max_length=255)
    customer_phone: str = Field(..., min_length=11, max_length=11)
    customer_email: str | None = Field(None, max_length=255)
    pickup_address_line1: str = Field(..., min_length=5, max_length=255)
    pickup_address_line2: str | None = Field(None, max_length=255)
    delivery_address_line1: str = Field(..., min_length=5, max_length=255)
    delivery_address_line2: str | None = Field(None, max_length=255)
    delivery_notes: str | None = None
    items: list[OrderItemRequest] = Field(..., min_length=1, max_length=100)


class OrderCreateResponse(BaseModel):
    order_id: int
    order_number: str
    status: str
    subtotal_egp: Decimal
    delivery_fee_egp: Decimal
    total_egp: Decimal
    tracking_token: str
    tracking_link: str
    created_at: str


class OrderListResponse(BaseModel):
    orders: list[dict[str, Any]]
    total_count: int
    limit: int
    offset: int


class OrderDetailResponse(BaseModel):
    order: dict[str, Any]
    items: list[dict[str, Any]]
    status_history: list[dict[str, Any]]
    driver: dict[str, Any] | None

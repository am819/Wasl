"""Pydantic schemas for merchant endpoints."""

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class MerchantRegisterRequest(BaseModel):
    business_name: str = Field(..., min_length=2, max_length=255)
    business_phone: str = Field(..., min_length=11, max_length=11)
    address_line1: str = Field(..., min_length=5, max_length=255)
    address_line2: str | None = Field(None, max_length=255)
    city: str = Field("Alexandria", max_length=100)
    postal_code: str | None = Field(None, max_length=10)
    business_registration_number: str | None = Field(None, max_length=50)
    tax_id: str | None = Field(None, max_length=50)
    contact_person_name: str = Field(..., min_length=2, max_length=255)


class MerchantUpdateRequest(BaseModel):
    business_name: str | None = Field(None, min_length=2, max_length=255)
    business_phone: str | None = Field(None, min_length=11, max_length=11)
    address_line1: str | None = Field(None, min_length=5, max_length=255)
    address_line2: str | None = Field(None, max_length=255)
    contact_person_name: str | None = Field(None, min_length=2, max_length=255)


class MerchantStatsResponse(BaseModel):
    total_orders: int
    total_delivery_fees_egp: Decimal
    total_platform_commission_egp: Decimal
    average_rating: Decimal


class MerchantProfileResponse(BaseModel):
    id: int
    user_id: int
    business_name: str
    business_phone: str
    address_line1: str
    address_line2: str | None
    city: str
    contact_person_name: str
    stats: MerchantStatsResponse
    status: str
    created_at: Any

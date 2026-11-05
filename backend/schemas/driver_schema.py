"""Pydantic schemas for driver endpoints."""

from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class DriverRegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    national_id_number: str = Field(..., min_length=5, max_length=50)
    vehicle_type: str = Field(..., pattern="^(motorcycle|car|van)$")
    vehicle_plate_number: str | None = Field(None, max_length=50)
    license_expiry: date | None = None


class DriverUpdateRequest(BaseModel):
    full_name: str | None = Field(None, min_length=2, max_length=255)
    vehicle_plate_number: str | None = Field(None, max_length=50)


class DriverStatsResponse(BaseModel):
    total_deliveries: int
    total_earnings_egp: Decimal
    average_rating: Decimal
    cancellation_rate: Decimal


class DriverProfileResponse(BaseModel):
    id: int
    user_id: int
    full_name: str
    vehicle_type: str
    vehicle_plate_number: str | None
    is_online: bool
    is_on_delivery: bool
    stats: DriverStatsResponse
    status: str
    created_at: Any

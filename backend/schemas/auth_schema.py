"""Pydantic schemas for authentication endpoints."""

import re
from typing import Any

from pydantic import BaseModel, EmailStr, Field, field_validator

# Egyptian mobile number: 010, 011, 012, 015 followed by 8 digits
_EGYPTIAN_PHONE_RE = re.compile(r"^01[0125]\d{8}$")


class RegisterRequest(BaseModel):
    email: EmailStr
    phone: str = Field(..., min_length=11, max_length=11)
    password: str = Field(..., min_length=8)
    role: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not _EGYPTIAN_PHONE_RE.match(v):
            raise ValueError(
                "Phone must be a valid Egyptian mobile number "
                "(e.g., 01012345678)"
            )
        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ("merchant", "driver"):
            raise ValueError("role must be 'merchant' or 'driver'")
        return v


class RegisterResponse(BaseModel):
    user_id: int
    email: str
    role: str
    status: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    user_id: int
    email: str
    role: str
    token: str
    refresh_token: str
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)


class RefreshResponse(BaseModel):
    token: str
    refresh_token: str
    expires_in: int


class ApiResponse(BaseModel):
    """Standard response envelope used by all endpoints."""
    success: bool
    data: Any = None
    error: Any = None

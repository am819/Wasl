"""
JWT access-token utilities.

Tokens are signed with HS256 using the JWT_SECRET_KEY env variable.
Access tokens expire in 24 hours; refresh tokens are opaque random strings
stored as SHA-256 hashes in user_sessions (see SECURITY.md).
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from config import settings

_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24       # 24 hours
REFRESH_TOKEN_EXPIRE_DAYS = 7


# ---------------------------------------------------------------------------
# Access token
# ---------------------------------------------------------------------------

def create_access_token(
    user_id: int,
    email: str,
    role: str,
) -> str:
    """Return a signed JWT access token valid for 24 hours."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token.

    Raises:
        jose.ExpiredSignatureError  — token is expired
        jose.JWTError               — token is invalid / tampered
    """
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[_ALGORITHM])


# ---------------------------------------------------------------------------
# Refresh token (opaque random string + SHA-256 hash)
# ---------------------------------------------------------------------------

def generate_refresh_token() -> tuple[str, str]:
    """Return (plaintext_token, sha256_hex_digest).

    The plaintext is returned to the client once and never persisted.
    Only the hex digest (CHAR(64)) is stored in user_sessions.token_hash.
    """
    plaintext = secrets.token_urlsafe(48)   # 48 bytes → 64-char URL-safe string
    digest = _sha256_hex(plaintext)
    return plaintext, digest


def hash_refresh_token(plaintext: str) -> str:
    """Return the SHA-256 hex digest of a plaintext refresh token."""
    return _sha256_hex(plaintext)


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Re-export JWTError so callers don't import from jose directly
# ---------------------------------------------------------------------------

__all__ = [
    "JWTError",
    "create_access_token",
    "decode_access_token",
    "generate_refresh_token",
    "hash_refresh_token",
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    "REFRESH_TOKEN_EXPIRE_DAYS",
]

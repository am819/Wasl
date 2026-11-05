"""
Authentication service.

Handles login, refresh token rotation, logout, and account lockout.
All sensitive values (tokens, passwords) are handled without logging.
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from models.audit_log import AuditLog
from models.user import User
from models.user_session import UserSession
from security.jwt_utils import (
    REFRESH_TOKEN_EXPIRE_DAYS,
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
)
from security.password import verify_password

logger = logging.getLogger(__name__)

# Lockout thresholds (defined in SECURITY.md)
_MAX_FAILURES = 5
_LOCKOUT_MINUTES = 15

# In-memory lockout store: {email: (failure_count, first_failure_utc)}
# In production this would move to Redis; for MVP it suffices.
_lockout: dict[str, tuple[int, datetime]] = {}


class AuthError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 401):
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


# ---------------------------------------------------------------------------
# Lockout helpers
# ---------------------------------------------------------------------------

def _is_locked(email: str) -> bool:
    if email not in _lockout:
        return False
    count, first = _lockout[email]
    if count < _MAX_FAILURES:
        return False
    elapsed = datetime.now(timezone.utc) - first
    if elapsed < timedelta(minutes=_LOCKOUT_MINUTES):
        return True
    # Lockout expired — reset
    del _lockout[email]
    return False


def _record_failure(email: str) -> None:
    now = datetime.now(timezone.utc)
    if email in _lockout:
        count, first = _lockout[email]
        _lockout[email] = (count + 1, first)
    else:
        _lockout[email] = (1, now)


def _clear_lockout(email: str) -> None:
    _lockout.pop(email, None)


# ---------------------------------------------------------------------------
# Audit helper
# ---------------------------------------------------------------------------

def _audit(
    db: Session,
    action: str,
    user_id: int | None,
    extra: dict | None = None,
    ip: str | None = None,
    ua: str | None = None,
) -> None:
    entry = AuditLog(
        user_id=user_id,
        action=action,
        entity_type="user",
        entity_id=user_id,
        new_values=extra,
        ip_address=ip,
        user_agent=ua,
    )
    db.add(entry)
    # flush within caller's transaction; commit happens in the router


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def login(
    db: Session,
    email: str,
    password: str,
    ip: str | None = None,
    ua: str | None = None,
) -> tuple[str, str]:
    """Authenticate user and return (access_token, refresh_token_plaintext).

    Raises AuthError for invalid credentials, locked accounts.
    All failures are logged to audit_logs before raising.
    """
    # 1. Lockout check (before touching the database)
    if _is_locked(email):
        _audit(
            db, "login_locked", None,
            {"email": email, "reason": "account_locked"}, ip, ua,
        )
        db.commit()
        raise AuthError(
            code="ACCOUNT_LOCKED",
            message=(
                "Account is temporarily locked due to too many failed attempts. "
                f"Try again in {_LOCKOUT_MINUTES} minutes."
            ),
            http_status=401,
        )

    user = db.query(User).filter(User.email == email).first()

    # 2. Verify credentials (same error for missing user and wrong password
    #    — prevents user enumeration)
    if user is None or not verify_password(password, user.password_hash):
        _record_failure(email)
        _audit(
            db, "login_failed", user.id if user else None,
            {"email": email, "reason": "invalid_credentials"}, ip, ua,
        )
        db.commit()
        raise AuthError(
            code="INVALID_CREDENTIALS",
            message="Email or password is incorrect",
            http_status=401,
        )

    # 3. Clear any previous lockout on success
    _clear_lockout(email)

    # 4. Invalidate all existing sessions for this user (new login = new device)
    db.query(UserSession).filter(UserSession.user_id == user.id).delete()

    # 5. Create new session
    plaintext, digest = generate_refresh_token()
    session = UserSession(
        user_id=user.id,
        token_hash=digest,
        expires_at=(
            datetime.now(timezone.utc)
            + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        ),
        created_ip=ip,
        user_agent=ua,
    )
    db.add(session)

    # 6. Issue access token
    access_token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
    )

    # 7. Audit success
    _audit(db, "login_success", user.id, {"email": email}, ip, ua)
    db.commit()

    return access_token, plaintext


def refresh_tokens(
    db: Session,
    refresh_token_plain: str,
    ip: str | None = None,
    ua: str | None = None,
) -> tuple[str, str]:
    """Rotate refresh token. Return (new_access_token, new_refresh_token_plain).

    Raises AuthError if token is expired, revoked, or not found (replay attack).
    """
    digest = hash_refresh_token(refresh_token_plain)
    now = datetime.now(timezone.utc)

    session = (
        db.query(UserSession)
        .filter(UserSession.token_hash == digest)
        .first()
    )

    if session is None:
        raise AuthError(
            code="TOKEN_INVALID",
            message="Refresh token is invalid",
            http_status=401,
        )
    if session.revoked_at is not None:
        raise AuthError(
            code="TOKEN_INVALID",
            message="Refresh token has been revoked",
            http_status=401,
        )
    if session.expires_at.replace(tzinfo=timezone.utc) < now:
        db.delete(session)
        db.commit()
        raise AuthError(
            code="TOKEN_EXPIRED",
            message="Refresh token has expired",
            http_status=401,
        )

    user = db.get(User, session.user_id)
    if user is None:
        db.delete(session)
        db.commit()
        raise AuthError(
            code="TOKEN_INVALID",
            message="User not found",
            http_status=401,
        )

    # Rotate: revoke old session, create new one
    session.revoked_at = now
    session.last_used_at = now

    new_plain, new_digest = generate_refresh_token()
    new_session = UserSession(
        user_id=user.id,
        token_hash=new_digest,
        expires_at=now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        created_ip=ip,
        user_agent=ua,
    )
    db.add(new_session)

    new_access = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
    )

    _audit(db, "token_refreshed", user.id, None, ip, ua)
    db.commit()

    return new_access, new_plain


def logout(
    db: Session,
    refresh_token_plain: str,
    user_id: int,
    ip: str | None = None,
    ua: str | None = None,
) -> None:
    """Revoke the supplied refresh token and log the logout."""
    digest = hash_refresh_token(refresh_token_plain)
    session = (
        db.query(UserSession)
        .filter(
            UserSession.token_hash == digest,
            UserSession.user_id == user_id,
        )
        .first()
    )
    if session:
        session.revoked_at = datetime.now(timezone.utc)

    _audit(db, "logout", user_id, None, ip, ua)
    db.commit()


def reset_lockout_for_test(email: str) -> None:
    """Test-only helper to clear the in-memory lockout store."""
    _lockout.pop(email, None)

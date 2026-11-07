"""Tests for scripts/reset_admin_password.py."""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

# Make the scripts/ directory importable
_SCRIPTS_DIR = str(Path(__file__).resolve().parents[2] / "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from reset_admin_password import main as reset_main  # noqa: E402


def _create_admin(db, email="admin@wasl.eg", phone="01000000000"):
    """Insert an approved admin user and return it."""
    from security.password import hash_password
    from models.user import User

    user = User(
        email=email,
        phone=phone,
        password_hash=hash_password("OldPassword1!"),
        role="admin",
        status="approved",
    )
    db.add(user)
    db.commit()
    db.expire_all()
    return user


def _set_env(email: str, new_password: str):
    """Set the env vars the script reads."""
    os.environ["ADMIN_EMAIL"] = email
    os.environ["NEW_ADMIN_PASSWORD"] = new_password


def _clear_env():
    os.environ.pop("ADMIN_EMAIL", None)
    os.environ.pop("NEW_ADMIN_PASSWORD", None)


class TestResetAdminPassword:

    def test_password_is_updated_in_db(self, db):
        """After reset, the new password verifies against the stored hash."""
        from security.password import verify_password
        from models.user import User

        _create_admin(db)
        _set_env("admin@wasl.eg", "NewSecure1!")
        try:
            reset_main()
        finally:
            _clear_env()

        db.expire_all()
        user = db.query(User).filter(User.email == "admin@wasl.eg").first()
        assert verify_password("NewSecure1!", user.password_hash)
        assert not verify_password("OldPassword1!", user.password_hash)

    def test_old_password_no_longer_works(self, db):
        from security.password import verify_password
        from models.user import User

        _create_admin(db, "admin2@wasl.eg", "01011111111")
        _set_env("admin2@wasl.eg", "AnotherNew1!")
        try:
            reset_main()
        finally:
            _clear_env()

        db.expire_all()
        user = db.query(User).filter(User.email == "admin2@wasl.eg").first()
        assert not verify_password("OldPassword1!", user.password_hash)

    def test_existing_sessions_are_revoked(self, db):
        """All active sessions are revoked after a password reset."""
        from models.user_session import UserSession

        user = _create_admin(db, "admin3@wasl.eg", "01022222222")
        # Create two active sessions
        for token_h in ("a" * 64, "b" * 64):
            session = UserSession(
                user_id=user.id,
                token_hash=token_h,
                expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
            )
            db.add(session)
        db.commit()

        _set_env("admin3@wasl.eg", "ResetPass1!")
        try:
            reset_main()
        finally:
            _clear_env()

        db.expire_all()
        active = (
            db.query(UserSession)
            .filter(
                UserSession.user_id == user.id,
                UserSession.revoked_at.is_(None),
            )
            .count()
        )
        assert active == 0

    def test_lockout_is_cleared(self, db):
        """In-memory lockout counter is cleared after a password reset."""
        from services.auth_service import _lockout, _record_failure

        _create_admin(db, "admin4@wasl.eg", "01033333333")
        # Simulate failed login attempts
        for _ in range(5):
            _record_failure("admin4@wasl.eg")
        assert "admin4@wasl.eg" in _lockout

        _set_env("admin4@wasl.eg", "ClearLock1!")
        try:
            reset_main()
        finally:
            _clear_env()

        assert "admin4@wasl.eg" not in _lockout

    def test_missing_env_vars_exits_nonzero(self, db):
        """Script exits with SystemExit(1) when env vars are missing."""
        _clear_env()
        with pytest.raises(SystemExit) as exc_info:
            reset_main()
        assert exc_info.value.code == 1

    def test_weak_password_exits_nonzero(self, db):
        """Script exits with SystemExit(1) when password is too weak."""
        _create_admin(db, "admin5@wasl.eg", "01044444444")
        _set_env("admin5@wasl.eg", "weak")
        try:
            with pytest.raises(SystemExit) as exc_info:
                reset_main()
            assert exc_info.value.code == 1
        finally:
            _clear_env()

    def test_nonexistent_user_exits_nonzero(self, db):
        """Script exits with SystemExit(1) when the email is not found."""
        _set_env("nobody@wasl.eg", "GoodPass1!")
        try:
            with pytest.raises(SystemExit) as exc_info:
                reset_main()
            assert exc_info.value.code == 1
        finally:
            _clear_env()

    def test_non_admin_role_exits_nonzero(self, db):
        """Script refuses to reset a non-admin user's password."""
        from security.password import hash_password
        from models.user import User

        merchant = User(
            email="merchant@wasl.eg",
            phone="01055555555",
            password_hash=hash_password("OldPassword1!"),
            role="merchant",
            status="approved",
        )
        db.add(merchant)
        db.commit()

        _set_env("merchant@wasl.eg", "GoodPass1!")
        try:
            with pytest.raises(SystemExit) as exc_info:
                reset_main()
            assert exc_info.value.code == 1
        finally:
            _clear_env()

"""Tests for Task 1.2 — Login & JWT Token Issuance."""

from sqlalchemy.orm import Session

from models.audit_log import AuditLog
from models.user_session import UserSession
from security.jwt_utils import decode_access_token
from services.auth_service import reset_lockout_for_test


class TestLogin:
    def test_login_success_returns_tokens(self, client, registered_merchant):
        resp = client.post("/api/v1/auth/login", json={
            "email": "merchant@test.com",
            "password": "SecurePass1!",
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "token" in data
        assert "refresh_token" in data
        assert data["expires_in"] == 86400      # 24 hours in seconds
        assert data["email"] == "merchant@test.com"
        assert data["role"] == "merchant"
        # Plaintext password must never appear in response
        assert "password" not in str(resp.json())

    def test_jwt_payload_contains_required_fields(
        self, client, registered_merchant
    ):
        resp = client.post("/api/v1/auth/login", json={
            "email": "merchant@test.com",
            "password": "SecurePass1!",
        })
        token = resp.json()["data"]["token"]
        payload = decode_access_token(token)
        assert "sub" in payload         # user_id
        assert "email" in payload
        assert "role" in payload
        assert "iat" in payload
        assert "exp" in payload
        assert payload["email"] == "merchant@test.com"
        assert payload["role"] == "merchant"

    def test_refresh_token_stored_as_hash_in_db(
        self, client, registered_merchant, db: Session
    ):
        resp = client.post("/api/v1/auth/login", json={
            "email": "merchant@test.com",
            "password": "SecurePass1!",
        })
        plaintext_refresh = resp.json()["data"]["refresh_token"]
        user_id = resp.json()["data"]["user_id"]

        from security.jwt_utils import hash_refresh_token
        expected_hash = hash_refresh_token(plaintext_refresh)

        session = (
            db.query(UserSession)
            .filter(UserSession.user_id == user_id)
            .first()
        )
        assert session is not None
        assert session.token_hash == expected_hash
        # The hash must be 64 hex characters (SHA-256)
        assert len(session.token_hash) == 64
        # Plaintext must NOT be stored
        assert session.token_hash != plaintext_refresh

    def test_invalid_password_returns_401(self, client, registered_merchant):
        resp = client.post("/api/v1/auth/login", json={
            "email": "merchant@test.com",
            "password": "WrongPassword1!",
        })
        assert resp.status_code == 401
        assert resp.json()["detail"]["code"] == "INVALID_CREDENTIALS"

    def test_nonexistent_email_returns_401(self, client):
        resp = client.post("/api/v1/auth/login", json={
            "email": "nobody@test.com",
            "password": "SecurePass1!",
        })
        assert resp.status_code == 401
        assert resp.json()["detail"]["code"] == "INVALID_CREDENTIALS"

    def test_login_failure_logged_to_audit(
        self, client, registered_merchant, db: Session
    ):
        reset_lockout_for_test("merchant@test.com")
        client.post("/api/v1/auth/login", json={
            "email": "merchant@test.com",
            "password": "BadPass1!",
        })
        log = (
            db.query(AuditLog)
            .filter(AuditLog.action == "login_failed")
            .first()
        )
        assert log is not None

    def test_login_success_logged_to_audit(
        self, client, registered_merchant, db: Session
    ):
        reset_lockout_for_test("merchant@test.com")
        client.post("/api/v1/auth/login", json={
            "email": "merchant@test.com",
            "password": "SecurePass1!",
        })
        log = (
            db.query(AuditLog)
            .filter(AuditLog.action == "login_success")
            .first()
        )
        assert log is not None

    def test_account_locked_after_5_failures(
        self, client, registered_merchant
    ):
        reset_lockout_for_test("merchant@test.com")
        for _ in range(5):
            client.post("/api/v1/auth/login", json={
                "email": "merchant@test.com",
                "password": "WrongPass1!",
            })
        # 6th attempt should be locked
        resp = client.post("/api/v1/auth/login", json={
            "email": "merchant@test.com",
            "password": "SecurePass1!",  # even correct password locked out
        })
        assert resp.status_code == 401
        assert resp.json()["detail"]["code"] == "ACCOUNT_LOCKED"
        # Always clean up so other tests aren't affected
        reset_lockout_for_test("merchant@test.com")

    def test_new_login_invalidates_previous_session(
        self, client, registered_merchant, db: Session
    ):
        reset_lockout_for_test("merchant@test.com")
        # First login
        resp1 = client.post("/api/v1/auth/login", json={
            "email": "merchant@test.com",
            "password": "SecurePass1!",
        })
        user_id = resp1.json()["data"]["user_id"]
        # Second login — should delete the first session
        client.post("/api/v1/auth/login", json={
            "email": "merchant@test.com",
            "password": "SecurePass1!",
        })
        sessions = (
            db.query(UserSession)
            .filter(UserSession.user_id == user_id)
            .all()
        )
        # Only one active (non-revoked) session should exist
        active = [s for s in sessions if s.revoked_at is None]
        assert len(active) == 1

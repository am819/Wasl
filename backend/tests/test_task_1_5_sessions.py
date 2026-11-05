"""Tests for Task 1.5 — Token Refresh & Session Management."""

from sqlalchemy.orm import Session

from models.user_session import UserSession


class TestTokenRefresh:
    def test_refresh_returns_new_token_pair(self, client, merchant_tokens):
        resp = client.post("/api/v1/auth/refresh", json={
            "refresh_token": merchant_tokens["refresh_token"],
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "token" in data
        assert "refresh_token" in data
        assert data["expires_in"] == 86400
        # New refresh token must always differ (random value)
        assert data["refresh_token"] != merchant_tokens["refresh_token"]
        # Access token is a valid JWT
        from security.jwt_utils import decode_access_token
        payload = decode_access_token(data["token"])
        assert payload["role"] == "merchant"

    def test_replayed_refresh_token_returns_401(
        self, client, merchant_tokens
    ):
        old_refresh = merchant_tokens["refresh_token"]
        # Use it once (valid)
        resp1 = client.post("/api/v1/auth/refresh", json={
            "refresh_token": old_refresh,
        })
        assert resp1.status_code == 200

        # Replay — must be rejected
        resp2 = client.post("/api/v1/auth/refresh", json={
            "refresh_token": old_refresh,
        })
        assert resp2.status_code == 401
        assert resp2.json()["detail"]["code"] in (
            "TOKEN_INVALID", "TOKEN_EXPIRED"
        )

    def test_invalid_refresh_token_returns_401(self, client):
        resp = client.post("/api/v1/auth/refresh", json={
            "refresh_token": "totally-made-up-token",
        })
        assert resp.status_code == 401
        assert resp.json()["detail"]["code"] == "TOKEN_INVALID"

    def test_new_refresh_token_is_stored_as_sha256_hash(
        self, client, merchant_tokens, db: Session
    ):
        resp = client.post("/api/v1/auth/refresh", json={
            "refresh_token": merchant_tokens["refresh_token"],
        })
        new_refresh_plain = resp.json()["data"]["refresh_token"]
        user_id = merchant_tokens["user_id"]

        from security.jwt_utils import hash_refresh_token
        expected_hash = hash_refresh_token(new_refresh_plain)

        session = (
            db.query(UserSession)
            .filter(
                UserSession.user_id == user_id,
                UserSession.revoked_at.is_(None),
            )
            .first()
        )
        assert session is not None
        assert session.token_hash == expected_hash
        assert len(session.token_hash) == 64  # SHA-256 hex is always 64 chars


class TestLogout:
    def test_logout_returns_204(self, client, merchant_tokens):
        resp = client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": merchant_tokens["refresh_token"]},
            headers={"Authorization": f"Bearer {merchant_tokens['token']}"},
        )
        assert resp.status_code == 204

    def test_refresh_after_logout_returns_401(
        self, client, merchant_tokens
    ):
        # Logout
        client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": merchant_tokens["refresh_token"]},
            headers={"Authorization": f"Bearer {merchant_tokens['token']}"},
        )
        # Attempt to refresh with now-revoked token
        resp = client.post("/api/v1/auth/refresh", json={
            "refresh_token": merchant_tokens["refresh_token"],
        })
        assert resp.status_code == 401

    def test_logout_requires_valid_access_token(self, client, merchant_tokens):
        resp = client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": merchant_tokens["refresh_token"]},
            # No Authorization header
        )
        assert resp.status_code == 401

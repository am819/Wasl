"""Tests for Task 1.3 — JWT Middleware & Protected Routes."""

from datetime import datetime, timedelta, timezone


class TestJWTMiddleware:
    def test_no_token_returns_401(self, client):
        resp = client.get("/api/v1/merchants/me")
        assert resp.status_code == 401

    def test_valid_token_allows_access(self, client, merchant_tokens):
        resp = client.get(
            "/api/v1/merchants/me",
            headers={"Authorization": f"Bearer {merchant_tokens['token']}"},
        )
        assert resp.status_code == 200

    def test_malformed_token_returns_401_invalid(self, client):
        resp = client.get(
            "/api/v1/merchants/me",
            headers={"Authorization": "Bearer this.is.notvalid"},
        )
        assert resp.status_code == 401
        assert resp.json()["detail"]["code"] == "TOKEN_INVALID"

    def test_tampered_token_returns_401_invalid(self, client, merchant_tokens):
        token = merchant_tokens["token"]
        # Flip last character
        tampered = token[:-1] + ("X" if token[-1] != "X" else "Y")
        resp = client.get(
            "/api/v1/merchants/me",
            headers={"Authorization": f"Bearer {tampered}"},
        )
        assert resp.status_code == 401
        assert resp.json()["detail"]["code"] == "TOKEN_INVALID"

    def test_expired_token_returns_401_expired(self, client, registered_merchant):
        # Create a token that expired 1 second ago
        from jose import jwt
        from config import settings
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(registered_merchant["user_id"]),
            "email": registered_merchant["email"],
            "role": registered_merchant["role"],
            "iat": now - timedelta(hours=25),
            "exp": now - timedelta(seconds=1),
        }
        expired_token = jwt.encode(
            payload, settings.jwt_secret_key, algorithm="HS256"
        )
        resp = client.get(
            "/api/v1/merchants/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert resp.status_code == 401
        assert resp.json()["detail"]["code"] == "TOKEN_EXPIRED"

    def test_missing_bearer_scheme_returns_401(self, client, merchant_tokens):
        resp = client.get(
            "/api/v1/merchants/me",
            headers={"Authorization": merchant_tokens["token"]},  # no "Bearer "
        )
        assert resp.status_code == 401

"""Tests for Task 1.1 — User Registration."""

from security.password import (
    hash_password,
    validate_password_complexity,
    verify_password,
)


# ── Unit: password hashing ────────────────────────────────────────────────

class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        hashed = hash_password("SecurePass1!")
        assert hashed != "SecurePass1!"

    def test_verify_correct_password(self):
        hashed = hash_password("SecurePass1!")
        assert verify_password("SecurePass1!", hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("SecurePass1!")
        assert verify_password("WrongPass2@", hashed) is False

    def test_hash_uses_bcrypt_prefix(self):
        hashed = hash_password("SecurePass1!")
        assert hashed.startswith("$2")  # bcrypt hash prefix


# ── Unit: password complexity ─────────────────────────────────────────────

class TestPasswordComplexity:
    def test_valid_password_no_errors(self):
        assert validate_password_complexity("SecurePass1!") == []

    def test_too_short(self):
        errors = validate_password_complexity("Ab1!")
        assert any("8 characters" in e for e in errors)

    def test_missing_uppercase(self):
        errors = validate_password_complexity("securepass1!")
        assert any("uppercase" in e for e in errors)

    def test_missing_lowercase(self):
        errors = validate_password_complexity("SECUREPASS1!")
        assert any("lowercase" in e for e in errors)

    def test_missing_digit(self):
        errors = validate_password_complexity("SecurePass!!")
        assert any("digit" in e for e in errors)

    def test_missing_special(self):
        errors = validate_password_complexity("SecurePass12")
        assert any("special" in e for e in errors)


# ── Integration: registration endpoint ────────────────────────────────────

class TestRegistration:
    def test_register_merchant_success(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "email": "new@merchant.com",
            "phone": "01012345678",
            "password": "SecurePass1!",
            "role": "merchant",
        })
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["email"] == "new@merchant.com"
        assert data["role"] == "merchant"
        assert data["status"] == "pending"
        assert "user_id" in data
        # Password must never appear in response
        assert "password" not in str(resp.json())

    def test_register_driver_success(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "email": "new@driver.com",
            "phone": "01112345678",
            "password": "SecurePass1!",
            "role": "driver",
        })
        assert resp.status_code == 201
        assert resp.json()["data"]["role"] == "driver"

    def test_duplicate_email_returns_409(self, client, registered_merchant):
        resp = client.post("/api/v1/auth/register", json={
            "email": "merchant@test.com",   # already registered
            "phone": "01099999999",
            "password": "SecurePass1!",
            "role": "merchant",
        })
        assert resp.status_code == 409
        detail = resp.json()["detail"]
        assert detail["code"] == "DUPLICATE_EMAIL"

    def test_duplicate_phone_returns_409(self, client, registered_merchant):
        resp = client.post("/api/v1/auth/register", json={
            "email": "other@merchant.com",
            "phone": "01012345678",          # already registered
            "password": "SecurePass1!",
            "role": "merchant",
        })
        assert resp.status_code == 409
        detail = resp.json()["detail"]
        assert detail["code"] == "DUPLICATE_PHONE"

    def test_invalid_role_rejected(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "email": "admin@test.com",
            "phone": "01099999998",
            "password": "SecurePass1!",
            "role": "admin",  # not allowed via self-registration
        })
        assert resp.status_code == 422  # Pydantic validation

    def test_weak_password_rejected(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "email": "weak@test.com",
            "phone": "01099999997",
            "password": "password",   # no complexity
            "role": "merchant",
        })
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert detail["code"] == "VALIDATION_ERROR"

    def test_invalid_email_rejected(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "email": "not-an-email",
            "phone": "01099999996",
            "password": "SecurePass1!",
            "role": "merchant",
        })
        assert resp.status_code == 422

    def test_invalid_phone_rejected(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "email": "phone@test.com",
            "phone": "12345678901",  # doesn't start with 01[0125]
            "password": "SecurePass1!",
            "role": "merchant",
        })
        assert resp.status_code == 422

    def test_missing_fields_rejected(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "email": "missing@test.com",
        })
        assert resp.status_code == 422

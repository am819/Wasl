"""Tests for Task 2.1 — Merchant Registration & Profile."""

from models.merchant import Merchant

MERCHANT_PROFILE = {
    "business_name": "Al Nour Restaurant",
    "business_phone": "01198765432",
    "address_line1": "45 El Geish Road",
    "city": "Alexandria",
    "contact_person_name": "Omar Hassan",
}


def _register_and_login(client, email="m1@test.com", phone="01012345678"):
    client.post("/api/v1/auth/register", json={
        "email": email, "phone": phone,
        "password": "SecurePass1!", "role": "merchant",
    })
    r = client.post("/api/v1/auth/login", json={
        "email": email, "password": "SecurePass1!",
    })
    return r.json()["data"]["token"]


class TestMerchantProfile:
    def test_create_profile_returns_201(self, client):
        token = _register_and_login(client)
        resp = client.post(
            "/api/v1/merchants/profile",
            json=MERCHANT_PROFILE,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["business_name"] == "Al Nour Restaurant"
        assert data["status"] == "pending"

    def test_profile_defaults_to_pending(self, client):
        token = _register_and_login(client)
        resp = client.post(
            "/api/v1/merchants/profile",
            json=MERCHANT_PROFILE,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.json()["data"]["status"] == "pending"

    def test_get_profile_returns_data(self, client):
        token = _register_and_login(client)
        client.post(
            "/api/v1/merchants/profile",
            json=MERCHANT_PROFILE,
            headers={"Authorization": f"Bearer {token}"},
        )
        resp = client.get(
            "/api/v1/merchants/profile",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["business_name"] == "Al Nour Restaurant"
        assert "stats" in resp.json()["data"]

    def test_update_profile(self, client):
        token = _register_and_login(client)
        client.post(
            "/api/v1/merchants/profile",
            json=MERCHANT_PROFILE,
            headers={"Authorization": f"Bearer {token}"},
        )
        resp = client.put(
            "/api/v1/merchants/profile",
            json={"business_name": "New Name Restaurant"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["business_name"] == "New Name Restaurant"

    def test_cannot_update_another_merchants_profile(self, client):
        """Merchant A cannot update Merchant B's profile (ownership enforced)."""
        token_a = _register_and_login(client, "a@test.com", "01011111111")
        token_b = _register_and_login(client, "b@test.com", "01022222222")
        # B creates profile
        client.post(
            "/api/v1/merchants/profile",
            json={**MERCHANT_PROFILE, "business_name": "B Shop"},
            headers={"Authorization": f"Bearer {token_b}"},
        )
        # A tries to update — gets the wrong merchant (their own 404)
        resp = client.put(
            "/api/v1/merchants/profile",
            json={"business_name": "Hacked"},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        # A has no profile yet, so 404
        assert resp.status_code == 404
        # And B's name is unchanged
        resp_b = client.get(
            "/api/v1/merchants/profile",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert resp_b.json()["data"]["business_name"] == "B Shop"

    def test_driver_cannot_access_merchant_profile(self, client,
                                                   registered_driver):
        token = client.post("/api/v1/auth/login", json={
            "email": "driver@test.com", "password": "SecurePass1!",
        }).json()["data"]["token"]
        resp = client.post(
            "/api/v1/merchants/profile",
            json=MERCHANT_PROFILE,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    def test_tax_id_encrypted_in_db(self, client, db):
        """tax_id must be stored encrypted, not in plaintext."""
        from security.encryption import decrypt_field, encrypt_field  # noqa: F401

        # Create profile with tax_id via the API (uses same db session via override)
        token = _register_and_login(client)
        resp = client.post(
            "/api/v1/merchants/profile",
            json={**MERCHANT_PROFILE, "tax_id": "TAX123456"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201

        # Query the same session (client uses the `db` fixture via override)
        db.expire_all()   # ensure we see the committed state within this session
        m = db.query(Merchant).filter(
            Merchant.business_name == "Al Nour Restaurant"
        ).first()
        assert m is not None, "Merchant not found in test DB session"
        assert m.tax_id is not None
        # Must NOT be stored as plaintext
        assert m.tax_id != "TAX123456"
        # Must be decryptable
        assert decrypt_field(m.tax_id) == "TAX123456"

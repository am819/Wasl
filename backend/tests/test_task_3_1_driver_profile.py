"""Tests for Task 3.1 — Driver Registration & Profile."""

from models.driver import Driver

DRIVER_PROFILE = {
    "full_name": "Mohamed Ali",
    "national_id_number": "12345678901234",
    "vehicle_type": "motorcycle",
    "vehicle_plate_number": "ABC-1234",
}


def _setup_driver(client, email="d1@t.com", phone="01012345678"):
    from services.auth_service import reset_lockout_for_test
    reset_lockout_for_test(email)
    client.post("/api/v1/auth/register", json={
        "email": email, "phone": phone,
        "password": "SecurePass1!", "role": "driver",
    })
    t = client.post("/api/v1/auth/login", json={
        "email": email, "password": "SecurePass1!",
    }).json()["data"]["token"]
    return t


class TestDriverProfile:
    def test_create_profile_returns_201(self, client):
        token = _setup_driver(client)
        resp = client.post(
            "/api/v1/drivers/profile",
            json=DRIVER_PROFILE,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["full_name"] == "Mohamed Ali"
        assert data["vehicle_type"] == "motorcycle"
        assert data["status"] == "pending"

    def test_get_profile(self, client):
        token = _setup_driver(client)
        client.post(
            "/api/v1/drivers/profile",
            json=DRIVER_PROFILE,
            headers={"Authorization": f"Bearer {token}"},
        )
        resp = client.get(
            "/api/v1/drivers/profile",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["full_name"] == "Mohamed Ali"

    def test_update_profile(self, client):
        token = _setup_driver(client)
        client.post(
            "/api/v1/drivers/profile",
            json=DRIVER_PROFILE,
            headers={"Authorization": f"Bearer {token}"},
        )
        resp = client.put(
            "/api/v1/drivers/profile",
            json={"full_name": "Updated Name"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["full_name"] == "Updated Name"

    def test_national_id_encrypted_in_db(self, client, db):
        """national_id_number must be stored encrypted, not plaintext."""
        token = _setup_driver(client)
        client.post(
            "/api/v1/drivers/profile",
            json=DRIVER_PROFILE,
            headers={"Authorization": f"Bearer {token}"},
        )
        db.expire_all()
        d = db.query(Driver).filter(
            Driver.full_name == "Mohamed Ali"
        ).first()
        assert d is not None
        assert d.national_id_number != "12345678901234"
        from security.encryption import decrypt_field
        assert decrypt_field(d.national_id_number) == "12345678901234"

    def test_merchant_cannot_access_driver_profile(self, client,
                                                    registered_merchant):
        token = client.post("/api/v1/auth/login", json={
            "email": "merchant@test.com", "password": "SecurePass1!",
        }).json()["data"]["token"]
        resp = client.post(
            "/api/v1/drivers/profile",
            json=DRIVER_PROFILE,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    def test_invalid_vehicle_type_rejected(self, client):
        token = _setup_driver(client)
        resp = client.post(
            "/api/v1/drivers/profile",
            json={**DRIVER_PROFILE, "vehicle_type": "truck"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

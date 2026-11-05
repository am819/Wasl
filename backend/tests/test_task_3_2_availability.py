"""Tests for Task 3.2 — Driver Availability Toggle."""


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
    client.post("/api/v1/drivers/profile", json={
        "full_name": "Mohamed Ali",
        "national_id_number": "12345678901234",
        "vehicle_type": "motorcycle",
    }, headers={"Authorization": f"Bearer {t}"})
    return t


class TestAvailability:
    def test_toggle_online(self, client, db):
        token = _setup_driver(client)
        # Approve the driver
        from models.user import User
        u = db.query(User).filter(User.email == "d1@t.com").first()
        u.status = "approved"
        db.commit()
        db.expire_all()
        resp = client.post(
            "/api/v1/drivers/availability",
            json={"is_online": True},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["is_online"] is True

    def test_toggle_offline(self, client, db):
        token = _setup_driver(client, "d2@t.com", "01022345679")
        from models.user import User
        u = db.query(User).filter(User.email == "d2@t.com").first()
        u.status = "approved"
        db.commit()
        db.expire_all()
        # Go online first
        client.post(
            "/api/v1/drivers/availability",
            json={"is_online": True},
            headers={"Authorization": f"Bearer {token}"},
        )
        # Then offline
        resp = client.post(
            "/api/v1/drivers/availability",
            json={"is_online": False},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["is_online"] is False

    def test_unapproved_cannot_go_online(self, client):
        """Unapproved driver cannot toggle availability — 403."""
        token = _setup_driver(client, "d3@t.com", "01033345680")
        # NOT approving — status stays pending
        resp = client.post(
            "/api/v1/drivers/availability",
            json={"is_online": True},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
        assert resp.json()["detail"]["code"] == "DRIVER_NOT_APPROVED"

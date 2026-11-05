"""Tests for Task 1.4 — Role-Based Access Control."""


class TestRBAC:
    def test_merchant_can_reach_merchant_endpoint(
        self, client, merchant_tokens
    ):
        resp = client.get(
            "/api/v1/merchants/me",
            headers={"Authorization": f"Bearer {merchant_tokens['token']}"},
        )
        assert resp.status_code == 200

    def test_merchant_cannot_reach_driver_endpoint(
        self, client, merchant_tokens
    ):
        resp = client.get(
            "/api/v1/drivers/me",
            headers={"Authorization": f"Bearer {merchant_tokens['token']}"},
        )
        assert resp.status_code == 403
        assert resp.json()["detail"]["code"] == "FORBIDDEN"

    def test_merchant_cannot_reach_admin_endpoint(
        self, client, merchant_tokens
    ):
        resp = client.get(
            "/api/v1/admin/me",
            headers={"Authorization": f"Bearer {merchant_tokens['token']}"},
        )
        assert resp.status_code == 403
        assert resp.json()["detail"]["code"] == "FORBIDDEN"

    def test_driver_can_reach_driver_endpoint(
        self, client, registered_driver
    ):
        login = client.post("/api/v1/auth/login", json={
            "email": "driver@test.com",
            "password": "SecurePass1!",
        })
        token = login.json()["data"]["token"]
        resp = client.get(
            "/api/v1/drivers/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

    def test_driver_cannot_reach_merchant_endpoint(
        self, client, registered_driver
    ):
        login = client.post("/api/v1/auth/login", json={
            "email": "driver@test.com",
            "password": "SecurePass1!",
        })
        token = login.json()["data"]["token"]
        resp = client.get(
            "/api/v1/merchants/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
        assert resp.json()["detail"]["code"] == "FORBIDDEN"

    def test_unauthenticated_cannot_reach_any_protected_endpoint(self, client):
        for path in ["/api/v1/merchants/me", "/api/v1/drivers/me",
                     "/api/v1/admin/me"]:
            resp = client.get(path)
            assert resp.status_code == 401, f"{path} should return 401"

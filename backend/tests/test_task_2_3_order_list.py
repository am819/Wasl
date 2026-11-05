"""Tests for Task 2.3 — Order List & Detail View."""


MERCHANT_PROFILE = {
    "business_name": "Test Restaurant",
    "business_phone": "01198765432",
    "address_line1": "45 El Geish Road",
    "city": "Alexandria",
    "contact_person_name": "Omar Hassan",
}

ORDER_BODY = {
    "customer_name": "Ahmed Hassan",
    "customer_phone": "01012345678",
    "pickup_address_line1": "45 El Geish Road",
    "delivery_address_line1": "123 Corniche St",
    "items": [
        {"item_name": "Chicken", "quantity": 2, "unit_price_egp": 45},
    ],
}


def _setup_merchant(client, db, email, phone):
    from services.auth_service import reset_lockout_for_test
    reset_lockout_for_test(email)
    client.post("/api/v1/auth/register", json={
        "email": email, "phone": phone,
        "password": "SecurePass1!", "role": "merchant",
    })
    t = client.post("/api/v1/auth/login", json={
        "email": email, "password": "SecurePass1!",
    }).json()["data"]["token"]
    client.post("/api/v1/merchants/profile", json=MERCHANT_PROFILE,
                 headers={"Authorization": f"Bearer {t}"})
    from models.user import User
    u = db.query(User).filter(User.email == email).first()
    u.status = "approved"
    db.commit()
    db.expire_all()
    return t


class TestOrderList:
    def test_list_orders_returns_paginated(self, client, db):
        token = _setup_merchant(client, db, "m1@t.com", "01012345678")
        for _ in range(3):
            client.post("/api/v1/merchants/orders", json=ORDER_BODY,
                        headers={"Authorization": f"Bearer {token}"})
        resp = client.get("/api/v1/merchants/orders?limit=2",
                          headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total_count"] == 3
        assert len(data["orders"]) == 2
        assert data["limit"] == 2

    def test_filter_by_status(self, client, db):
        token = _setup_merchant(client, db, "m2@t.com", "01012345679")
        client.post("/api/v1/merchants/orders", json=ORDER_BODY,
                     headers={"Authorization": f"Bearer {token}"})
        resp = client.get("/api/v1/merchants/orders?status=pending",
                          headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        orders = resp.json()["data"]["orders"]
        assert all(o["status"] == "pending" for o in orders)

    def test_merchant_only_sees_own_orders(self, client, db):
        """Merchant A cannot see Merchant B's orders."""
        token_a = _setup_merchant(client, db, "a@t.com", "01011111111")
        token_b = _setup_merchant(client, db, "b@t.com", "01022222222")
        # B creates an order
        client.post("/api/v1/merchants/orders", json=ORDER_BODY,
                     headers={"Authorization": f"Bearer {token_b}"})
        # A lists orders — should see 0
        resp = client.get("/api/v1/merchants/orders",
                          headers={"Authorization": f"Bearer {token_a}"})
        assert resp.json()["data"]["total_count"] == 0

    def test_get_order_detail(self, client, db):
        token = _setup_merchant(client, db, "m3@t.com", "01012345680")
        r = client.post("/api/v1/merchants/orders", json=ORDER_BODY,
                        headers={"Authorization": f"Bearer {token}"})
        oid = r.json()["data"]["order_id"]
        resp = client.get(f"/api/v1/merchants/orders/{oid}",
                          headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["order"]["id"] == oid
        assert len(data["items"]) == 1
        assert data["items"][0]["item_name"] == "Chicken"
        assert len(data["status_history"]) >= 1

    def test_other_merchant_order_returns_403(self, client, db):
        """Merchant A accessing Merchant B's order gets 403, not 404."""
        token_a = _setup_merchant(client, db, "a2@t.com", "01033333333")
        token_b = _setup_merchant(client, db, "b2@t.com", "01044444444")
        r = client.post("/api/v1/merchants/orders", json=ORDER_BODY,
                        headers={"Authorization": f"Bearer {token_b}"})
        oid = r.json()["data"]["order_id"]
        resp = client.get(f"/api/v1/merchants/orders/{oid}",
                          headers={"Authorization": f"Bearer {token_a}"})
        assert resp.status_code == 403
        assert resp.json()["detail"]["code"] == "FORBIDDEN"

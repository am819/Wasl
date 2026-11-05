"""Tests for Task 2.4 — Merchant Analytics."""

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


def _setup_merchant(client, db, email="m1@t.com", phone="01012345678"):
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


class TestAnalytics:
    def test_analytics_returns_metrics(self, client, db):
        token = _setup_merchant(client, db)
        client.post("/api/v1/merchants/orders", json=ORDER_BODY,
                     headers={"Authorization": f"Bearer {token}"})
        resp = client.get("/api/v1/merchants/analytics?period=week",
                          headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["period"] == "week"
        assert data["total_orders"] == 1
        assert "total_delivery_fees_egp" in data
        assert "total_platform_commission_egp" in data
        assert "delivered_orders" in data
        assert "cancelled_orders" in data
        assert "average_rating" in data

    def test_analytics_period_filter(self, client, db):
        token = _setup_merchant(client, db)
        client.post("/api/v1/merchants/orders", json=ORDER_BODY,
                     headers={"Authorization": f"Bearer {token}"})
        for p in ["today", "week", "month"]:
            resp = client.get(
                f"/api/v1/merchants/analytics?period={p}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            assert resp.json()["data"]["period"] == p

    def test_analytics_with_delivered_order(self, client, db):
        token = _setup_merchant(client, db)
        # Create order and manually mark as delivered
        r = client.post("/api/v1/merchants/orders", json=ORDER_BODY,
                        headers={"Authorization": f"Bearer {token}"})
        from models.order import Order
        o = db.query(Order).filter(Order.id == r.json()["data"]["order_id"]).first()
        o.status = "delivered"
        db.commit()
        db.expire_all()

        resp = client.get("/api/v1/merchants/analytics?period=week",
                          headers={"Authorization": f"Bearer {token}"})
        data = resp.json()["data"]
        assert data["delivered_orders"] == 1
        # delivery_fees should include the 15 EGP fee
        assert data["total_delivery_fees_egp"] == 15.0

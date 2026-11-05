"""Tests for Task 2.2 — Order Creation."""

from models.order_item import OrderItem
from models.order_status_history import OrderStatusHistory
from models.tracking_token import TrackingToken

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
        {"item_name": "Chicken", "quantity": 2, "unit_price_egp": 45.00},
        {"item_name": "Tea", "quantity": 2, "unit_price_egp": 10.00},
    ],
}


def _setup_approved_merchant(client, db=None, email="m1@test.com", phone="01012345678"):
    """Register, create profile, approve user, return token."""
    from services.auth_service import reset_lockout_for_test
    reset_lockout_for_test(email)
    client.post("/api/v1/auth/register", json={
        "email": email, "phone": phone,
        "password": "SecurePass1!", "role": "merchant",
    })
    login_resp = client.post("/api/v1/auth/login", json={
        "email": email, "password": "SecurePass1!",
    })
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    token = login_resp.json()["data"]["token"]
    client.post(
        "/api/v1/merchants/profile",
        json=MERCHANT_PROFILE,
        headers={"Authorization": f"Bearer {token}"},
    )
    if db:
        _approve_user(client, db, email)
    return token


def _approve_user(client, db, email):
    """Directly set user status to approved in DB."""
    from models.user import User
    user = db.query(User).filter(User.email == email).first()
    user.status = "approved"
    db.commit()
    db.expire_all()


class TestOrderCreation:
    def test_create_order_success(self, client, db):
        token = _setup_approved_merchant(client, db)
        resp = client.post(
            "/api/v1/merchants/orders",
            json=ORDER_BODY,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["status"] == "pending"
        assert data["order_number"].startswith("WAS-")
        assert data["subtotal_egp"] == 110.0
        assert data["delivery_fee_egp"] == 15.0
        assert data["total_egp"] == 125.0
        assert "tracking_token" in data
        assert data["tracking_link"].startswith("/tracking/")

    def test_order_number_format(self, client, db):
        token = _setup_approved_merchant(client, db)
        resp = client.post(
            "/api/v1/merchants/orders",
            json=ORDER_BODY,
            headers={"Authorization": f"Bearer {token}"},
        )
        num = resp.json()["data"]["order_number"]
        # WAS-YYYYMMDD-NNN
        parts = num.split("-")
        assert len(parts) == 3
        assert parts[0] == "WAS"
        assert len(parts[2]) == 3

    def test_order_items_created(self, client, db):
        token = _setup_approved_merchant(client, db)
        resp = client.post(
            "/api/v1/merchants/orders",
            json=ORDER_BODY,
            headers={"Authorization": f"Bearer {token}"},
        )
        order_id = resp.json()["data"]["order_id"]
        db.expire_all()
        items = db.query(OrderItem).filter(
            OrderItem.order_id == order_id
        ).all()
        assert len(items) == 2
        assert items[0].item_name == "Chicken"
        assert items[0].quantity == 2

    def test_status_history_created(self, client, db):
        token = _setup_approved_merchant(client, db)
        resp = client.post(
            "/api/v1/merchants/orders",
            json=ORDER_BODY,
            headers={"Authorization": f"Bearer {token}"},
        )
        order_id = resp.json()["data"]["order_id"]
        db.expire_all()
        hist = db.query(OrderStatusHistory).filter(
            OrderStatusHistory.order_id == order_id
        ).all()
        assert len(hist) == 1
        assert hist[0].new_status == "pending"

    def test_tracking_token_stored(self, client, db):
        token = _setup_approved_merchant(client, db)
        resp = client.post(
            "/api/v1/merchants/orders",
            json=ORDER_BODY,
            headers={"Authorization": f"Bearer {token}"},
        )
        order_id = resp.json()["data"]["order_id"]
        db.expire_all()
        tt = db.query(TrackingToken).filter(
            TrackingToken.order_id == order_id
        ).first()
        assert tt is not None
        assert len(tt.token) > 30  # random URL-safe string

    def test_pending_merchant_cannot_create_orders(self, client, db):
        """Merchant must be approved — pending returns 403."""
        token = _setup_approved_merchant(client, db)
        # Revoke approval to test
        from models.user import User
        u = db.query(User).filter(User.email == "m1@test.com").first()
        u.status = "pending"
        db.commit()
        db.expire_all()
        resp = client.post(
            "/api/v1/merchants/orders",
            json=ORDER_BODY,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
        assert resp.json()["detail"]["code"] == "MERCHANT_NOT_APPROVED"

    def test_total_calculation(self, client, db):
        token = _setup_approved_merchant(client, db)
        body = {
            **ORDER_BODY,
            "items": [{"item_name": "X", "quantity": 1, "unit_price_egp": 100}],
        }
        resp = client.post(
            "/api/v1/merchants/orders",
            json=body,
            headers={"Authorization": f"Bearer {token}"},
        )
        data = resp.json()["data"]
        assert data["subtotal_egp"] == 100.0
        assert data["delivery_fee_egp"] == 15.0  # from config
        assert data["total_egp"] == 115.0

    def test_empty_items_rejected(self, client, db):
        token = _setup_approved_merchant(client, db)
        resp = client.post(
            "/api/v1/merchants/orders",
            json={**ORDER_BODY, "items": []},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422  # Pydantic min_length=1

    def test_missing_customer_phone_rejected(self, client, db):
        token = _setup_approved_merchant(client, db)
        body = {**ORDER_BODY, "customer_phone": ""}
        resp = client.post(
            "/api/v1/merchants/orders",
            json=body,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

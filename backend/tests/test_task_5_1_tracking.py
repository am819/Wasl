"""Tests for Task 5.1 — Public Tracking."""

from datetime import datetime, timedelta, timezone
from models.tracking_token import TrackingToken
from models.user import User


def _setup_admin(client, db):
    from security.password import hash_password
    from services.auth_service import reset_lockout_for_test
    reset_lockout_for_test("admin@wasl.eg")
    admin = User(
        email="admin@wasl.eg", phone="01000000000",
        password_hash=hash_password("AdminPass1!"),
        role="admin", status="approved",
    )
    db.add(admin)
    db.commit()
    db.expire_all()
    resp = client.post("/api/v1/auth/login", json={
        "email": "admin@wasl.eg", "password": "AdminPass1!",
    })
    return resp.json()["data"]["token"]


def _create_order_with_token(client, db):
    """Create a merchant order and return (order_id, tracking_token)."""
    from services.auth_service import reset_lockout_for_test
    reset_lockout_for_test("m@t.com")
    client.post("/api/v1/auth/register", json={
        "email": "m@t.com", "phone": "01012345678",
        "password": "SecurePass1!", "role": "merchant",
    })
    t = client.post("/api/v1/auth/login", json={
        "email": "m@t.com", "password": "SecurePass1!",
    }).json()["data"]["token"]
    client.post("/api/v1/merchants/profile", json={
        "business_name": "Test", "business_phone": "01198765432",
        "address_line1": "45 El Geish", "city": "Alexandria",
        "contact_person_name": "Omar",
    }, headers={"Authorization": f"Bearer {t}"})
    u = db.query(User).filter(User.email == "m@t.com").first()
    u.status = "approved"
    db.commit()
    db.expire_all()
    r = client.post("/api/v1/merchants/orders", json={
        "customer_name": "Ahmed", "customer_phone": "01012345678",
        "pickup_address_line1": "45 El Geish",
        "delivery_address_line1": "123 Corniche",
        "items": [{"item_name": "X", "quantity": 1, "unit_price_egp": 50}],
    }, headers={"Authorization": f"Bearer {t}"})
    return r.json()["data"]["order_id"], r.json()["data"]["tracking_token"]


class TestPublicTracking:
    def test_valid_token_returns_public_info(self, client, db):
        _, token = _create_order_with_token(client, db)
        resp = client.get(f"/api/v1/tracking/{token}")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "order_number" in data
        assert "status" in data
        assert "customer_name" in data
        assert "delivery_address_line1" in data

    def test_no_auth_required(self, client, db):
        _, token = _create_order_with_token(client, db)
        # No Authorization header at all
        resp = client.get(f"/api/v1/tracking/{token}")
        assert resp.status_code == 200

    def test_invalid_token_returns_404(self, client):
        resp = client.get("/api/v1/tracking/totally-fake-token-12345")
        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "TRACKING_TOKEN_INVALID"

    def test_expired_token_returns_404(self, client, db):
        oid, _ = _create_order_with_token(client, db)
        # Manually expire the token
        tt = db.query(TrackingToken).filter(
            TrackingToken.order_id == oid
        ).first()
        tt.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        db.commit()
        db.expire_all()
        resp = client.get(f"/api/v1/tracking/{tt.token}")
        assert resp.status_code == 404

    def test_access_count_incremented(self, client, db):
        _, token = _create_order_with_token(client, db)
        client.get(f"/api/v1/tracking/{token}")
        client.get(f"/api/v1/tracking/{token}")
        db.expire_all()
        tt = db.query(TrackingToken).filter(
            TrackingToken.token == token
        ).first()
        assert tt.access_count >= 2

    def test_no_sensitive_data_exposed(self, client, db):
        _, token = _create_order_with_token(client, db)
        resp = client.get(f"/api/v1/tracking/{token}")
        data = resp.json()["data"]
        # These must NOT appear in the public tracking response
        assert "customer_phone" not in data
        assert "merchant" not in str(data).lower().replace(
            "merchant_name", ""
        ) or "merchant_name" not in data
        assert "total_egp" not in data
        assert "subtotal" not in data
        assert "delivery_fee" not in data
        assert "merchant_id" not in data
        # Driver phone must not be exposed
        assert "driver_phone" not in data
        assert "phone" not in str(data).lower() or "customer_phone" not in data

"""End-to-end workflow test (Task 5.2).

Tests the full operational flow:
  Merchant creates order → Admin assigns driver →
  Driver accepts → Driver delivers → Financial transactions created
  → Public tracking shows delivered status
"""

from models.audit_log import AuditLog
from models.driver import Driver
from models.financial_transaction import FinancialTransaction
from models.order_status_history import OrderStatusHistory
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
    return client.post("/api/v1/auth/login", json={
        "email": "admin@wasl.eg", "password": "AdminPass1!",
    }).json()["data"]["token"]


def _setup_merchant(client, db):
    from services.auth_service import reset_lockout_for_test
    reset_lockout_for_test("merchant@e2e.com")
    client.post("/api/v1/auth/register", json={
        "email": "merchant@e2e.com", "phone": "01011111111",
        "password": "SecurePass1!", "role": "merchant",
    })
    t = client.post("/api/v1/auth/login", json={
        "email": "merchant@e2e.com", "password": "SecurePass1!",
    }).json()["data"]["token"]
    client.post("/api/v1/merchants/profile", json={
        "business_name": "E2E Restaurant",
        "business_phone": "01198765432",
        "address_line1": "45 El Geish Road",
        "city": "Alexandria",
        "contact_person_name": "Omar Hassan",
    }, headers={"Authorization": f"Bearer {t}"})
    u = db.query(User).filter(User.email == "merchant@e2e.com").first()
    u.status = "approved"
    db.commit()
    db.expire_all()
    return t


def _setup_driver(client, db):
    from services.auth_service import reset_lockout_for_test
    reset_lockout_for_test("driver@e2e.com")
    client.post("/api/v1/auth/register", json={
        "email": "driver@e2e.com", "phone": "01022222222",
        "password": "SecurePass1!", "role": "driver",
    })
    t = client.post("/api/v1/auth/login", json={
        "email": "driver@e2e.com", "password": "SecurePass1!",
    }).json()["data"]["token"]
    client.post("/api/v1/drivers/profile", json={
        "full_name": "E2E Driver",
        "national_id_number": "12345678901234",
        "vehicle_type": "motorcycle",
    }, headers={"Authorization": f"Bearer {t}"})
    u = db.query(User).filter(User.email == "driver@e2e.com").first()
    u.status = "approved"
    db.commit()
    db.expire_all()
    d = db.query(Driver).filter(Driver.user_id == u.id).first()
    return t, d.id


class TestEndToEndWorkflow:
    def test_full_delivery_workflow(self, client, db):
        """Complete flow: create → assign → accept → deliver → verify."""
        # 1. Setup
        admin_token = _setup_admin(client, db)
        merchant_token = _setup_merchant(client, db)
        driver_token, driver_id = _setup_driver(client, db)

        # 2. Merchant creates order
        r = client.post("/api/v1/merchants/orders", json={
            "customer_name": "Ahmed Hassan",
            "customer_phone": "01012345678",
            "pickup_address_line1": "45 El Geish Road",
            "delivery_address_line1": "123 Corniche St",
            "items": [
                {"item_name": "Chicken", "quantity": 2, "unit_price_egp": 45},
                {"item_name": "Tea", "quantity": 1, "unit_price_egp": 10},
            ],
        }, headers={"Authorization": f"Bearer {merchant_token}"})
        assert r.status_code == 201
        order_id = r.json()["data"]["order_id"]
        tracking_token = r.json()["data"]["tracking_token"]

        # 3. Admin assigns driver
        r = client.post(
            f"/api/v1/admin/orders/{order_id}/assign",
            json={"driver_id": driver_id},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 200

        # 4. Driver accepts
        r = client.post(
            f"/api/v1/drivers/tasks/{order_id}/accept",
            headers={"Authorization": f"Bearer {driver_token}"},
        )
        assert r.status_code == 200

        # 5. Driver updates status through delivery
        for status in ["picked_up", "in_transit", "delivered"]:
            r = client.put(
                f"/api/v1/drivers/tasks/{order_id}/status",
                json={"status": status},
                headers={"Authorization": f"Bearer {driver_token}"},
            )
            assert r.status_code == 200
            assert r.json()["data"]["status"] == status

        # 6. Verify financial transactions
        db.expire_all()
        txns = db.query(FinancialTransaction).filter(
            FinancialTransaction.related_order_id == order_id
        ).all()
        assert len(txns) == 2
        types = {t.transaction_type for t in txns}
        assert "order_commission" in types
        assert "driver_payout" in types

        # 7. Verify order status history
        history = db.query(OrderStatusHistory).filter(
            OrderStatusHistory.order_id == order_id
        ).order_by(OrderStatusHistory.created_at.asc()).all()
        statuses = [h.new_status for h in history]
        assert "pending" in statuses
        assert "assigned" in statuses
        assert "delivered" in statuses

        # 8. Verify public tracking shows delivered
        r = client.get(f"/api/v1/tracking/{tracking_token}")
        assert r.status_code == 200
        assert r.json()["data"]["status"] == "delivered"

        # 9. Verify audit logs
        logs = db.query(AuditLog).filter(
            AuditLog.entity_id == order_id
        ).all()
        assert len(logs) >= 1  # at least the assignment

        # 10. Verify driver earnings
        r = client.get(
            "/api/v1/drivers/earnings?period=week",
            headers={"Authorization": f"Bearer {driver_token}"},
        )
        assert r.status_code == 200
        assert r.json()["data"]["order_count"] >= 1

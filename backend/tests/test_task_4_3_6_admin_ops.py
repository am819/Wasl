"""Tests for Tasks 4.3-4.6 — Order assignment, settlements, analytics, audit."""

from models.audit_log import AuditLog
from models.driver import Driver
from models.driver_assignment import DriverAssignment
from models.financial_transaction import FinancialTransaction
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
    assert resp.status_code == 200
    return resp.json()["data"]["token"]


def _setup_merchant_with_order(client, db, email="m@t.com", phone="01012345678"):
    from services.auth_service import reset_lockout_for_test
    reset_lockout_for_test(email)
    client.post("/api/v1/auth/register", json={
        "email": email, "phone": phone,
        "password": "SecurePass1!", "role": "merchant",
    })
    t = client.post("/api/v1/auth/login", json={
        "email": email, "password": "SecurePass1!",
    }).json()["data"]["token"]
    client.post("/api/v1/merchants/profile", json={
        "business_name": "Test", "business_phone": "01198765432",
        "address_line1": "45 El Geish", "city": "Alexandria",
        "contact_person_name": "Omar",
    }, headers={"Authorization": f"Bearer {t}"})
    u = db.query(User).filter(User.email == email).first()
    u.status = "approved"
    db.commit()
    db.expire_all()
    r = client.post("/api/v1/merchants/orders", json={
        "customer_name": "Ahmed", "customer_phone": "01012345678",
        "pickup_address_line1": "45 El Geish",
        "delivery_address_line1": "123 Corniche",
        "items": [{"item_name": "X", "quantity": 1, "unit_price_egp": 50}],
    }, headers={"Authorization": f"Bearer {t}"})
    return r.json()["data"]["order_id"]


def _setup_approved_driver(client, db, email="d@t.com", phone="01012345679"):
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
        "full_name": "Driver One", "national_id_number": "12345678901234",
        "vehicle_type": "motorcycle",
    }, headers={"Authorization": f"Bearer {t}"})
    u = db.query(User).filter(User.email == email).first()
    u.status = "approved"
    db.commit()
    db.expire_all()
    d = db.query(Driver).filter(Driver.user_id == u.id).first()
    return t, d.id


class TestOrderAssignment:
    """Task 4.3"""

    def test_list_pending_orders(self, client, db):
        admin_token = _setup_admin(client, db)
        _setup_merchant_with_order(client, db)
        resp = client.get(
            "/api/v1/admin/orders?status=pending",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["total_count"] >= 1

    def test_assign_order_to_driver(self, client, db):
        admin_token = _setup_admin(client, db)
        oid = _setup_merchant_with_order(client, db)
        _, driver_id = _setup_approved_driver(client, db)
        resp = client.post(
            f"/api/v1/admin/orders/{oid}/assign",
            json={"driver_id": driver_id},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "assigned"
        # Verify assignment created
        db.expire_all()
        a = db.query(DriverAssignment).filter(
            DriverAssignment.order_id == oid
        ).first()
        assert a is not None
        assert a.driver_id == driver_id

    def test_assignment_logged_to_audit(self, client, db):
        admin_token = _setup_admin(client, db)
        oid = _setup_merchant_with_order(client, db, "m2@t.com", "01022345678")
        _, driver_id = _setup_approved_driver(client, db, "d2@t.com", "01022345679")
        client.post(
            f"/api/v1/admin/orders/{oid}/assign",
            json={"driver_id": driver_id},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        db.expire_all()
        log = db.query(AuditLog).filter(
            AuditLog.action == "assign_driver",
            AuditLog.entity_id == oid,
        ).first()
        assert log is not None


class TestFinancialTransactions:
    """Task 4.4"""

    def test_delivery_creates_two_transactions(self, client, db):
        admin_token = _setup_admin(client, db)
        oid = _setup_merchant_with_order(client, db)
        driver_token, driver_id = _setup_approved_driver(client, db)
        # Assign
        client.post(
            f"/api/v1/admin/orders/{oid}/assign",
            json={"driver_id": driver_id},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        # Accept and deliver
        client.post(
            f"/api/v1/drivers/tasks/{oid}/accept",
            headers={"Authorization": f"Bearer {driver_token}"},
        )
        for s in ["picked_up", "in_transit", "delivered"]:
            client.put(
                f"/api/v1/drivers/tasks/{oid}/status",
                json={"status": s},
                headers={"Authorization": f"Bearer {driver_token}"},
            )
        db.expire_all()
        txns = db.query(FinancialTransaction).filter(
            FinancialTransaction.related_order_id == oid
        ).all()
        assert len(txns) == 2
        types = {t.transaction_type for t in txns}
        assert "order_commission" in types
        assert "driver_payout" in types
        assert all(t.status == "pending" for t in txns)

    def test_amounts_from_config(self, client, db):
        from config import settings
        admin_token = _setup_admin(client, db)
        oid = _setup_merchant_with_order(client, db, "m3@t.com", "01033345678")
        driver_token, driver_id = _setup_approved_driver(
            client, db, "d3@t.com", "01033345679"
        )
        client.post(
            f"/api/v1/admin/orders/{oid}/assign",
            json={"driver_id": driver_id},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        client.post(
            f"/api/v1/drivers/tasks/{oid}/accept",
            headers={"Authorization": f"Bearer {driver_token}"},
        )
        for s in ["picked_up", "in_transit", "delivered"]:
            client.put(
                f"/api/v1/drivers/tasks/{oid}/status",
                json={"status": s},
                headers={"Authorization": f"Bearer {driver_token}"},
            )
        db.expire_all()
        commission = db.query(FinancialTransaction).filter(
            FinancialTransaction.transaction_type == "order_commission",
            FinancialTransaction.related_order_id == oid,
        ).first()
        payout = db.query(FinancialTransaction).filter(
            FinancialTransaction.transaction_type == "driver_payout",
            FinancialTransaction.related_order_id == oid,
        ).first()
        assert float(commission.amount_egp) == settings.platform_commission_egp
        assert float(payout.amount_egp) == settings.driver_payout_egp


class TestSettlements:
    """Task 4.5"""

    def test_list_pending_settlements(self, client, db):
        admin_token = _setup_admin(client, db)
        resp = client.get(
            "/api/v1/admin/settlements?status=pending",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert "settlements" in resp.json()["data"]

    def test_process_settlements(self, client, db):
        admin_token = _setup_admin(client, db)
        oid = _setup_merchant_with_order(client, db)
        driver_token, driver_id = _setup_approved_driver(client, db)
        client.post(
            f"/api/v1/admin/orders/{oid}/assign",
            json={"driver_id": driver_id},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        client.post(
            f"/api/v1/drivers/tasks/{oid}/accept",
            headers={"Authorization": f"Bearer {driver_token}"},
        )
        for s in ["picked_up", "in_transit", "delivered"]:
            client.put(
                f"/api/v1/drivers/tasks/{oid}/status",
                json={"status": s},
                headers={"Authorization": f"Bearer {driver_token}"},
            )
        # Process driver payouts
        resp = client.post(
            "/api/v1/admin/settlements/process",
            json={"transaction_type": "driver_payout"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["processed_count"] >= 1
        db.expire_all()
        completed = db.query(FinancialTransaction).filter(
            FinancialTransaction.transaction_type == "driver_payout",
            FinancialTransaction.status == "completed",
        ).all()
        assert len(completed) >= 1

    def test_settlement_logged_to_audit(self, client, db):
        admin_token = _setup_admin(client, db)
        client.post(
            "/api/v1/admin/settlements/process",
            json={"transaction_type": "driver_payout"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        db.expire_all()
        log = db.query(AuditLog).filter(
            AuditLog.action == "process_settlement"
        ).first()
        assert log is not None


class TestPlatformAnalytics:
    """Task 4.6"""

    def test_platform_analytics(self, client, db):
        admin_token = _setup_admin(client, db)
        _setup_merchant_with_order(client, db)
        resp = client.get(
            "/api/v1/admin/analytics?period=week",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "total_orders" in data
        assert "active_merchants" in data
        assert "active_drivers" in data
        assert "completion_rate" in data

    def test_audit_log_viewer(self, client, db):
        admin_token = _setup_admin(client, db)
        resp = client.get(
            "/api/v1/admin/audit-logs",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert "logs" in resp.json()["data"]

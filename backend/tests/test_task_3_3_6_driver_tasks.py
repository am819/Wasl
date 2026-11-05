"""Tests for Tasks 3.3-3.6 — Task queue, accept/reject, status, earnings."""

from models.driver import Driver
from models.driver_assignment import DriverAssignment
from models.financial_transaction import FinancialTransaction
from models.order import Order


def _setup_approved_driver(client, db, email="d1@t.com", phone="01012345678"):
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
    from models.user import User
    u = db.query(User).filter(User.email == email).first()
    u.status = "approved"
    db.commit()
    db.expire_all()
    return t


def _setup_approved_merchant(client, db, email="m1@t.com", phone="01012345678"):
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
        "business_name": "Test Restaurant",
        "business_phone": "01198765432",
        "address_line1": "45 El Geish Road",
        "city": "Alexandria",
        "contact_person_name": "Omar Hassan",
    }, headers={"Authorization": f"Bearer {t}"})
    from models.user import User
    u = db.query(User).filter(User.email == email).first()
    u.status = "approved"
    db.commit()
    db.expire_all()
    return t


def _create_order_and_assign(client, db, merchant_token, driver_id,
                              admin_user_id):
    """Create order, manually assign to driver."""
    r = client.post("/api/v1/merchants/orders", json={
        "customer_name": "Ahmed Hassan",
        "customer_phone": "01012345678",
        "pickup_address_line1": "45 El Geish Road",
        "delivery_address_line1": "123 Corniche St",
        "items": [{"item_name": "Chicken", "quantity": 1,
                   "unit_price_egp": 50}],
    }, headers={"Authorization": f"Bearer {merchant_token}"})
    order_id = r.json()["data"]["order_id"]

    # Manually assign (simulating admin assignment)
    order = db.get(Order, order_id)
    order.assigned_driver_id = driver_id
    order.status = "assigned"
    db.flush()

    assignment = DriverAssignment(
        order_id=order_id,
        driver_id=driver_id,
        assigned_by_user_id=admin_user_id,
        assignment_status="assigned",
    )
    db.add(assignment)
    db.commit()
    db.expire_all()
    return order_id


class TestTaskQueue:
    """Task 3.3 — Driver task queue."""

    def test_driver_sees_assigned_tasks(self, client, db):
        token = _setup_approved_driver(client, db)
        driver = db.query(Driver).filter(Driver.full_name == "Mohamed Ali").first()
        mt = _setup_approved_merchant(client, db, "m1@t.com", "01012345679")
        admin = db.query(__import__("models.user", fromlist=["User"]).User).first()
        oid = _create_order_and_assign(client, db, mt, driver.id, admin.id)

        resp = client.get(
            "/api/v1/drivers/tasks",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        tasks = resp.json()["data"]["tasks"]
        assert len(tasks) == 1
        assert tasks[0]["order_id"] == oid
        assert tasks[0]["merchant_name"] == "Test Restaurant"

    def test_driver_only_sees_own_tasks(self, client, db):
        """Driver A cannot see Driver B's tasks."""
        token_a = _setup_approved_driver(client, db, "da@t.com", "01012345670")
        token_b = _setup_approved_driver(client, db, "db@t.com", "01012345671")
        from models.user import User
        ub = db.query(User).filter(User.email == "db@t.com").first()
        driver_b = db.query(Driver).filter(Driver.user_id == ub.id).first()

        mt = _setup_approved_merchant(client, db, "m1@t.com", "01012345679")
        admin = db.query(User).first()
        _create_order_and_assign(client, db, mt, driver_b.id, admin.id)

        # Driver A should see 0 tasks
        resp_a = client.get(
            "/api/v1/drivers/tasks",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert resp_a.json()["data"]["count"] == 0

        # Driver B should see 1 task
        resp_b = client.get(
            "/api/v1/drivers/tasks",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert resp_b.json()["data"]["count"] == 1


class TestAcceptReject:
    """Task 3.4 — Task acceptance and rejection."""

    def test_accept_task(self, client, db):
        token = _setup_approved_driver(client, db)
        driver = db.query(Driver).first()
        mt = _setup_approved_merchant(client, db, "m1@t.com", "01012345679")
        from models.user import User
        admin = db.query(User).first()
        oid = _create_order_and_assign(client, db, mt, driver.id, admin.id)

        resp = client.post(
            f"/api/v1/drivers/tasks/{oid}/accept",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["assignment_status"] == "accepted"

    def test_reject_task(self, client, db):
        token = _setup_approved_driver(client, db)
        driver = db.query(Driver).first()
        mt = _setup_approved_merchant(client, db, "m1@t.com", "01012345679")
        from models.user import User
        admin = db.query(User).first()
        oid = _create_order_and_assign(client, db, mt, driver.id, admin.id)

        resp = client.post(
            f"/api/v1/drivers/tasks/{oid}/reject",
            json={"reason": "Vehicle issue"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["assignment_status"] == "rejected"

        # Order should be back to pending
        db.expire_all()
        order = db.get(Order, oid)
        assert order.status == "pending"

    def test_driver_cannot_accept_other_driver_task(self, client, db):
        """Driver cannot accept a task assigned to another driver."""
        token_a = _setup_approved_driver(client, db, "da@t.com", "01012345670")
        _setup_approved_driver(client, db, "db@t.com", "01012345671")
        from models.user import User
        ub = db.query(User).filter(User.email == "db@t.com").first()
        driver_b = db.query(Driver).filter(Driver.user_id == ub.id).first()
        mt = _setup_approved_merchant(client, db, "m1@t.com", "01012345679")
        admin = db.query(User).first()
        oid = _create_order_and_assign(client, db, mt, driver_b.id, admin.id)

        # Driver A tries to accept B's task
        resp = client.post(
            f"/api/v1/drivers/tasks/{oid}/accept",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert resp.status_code == 403


class TestDeliveryStatus:
    """Task 3.5 — Delivery status updates (state machine)."""

    def _setup_and_accept(self, client, db):
        token = _setup_approved_driver(client, db)
        driver = db.query(Driver).first()
        mt = _setup_approved_merchant(client, db, "m1@t.com", "01012345679")
        from models.user import User
        admin = db.query(User).first()
        oid = _create_order_and_assign(client, db, mt, driver.id, admin.id)
        client.post(
            f"/api/v1/drivers/tasks/{oid}/accept",
            headers={"Authorization": f"Bearer {token}"},
        )
        return token, oid

    def test_valid_transition_assigned_to_picked_up(self, client, db):
        token, oid = self._setup_and_accept(client, db)
        resp = client.put(
            f"/api/v1/drivers/tasks/{oid}/status",
            json={"status": "picked_up"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "picked_up"

    def test_valid_transition_picked_up_to_in_transit(self, client, db):
        token, oid = self._setup_and_accept(client, db)
        client.put(
            f"/api/v1/drivers/tasks/{oid}/status",
            json={"status": "picked_up"},
            headers={"Authorization": f"Bearer {token}"},
        )
        resp = client.put(
            f"/api/v1/drivers/tasks/{oid}/status",
            json={"status": "in_transit"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "in_transit"

    def test_valid_transition_in_transit_to_delivered(self, client, db):
        token, oid = self._setup_and_accept(client, db)
        client.put(
            f"/api/v1/drivers/tasks/{oid}/status",
            json={"status": "picked_up"},
            headers={"Authorization": f"Bearer {token}"},
        )
        client.put(
            f"/api/v1/drivers/tasks/{oid}/status",
            json={"status": "in_transit"},
            headers={"Authorization": f"Bearer {token}"},
        )
        resp = client.put(
            f"/api/v1/drivers/tasks/{oid}/status",
            json={"status": "delivered"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "delivered"

    def test_skip_status_returns_400(self, client, db):
        """Cannot skip from assigned directly to in_transit."""
        token, oid = self._setup_and_accept(client, db)
        resp = client.put(
            f"/api/v1/drivers/tasks/{oid}/status",
            json={"status": "in_transit"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"]["code"] == "INVALID_STATUS_TRANSITION"

    def test_financial_transactions_created_on_delivery(self, client, db):
        """On delivery, two financial_transactions created."""
        token, oid = self._setup_and_accept(client, db)
        for s in ["picked_up", "in_transit", "delivered"]:
            client.put(
                f"/api/v1/drivers/tasks/{oid}/status",
                json={"status": s},
                headers={"Authorization": f"Bearer {token}"},
            )
        db.expire_all()
        txns = db.query(FinancialTransaction).filter(
            FinancialTransaction.related_order_id == oid
        ).all()
        assert len(txns) == 2
        types = {t.transaction_type for t in txns}
        assert "order_commission" in types
        assert "driver_payout" in types
        # Commission from config
        from config import settings
        commission = [t for t in txns if t.transaction_type == "order_commission"][0]
        assert float(commission.amount_egp) == settings.platform_commission_egp
        payout = [t for t in txns if t.transaction_type == "driver_payout"][0]
        assert float(payout.amount_egp) == settings.driver_payout_egp

    def test_is_on_delivery_false_after_delivery(self, client, db):
        token, oid = self._setup_and_accept(client, db)
        for s in ["picked_up", "in_transit", "delivered"]:
            client.put(
                f"/api/v1/drivers/tasks/{oid}/status",
                json={"status": s},
                headers={"Authorization": f"Bearer {token}"},
            )
        db.expire_all()
        driver = db.query(Driver).first()
        assert driver.is_on_delivery is False

    def test_unauthorized_driver_cannot_update(self, client, db):
        """Non-assigned driver cannot update status."""
        token_a = _setup_approved_driver(client, db, "da@t.com", "01012345670")
        token_b = _setup_approved_driver(client, db, "db@t.com", "01012345671")
        from models.user import User
        ub = db.query(User).filter(User.email == "db@t.com").first()
        driver_b = db.query(Driver).filter(Driver.user_id == ub.id).first()
        mt = _setup_approved_merchant(client, db, "m1@t.com", "01012345679")
        admin = db.query(User).first()
        oid = _create_order_and_assign(client, db, mt, driver_b.id, admin.id)
        # Driver B accepts
        client.post(
            f"/api/v1/drivers/tasks/{oid}/accept",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        # Driver A tries to update status
        resp = client.put(
            f"/api/v1/drivers/tasks/{oid}/status",
            json={"status": "picked_up"},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert resp.status_code == 403


class TestEarnings:
    """Task 3.6 — Driver earnings dashboard."""

    def test_earnings_empty(self, client, db):
        token = _setup_approved_driver(client, db)
        resp = client.get(
            "/api/v1/drivers/earnings?period=week",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total_earnings_egp"] == 0.0
        assert data["order_count"] == 0

    def test_earnings_after_delivery(self, client, db):
        token = _setup_approved_driver(client, db)
        driver = db.query(Driver).first()
        mt = _setup_approved_merchant(client, db, "m1@t.com", "01012345679")
        from models.user import User
        admin = db.query(User).first()
        oid = _create_order_and_assign(client, db, mt, driver.id, admin.id)
        client.post(
            f"/api/v1/drivers/tasks/{oid}/accept",
            headers={"Authorization": f"Bearer {token}"},
        )
        for s in ["picked_up", "in_transit", "delivered"]:
            client.put(
                f"/api/v1/drivers/tasks/{oid}/status",
                json={"status": s},
                headers={"Authorization": f"Bearer {token}"},
            )

        resp = client.get(
            "/api/v1/drivers/earnings?period=week",
            headers={"Authorization": f"Bearer {token}"},
        )
        data = resp.json()["data"]
        from config import settings
        assert data["order_count"] == 1
        assert data["total_earnings_egp"] == settings.driver_payout_egp
        assert data["pending_payout_egp"] == settings.driver_payout_egp

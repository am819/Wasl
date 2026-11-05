"""Tests for fixed Task 4.5 — Settlement Records (roadmap-compliant)."""

from datetime import date, timedelta
from models.audit_log import AuditLog
from models.financial_transaction import FinancialTransaction
from models.settlement_record import SettlementRecord
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


def _create_driver_payout_txn(db, driver_id):
    """Create a pending driver_payout transaction directly."""
    txn = FinancialTransaction(
        transaction_type="driver_payout",
        related_driver_id=driver_id,
        amount_egp=10.0,
        status="pending",
    )
    db.add(txn)
    db.commit()
    db.expire_all()
    return txn


class TestSettlementRecords:
    def test_create_settlement_record(self, client, db):
        """POST /admin/settlements creates a settlement_record in the DB."""
        admin_token = _setup_admin(client, db)
        today = date.today()
        resp = client.post(
            "/api/v1/admin/settlements",
            json={
                "settlement_type": "driver",
                "recipient_id": 99,
                "period_start": str(today - timedelta(days=7)),
                "period_end": str(today),
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["settlement_type"] == "driver"
        assert "id" in data
        assert data["status"] == "pending"
        # Verify persisted to DB
        db.expire_all()
        record = db.get(SettlementRecord, data["id"])
        assert record is not None
        assert record.status == "pending"

    def test_settlement_total_equals_sum_of_transactions(self, client, db):
        """Total in settlement record must equal sum of matching transactions."""
        from models.driver import Driver
        from security.password import hash_password
        # Create a driver directly
        driver_user = User(
            email="d_settle@wasl.eg", phone="01099999991",
            password_hash=hash_password("Dummy1!"),
            role="driver", status="approved",
        )
        db.add(driver_user)
        db.flush()
        driver = Driver(
            user_id=driver_user.id,
            full_name="Driver Settlement",
            national_id_number="settle_driver_id",
            vehicle_type="motorcycle",
        )
        db.add(driver)
        db.commit()
        db.expire_all()

        # Create two pending payout transactions
        for _ in range(2):
            _create_driver_payout_txn(db, driver.id)

        admin_token = _setup_admin(client, db)
        today = date.today()
        resp = client.post(
            "/api/v1/admin/settlements",
            json={
                "settlement_type": "driver",
                "recipient_id": driver.id,
                "period_start": str(today - timedelta(days=7)),
                "period_end": str(today),
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        # Total should be 2 × 10 EGP = 20 EGP
        assert resp.json()["data"]["total_amount_egp"] == 20.0

    def test_list_settlement_records(self, client, db):
        """GET /admin/settlements returns records from settlement_records table."""
        admin_token = _setup_admin(client, db)
        today = date.today()
        # Create one record
        client.post(
            "/api/v1/admin/settlements",
            json={
                "settlement_type": "driver",
                "recipient_id": 1,
                "period_start": str(today - timedelta(days=7)),
                "period_end": str(today),
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        resp = client.get(
            "/api/v1/admin/settlements",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["total_count"] >= 1
        record = resp.json()["data"]["settlements"][0]
        assert "id" in record
        assert "settlement_type" in record

    def test_process_settlement_by_id(self, client, db):
        """POST /admin/settlements/{id}/process marks record completed."""
        from models.driver import Driver
        from security.password import hash_password
        driver_user = User(
            email="d_proc@wasl.eg", phone="01099999992",
            password_hash=hash_password("Dummy1!"),
            role="driver", status="approved",
        )
        db.add(driver_user)
        db.flush()
        driver = Driver(
            user_id=driver_user.id,
            full_name="Driver Process",
            national_id_number="proc_driver_id",
            vehicle_type="motorcycle",
        )
        db.add(driver)
        db.commit()
        db.expire_all()

        _create_driver_payout_txn(db, driver.id)

        admin_token = _setup_admin(client, db)
        today = date.today()
        create_resp = client.post(
            "/api/v1/admin/settlements",
            json={
                "settlement_type": "driver",
                "recipient_id": driver.id,
                "period_start": str(today - timedelta(days=7)),
                "period_end": str(today),
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        settlement_id = create_resp.json()["data"]["id"]

        resp = client.post(
            f"/api/v1/admin/settlements/{settlement_id}/process",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "completed"

        # Verify the record in DB
        db.expire_all()
        record = db.get(SettlementRecord, settlement_id)
        assert record.status == "completed"
        assert record.processed_at is not None

        # Verify the underlying transactions are completed
        txns = db.query(FinancialTransaction).filter(
            FinancialTransaction.related_driver_id == driver.id,
        ).all()
        assert all(t.status == "completed" for t in txns)

    def test_process_settlement_logged_to_audit(self, client, db):
        admin_token = _setup_admin(client, db)
        today = date.today()
        create_resp = client.post(
            "/api/v1/admin/settlements",
            json={
                "settlement_type": "driver",
                "recipient_id": 1,
                "period_start": str(today - timedelta(days=7)),
                "period_end": str(today),
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        sid = create_resp.json()["data"]["id"]
        client.post(
            f"/api/v1/admin/settlements/{sid}/process",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        db.expire_all()
        log = db.query(AuditLog).filter(
            AuditLog.action == "process_settlement",
            AuditLog.entity_id == sid,
        ).first()
        assert log is not None

    def test_cannot_process_already_completed(self, client, db):
        admin_token = _setup_admin(client, db)
        today = date.today()
        create_resp = client.post(
            "/api/v1/admin/settlements",
            json={
                "settlement_type": "driver",
                "recipient_id": 1,
                "period_start": str(today - timedelta(days=7)),
                "period_end": str(today),
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        sid = create_resp.json()["data"]["id"]
        # Process once
        client.post(
            f"/api/v1/admin/settlements/{sid}/process",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        # Try again — should fail
        resp = client.post(
            f"/api/v1/admin/settlements/{sid}/process",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 400

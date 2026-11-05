"""Tests for Task 4.2 — Driver Approval Workflow."""

from models.audit_log import AuditLog
from models.driver import Driver
from models.user import User


def _setup_admin(client, db):
    from security.password import hash_password
    from services.auth_service import reset_lockout_for_test
    reset_lockout_for_test("admin@wasl.eg")
    admin = User(
        email="admin@wasl.eg",
        phone="01000000000",
        password_hash=hash_password("AdminPass1!"),
        role="admin",
        status="approved",
    )
    db.add(admin)
    db.commit()
    db.expire_all()
    resp = client.post("/api/v1/auth/login", json={
        "email": "admin@wasl.eg", "password": "AdminPass1!",
    })
    assert resp.status_code == 200, f"Admin login: {resp.text}"
    return resp.json()["data"]["token"]


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


def _get_driver_id(db, email):
    u = db.query(User).filter(User.email == email).first()
    d = db.query(Driver).filter(Driver.user_id == u.id).first()
    return d.id


class TestDriverApproval:
    def test_list_pending_drivers(self, client, db):
        admin_token = _setup_admin(client, db)
        _setup_driver(client)
        resp = client.get(
            "/api/v1/admin/drivers?status=pending",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["total_count"] >= 1

    def test_approve_driver(self, client, db):
        admin_token = _setup_admin(client, db)
        _setup_driver(client, "d2@t.com", "01012345679")
        did = _get_driver_id(db, "d2@t.com")
        resp = client.post(
            f"/api/v1/admin/drivers/{did}/approve",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "approved"
        db.expire_all()
        u = db.query(User).filter(User.email == "d2@t.com").first()
        assert u.status == "approved"

    def test_reject_driver(self, client, db):
        admin_token = _setup_admin(client, db)
        _setup_driver(client, "d3@t.com", "01012345680")
        did = _get_driver_id(db, "d3@t.com")
        resp = client.post(
            f"/api/v1/admin/drivers/{did}/reject",
            json={"rejection_reason": "Expired license"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "rejected"

    def test_approval_logged_to_audit(self, client, db):
        admin_token = _setup_admin(client, db)
        _setup_driver(client, "d4@t.com", "01012345681")
        did = _get_driver_id(db, "d4@t.com")
        client.post(
            f"/api/v1/admin/drivers/{did}/approve",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        db.expire_all()
        log = db.query(AuditLog).filter(
            AuditLog.action == "approve_driver",
            AuditLog.entity_id == did,
        ).first()
        assert log is not None

    def test_non_admin_cannot_approve(self, client, db):
        _setup_driver(client, "d5@t.com", "01012345682")
        driver_token = client.post("/api/v1/auth/login", json={
            "email": "d5@t.com", "password": "SecurePass1!",
        }).json()["data"]["token"]
        resp = client.post(
            "/api/v1/admin/drivers/1/approve",
            headers={"Authorization": f"Bearer {driver_token}"},
        )
        assert resp.status_code == 403

"""Tests for Task 4.1 — Merchant Approval Workflow."""

from models.audit_log import AuditLog
from models.user import User


def _setup_admin(client, db):
    """Create an admin user directly in the DB."""
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
    assert resp.status_code == 200, f"Admin login failed: {resp.text}"
    return resp.json()["data"]["token"]


def _setup_merchant(client, email="m1@t.com", phone="01012345678"):
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
    return t


def _get_merchant_id(db, email):
    """Helper to find merchant ID by email."""
    from models.merchant import Merchant
    from models.user import User as U
    u = db.query(U).filter(U.email == email).first()
    m = db.query(Merchant).filter(Merchant.user_id == u.id).first()
    return m.id


class TestMerchantApproval:
    def test_list_pending_merchants(self, client, db):
        admin_token = _setup_admin(client, db)
        _setup_merchant(client)  # creates pending merchant
        resp = client.get(
            "/api/v1/admin/merchants?status=pending",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total_count"] >= 1
        assert all(m["status"] == "pending" for m in data["merchants"])

    def test_approve_merchant(self, client, db):
        admin_token = _setup_admin(client, db)
        _setup_merchant(client)
        mid = _get_merchant_id(db, "m1@t.com")
        resp = client.post(
            f"/api/v1/admin/merchants/{mid}/approve",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "approved"
        # Verify in DB
        db.expire_all()
        u = db.query(User).filter(User.email == "m1@t.com").first()
        assert u.status == "approved"

    def test_reject_merchant(self, client, db):
        admin_token = _setup_admin(client, db)
        _setup_merchant(client, "m2@t.com", "01012345679")
        mid = _get_merchant_id(db, "m2@t.com")
        resp = client.post(
            f"/api/v1/admin/merchants/{mid}/reject",
            json={"rejection_reason": "Invalid documentation"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "rejected"

    def test_approval_logged_to_audit(self, client, db):
        admin_token = _setup_admin(client, db)
        _setup_merchant(client, "m3@t.com", "01012345680")
        mid = _get_merchant_id(db, "m3@t.com")
        client.post(
            f"/api/v1/admin/merchants/{mid}/approve",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        db.expire_all()
        log = db.query(AuditLog).filter(
            AuditLog.action == "approve_merchant",
            AuditLog.entity_id == mid,
        ).first()
        assert log is not None
        assert log.new_values["status"] == "approved"

    def test_non_admin_cannot_approve(self, client, db):
        _setup_merchant(client, "m4@t.com", "01012345681")
        merchant_token = client.post("/api/v1/auth/login", json={
            "email": "m4@t.com", "password": "SecurePass1!",
        }).json()["data"]["token"]
        resp = client.post(
            "/api/v1/admin/merchants/1/approve",
            headers={"Authorization": f"Bearer {merchant_token}"},
        )
        assert resp.status_code == 403

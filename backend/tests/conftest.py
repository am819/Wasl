"""
Pytest fixtures for WASL backend tests.

Uses a separate wasl_test database. Tables are truncated before each
test so services can call db.commit() freely without transaction
isolation issues.
"""

import os

# ── MUST be set before any backend module is imported ───────────────────
os.environ["DATABASE_URL"] = (
    "postgresql://postgres:postgres@localhost:5432/wasl_test"
)
os.environ["JWT_SECRET_KEY"] = "test-only-secret-not-for-production-xxxxx"
os.environ["ENCRYPTION_KEY"] = "hY21ckPKI40Ty5M4ZZzUrgQpAxsXwrDcwrSRk15ExH8="
os.environ["ENVIRONMENT"] = "development"
os.environ["LOG_LEVEL"] = "WARNING"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from database import get_db  # noqa: E402
from main import app  # noqa: E402

_TEST_DB_URL = os.environ["DATABASE_URL"]
_engine = create_engine(_TEST_DB_URL, echo=False)
_TestingSession = sessionmaker(bind=_engine, autocommit=False, autoflush=False)

# All tables to truncate (order doesn't matter with CASCADE)
_TRUNCATE_SQL = (
    "TRUNCATE TABLE users, user_sessions, audit_logs, "
    "merchants, drivers, orders, order_items, "
    "order_status_history, driver_assignments, "
    "delivery_tracking, tracking_tokens, "
    "financial_transactions, settlement_records, "
    "support_tickets RESTART IDENTITY CASCADE"
)


@pytest.fixture(autouse=True)
def _clean_tables():
    """Truncate all tables before each test so services can commit freely."""
    with _engine.connect() as conn:
        conn.execute(text(_TRUNCATE_SQL))
        conn.commit()
    yield


@pytest.fixture()
def db():
    """Yield a DB session.  Truncate-before-test ensures a clean slate."""
    session = _TestingSession()
    yield session
    session.close()


@pytest.fixture()
def client(db):
    """FastAPI TestClient with the test DB session injected."""
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


# ── Convenience fixtures ─────────────────────────────────────────────────
@pytest.fixture()
def registered_merchant(client):
    resp = client.post("/api/v1/auth/register", json={
        "email": "merchant@test.com",
        "phone": "01012345678",
        "password": "SecurePass1!",
        "role": "merchant",
    })
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


@pytest.fixture()
def registered_driver(client):
    resp = client.post("/api/v1/auth/register", json={
        "email": "driver@test.com",
        "phone": "01112345678",
        "password": "SecurePass1!",
        "role": "driver",
    })
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


@pytest.fixture()
def merchant_tokens(client, registered_merchant):
    from services.auth_service import reset_lockout_for_test
    reset_lockout_for_test("merchant@test.com")
    resp = client.post("/api/v1/auth/login", json={
        "email": "merchant@test.com",
        "password": "SecurePass1!",
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    data["user_id"] = registered_merchant["user_id"]
    return data

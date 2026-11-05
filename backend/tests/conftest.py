"""
Pytest fixtures for WASL backend tests.

Uses a separate wasl_test database. The environment variables must be set
BEFORE any backend module is imported, because config.py calls Settings()
at module level. We achieve this by setting them here at the top of conftest
and relying on pytest to load conftest.py before collecting tests.
"""

import os

# ── MUST be set before any backend module is imported ───────────────────
# These take priority over any .env file because pydantic-settings checks
# os.environ before reading env_file.
os.environ["DATABASE_URL"] = (
    "postgresql://postgres:postgres@localhost:5432/wasl_test"
)
os.environ["JWT_SECRET_KEY"] = "test-only-secret-not-for-production-xxxxx"
os.environ["ENCRYPTION_KEY"] = "hY21ckPKI40Ty5M4ZZzUrgQpAxsXwrDcwrSRk15ExH8="
os.environ["ENVIRONMENT"] = "development"
os.environ["LOG_LEVEL"] = "WARNING"

# ── Now it is safe to import backend modules ─────────────────────────────
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from database import get_db  # noqa: E402
from main import app  # noqa: E402

# ── Test engine ───────────────────────────────────────────────────────────
_TEST_DB_URL = os.environ["DATABASE_URL"]
_engine = create_engine(_TEST_DB_URL, echo=False)
_TestingSession = sessionmaker(bind=_engine, autocommit=False, autoflush=False)


# ── Session-scoped: verify migrations ran on wasl_test ──────────────────
@pytest.fixture(scope="session", autouse=True)
def ensure_tables():
    with _engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT tablename FROM pg_tables "
                "WHERE schemaname='public'"
            )
        )
        tables = {r[0] for r in result}
    required = {"users", "user_sessions", "audit_logs"}
    missing = required - tables
    assert not missing, (
        f"Missing tables in wasl_test: {missing}. "
        "Run: alembic upgrade head"
    )


# ── Per-test DB session (rolls back after each test) ────────────────────
@pytest.fixture()
def db():
    connection = _engine.connect()
    transaction = connection.begin()
    session = _TestingSession(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


# ── TestClient with overridden DB session ────────────────────────────────
@pytest.fixture()
def client(db):
    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
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
    resp = client.post("/api/v1/auth/login", json={
        "email": "merchant@test.com",
        "password": "SecurePass1!",
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    data["user_id"] = registered_merchant["user_id"]
    return data

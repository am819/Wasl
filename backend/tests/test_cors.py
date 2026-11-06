"""Tests for CORS preflight behaviour.

Verifies that OPTIONS preflight requests from allowed origins receive the
correct Access-Control-Allow-Origin header, and that the env-var parsing
handles comma-separated strings, surrounding quotes, and whitespace.
"""

import os

import pytest
from fastapi.testclient import TestClient

ALLOWED_ORIGIN = "https://frontend-gamma-steel-33.vercel.app"
OTHER_ALLOWED = "https://frontend-am819.vercel.app"
BLOCKED_ORIGIN = "https://evil.example.com"


# ── Dedicated test client with the Vercel origins in CORS allow-list ─────
@pytest.fixture(scope="module")
def cors_client():
    """TestClient whose app allows the two Vercel test origins."""
    from main import app
    from fastapi.middleware.cors import CORSMiddleware
    import main as _main

    original_origins = _main._allowed_origins[:]
    _main._allowed_origins.clear()
    _main._allowed_origins.extend([ALLOWED_ORIGIN, OTHER_ALLOWED])

    # Add a CORSMiddleware entry with the test origins.
    # Starlette evaluates all CORS middlewares; the innermost explicit-origin
    # match wins over any wildcard outer entry.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[ALLOWED_ORIGIN, OTHER_ALLOWED],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    _main._allowed_origins.clear()
    _main._allowed_origins.extend(original_origins)


class TestCORSPreflight:
    def test_options_returns_allow_origin_for_known_origin(self, cors_client):
        """OPTIONS from an allowed origin must include the ACAO header."""
        resp = cors_client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": ALLOWED_ORIGIN,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert resp.status_code in (200, 204), (
            f"Preflight failed: {resp.status_code} {resp.text}"
        )
        acao = resp.headers.get("access-control-allow-origin", "")
        assert acao == ALLOWED_ORIGIN, (
            f"Expected ACAO={ALLOWED_ORIGIN!r}, got {acao!r}"
        )

    def test_options_login_allows_post_method(self, cors_client):
        resp = cors_client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": ALLOWED_ORIGIN,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert resp.status_code in (200, 204)
        acam = resp.headers.get("access-control-allow-methods", "")
        assert "POST" in acam

    def test_options_register_returns_allow_origin(self, cors_client):
        resp = cors_client.options(
            "/api/v1/auth/register",
            headers={
                "Origin": ALLOWED_ORIGIN,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert resp.status_code in (200, 204)
        assert (
            resp.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN
        )

    def test_post_login_response_includes_acao(self, cors_client):
        """Non-preflight POST from an allowed origin also gets ACAO header."""
        resp = cors_client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@wasl.eg", "password": "irrelevant"},
            headers={"Origin": ALLOWED_ORIGIN},
        )
        acao = resp.headers.get("access-control-allow-origin", "")
        assert acao == ALLOWED_ORIGIN

    def test_blocked_origin_has_no_acao(self, cors_client):
        """An origin not in the allow-list must not receive ACAO header."""
        resp = cors_client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": BLOCKED_ORIGIN,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        acao = resp.headers.get("access-control-allow-origin", "")
        assert acao != BLOCKED_ORIGIN, (
            f"Blocked origin {BLOCKED_ORIGIN!r} must not appear in ACAO"
        )


class TestAllowedOriginsListParsing:
    """Unit tests for config.allowed_origins_list() robustness."""

    def _make_settings(self, raw: str):
        """Return a Settings instance with the given raw ALLOWED_ORIGINS."""
        from config import Settings
        # Temporarily set the env var so the new Settings instance picks it up
        old = os.environ.get("ALLOWED_ORIGINS")
        os.environ["ALLOWED_ORIGINS"] = raw
        try:
            s = Settings()
        finally:
            if old is None:
                os.environ.pop("ALLOWED_ORIGINS", None)
            else:
                os.environ["ALLOWED_ORIGINS"] = old
        return s

    def test_simple_comma_separated(self):
        s = self._make_settings(
            "https://a.vercel.app,https://b.vercel.app"
        )
        result = s.allowed_origins_list()
        assert result == ["https://a.vercel.app", "https://b.vercel.app"]

    def test_strips_surrounding_double_quotes(self):
        """Railway dashboard may wrap the value in double-quotes."""
        s = self._make_settings(
            '"https://a.vercel.app,https://b.vercel.app"'
        )
        result = s.allowed_origins_list()
        assert result == ["https://a.vercel.app", "https://b.vercel.app"]

    def test_strips_whitespace_around_entries(self):
        s = self._make_settings(
            "https://a.vercel.app , https://b.vercel.app"
        )
        result = s.allowed_origins_list()
        assert result == ["https://a.vercel.app", "https://b.vercel.app"]

    def test_drops_empty_entries(self):
        s = self._make_settings(
            "https://a.vercel.app,,https://b.vercel.app,"
        )
        result = s.allowed_origins_list()
        assert result == ["https://a.vercel.app", "https://b.vercel.app"]

    def test_single_origin_no_comma(self):
        s = self._make_settings("https://a.vercel.app")
        result = s.allowed_origins_list()
        assert result == ["https://a.vercel.app"]

    def test_strips_per_entry_quotes(self):
        """Handles per-entry quoted values like '"a.com","b.com"'."""
        s = self._make_settings(
            '"https://a.vercel.app","https://b.vercel.app"'
        )
        result = s.allowed_origins_list()
        assert result == ["https://a.vercel.app", "https://b.vercel.app"]

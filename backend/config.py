"""
WASL application configuration.

All settings are read from environment variables.
Copy .env.example to .env and fill in real values for local development.
Never hardcode secrets in this file.

Development vs. production behaviour differences:
  development  — DEBUG logging, Swagger /docs and /redoc exposed,
                 placeholder secret values accepted, SQLAlchemy echo on
  production   — INFO/WARNING logging, /docs and /redoc hidden,
                 placeholder secrets raise a startup error, SQLAlchemy echo off
"""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PLACEHOLDER_SECRETS = {"CHANGE_ME_BEFORE_USE", "CHANGE_ME_IN_PRODUCTION_MIN_32_CHARS"}


class Settings(BaseSettings):
    # ── Application ────────────────────────────────────────────────────────
    environment: str = "development"
    log_level: str = "DEBUG"

    # ── Database (required, no default) ───────────────────────────────────
    database_url: str

    # ── Authentication ─────────────────────────────────────────────────────
    # Placeholder is safe in development; raises on startup in production.
    jwt_secret_key: str = "CHANGE_ME_BEFORE_USE"

    # ── Field encryption ───────────────────────────────────────────────────
    encryption_key: str = "CHANGE_ME_BEFORE_USE"

    # ── CORS ───────────────────────────────────────────────────────────────
    # Comma-separated list of allowed origins.
    # Default covers the two production Vercel deployments and local dev.
    allowed_origins: str = (
        "https://frontend-gamma-steel-33.vercel.app,"
        "https://frontend-am819.vercel.app,"
        "http://localhost:3000"
    )

    # ── Financial (unverified assumptions — see BUSINESS_MODEL.md) ─────────
    # All amounts in EGP. Change here to adjust platform economics globally.
    delivery_fee_egp: float = 15.0          # charged to merchant per order
    platform_commission_egp: float = 5.0    # WASL keeps per delivered order
    driver_payout_egp: float = 10.0         # driver earns per delivery

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Validators ─────────────────────────────────────────────────────────

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"environment must be one of {allowed}, got '{v}'")
        return v

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret(cls, v: str, info) -> str:
        env = (info.data or {}).get("environment", "development")
        if env == "production" and v in _PLACEHOLDER_SECRETS:
            raise ValueError(
                "JWT_SECRET_KEY must be set to a real secret in production. "
                "Generate: python -c \"import secrets; "
                "print(secrets.token_urlsafe(32))\""
            )
        return v

    @field_validator("encryption_key")
    @classmethod
    def validate_encryption_key(cls, v: str, info) -> str:
        env = (info.data or {}).get("environment", "development")
        if env == "production" and v in _PLACEHOLDER_SECRETS:
            raise ValueError(
                "ENCRYPTION_KEY must be set to a real secret in production. "
                "Generate with: python -c \"from cryptography.fernet import Fernet; "
                "print(Fernet.generate_key().decode())\""
            )
        return v

    # ── Derived helpers ────────────────────────────────────────────────────

    def allowed_origins_list(self) -> list[str]:
        """Return CORS origins as a cleaned list.

        Handles the Railway/Vercel dashboard quirk where the env var value
        may be stored with surrounding double-quotes, e.g.:
            '"https://a.vercel.app,https://b.vercel.app"'
        Strip outer quotes, split on commas, strip whitespace, drop empties.
        Falls back to the field default when the value is empty or whitespace.
        """
        raw = self.allowed_origins.strip().strip('"').strip("'")
        entries = [
            o.strip().strip('"').strip("'")
            for o in raw.split(",")
            if o.strip()
        ]
        if not entries:
            # Value was empty or whitespace-only — use the field default
            default = Settings.model_fields["allowed_origins"].default
            entries = [
                o.strip().strip('"').strip("'")
                for o in default.split(",")
                if o.strip()
            ]
        return entries

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def docs_enabled(self) -> bool:
        """Swagger /docs and /redoc only exposed in non-production."""
        return not self.is_production

    @property
    def sqlalchemy_echo(self) -> bool:
        """Log SQL queries only in development."""
        return self.environment == "development"


# Single shared instance — import this everywhere
settings = Settings()

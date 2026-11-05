"""
WASL application configuration.

All settings are read from environment variables.
Copy .env.example to .env and fill in real values for local development.
Never hardcode secrets in this file.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application
    environment: str = "development"
    log_level: str = "DEBUG"

    # Database — required, no default
    database_url: str

    # Authentication — required in production, placeholder safe for skeleton
    jwt_secret_key: str = "CHANGE_ME_BEFORE_USE"

    # Field encryption — required in production
    encryption_key: str = "CHANGE_ME_BEFORE_USE"

    # CORS — comma-separated origins
    allowed_origins: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def allowed_origins_list(self) -> list[str]:
        """Return CORS origins as a list."""
        return [o.strip() for o in self.allowed_origins.split(",")]


# Single shared instance — import this everywhere
settings = Settings()

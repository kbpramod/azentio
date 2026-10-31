import os
from pathlib import Path
from typing import List, Optional, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Ensure .env is discovered whether run from /server or workspace root
SERVER_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = SERVER_DIR / ".env"


class Settings(BaseSettings):
    PROJECT_NAME: str = "Azentio Banking System"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = True
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # Database: Exclusively PostgreSQL (Neon)
    DATABASE_URL: str = ""

    # Authentication & JWT
    SECRET_KEY: str = "azentio-banking-jwt-secret-key-change-in-production-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15        # Short-lived access token
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7          # 7-day refresh token

    # Cookie Security Settings
    COOKIE_ACCESS_NAME: str = "azentio_access_token"
    COOKIE_REFRESH_NAME: str = "azentio_refresh_token"
    COOKIE_SAMESITE: str = "lax"
    COOKIE_SECURE: bool = False                 # True in production HTTPS

    # Better Auth Configuration (if needed)
    BETTER_AUTH_SECRET: Optional[str] = None
    BETTER_AUTH_API_KEY: Optional[str] = None

    # AI Credits API
    AICREDITS_API_KEY: Optional[str] = None
    AICREDITS_BASE_URL: str = "https://api.aicredits.com/v1"

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_url(cls, v: str) -> str:
        if not v or not v.strip():
            return ""

        url = v.strip().strip('"').strip("'")
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

        # Remove sslmode query parameter if present, handled via asyncpg connect_args
        if "?sslmode=" in url:
            parts = url.split("?sslmode=")
            url = parts[0]
        elif "&sslmode=" in url:
            parts = url.split("&sslmode=")
            url = parts[0]

        return url

    model_config = SettingsConfigDict(
        env_file=(str(ENV_PATH), ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()

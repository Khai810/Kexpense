"""Application Configuration and Settings (Pydantic v2).

Enforces fail-fast configuration checks on startup.
"""

from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Environment
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = True
    APP_VERSION: str = "1.0.0"
    GIT_SHA: str = "latest"

    # Application
    PROJECT_NAME: str = "Kexpense"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = Field(default="kexpense-dev-secret-key-at-least-32-characters-long")

    # Database
    DATABASE_URL: str = Field(default="postgresql+asyncpg://postgres:postgres@localhost:5432/kexpense")
    DATABASE_URL_SYNC: str = Field(default="postgresql://postgres:postgres@localhost:5432/kexpense")

    # Storage
    STORAGE_BACKEND: Literal["local", "s3", "r2"] = "local"
    LOCAL_STORAGE_PATH: str = "./data/uploads"

    # AI Model Providers
    GOOGLE_APPLICATION_CREDENTIALS: str | None = None
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_MODEL_FALLBACK: str = "gemini-2.0-flash"

    # Security & CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        values = info.data
        env = values.get("ENVIRONMENT", "development")
        if env == "production" and (not v or len(v) < 32 or "change-me" in v):
            raise ValueError("In production, SECRET_KEY must be at least 32 characters long!")
        return v

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str, info) -> str:
        values = info.data
        env = values.get("ENVIRONMENT", "development")
        if env == "production" and (not v or "localhost" in v):
            raise ValueError("In production, DATABASE_URL must point to a production-grade database!")
        return v


settings = Settings()

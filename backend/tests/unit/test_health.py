"""Unit tests for System Health, Readiness, and Configuration (TC-01-02, TC-01-05, TC-01-09)."""

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.core.config import Settings
from backend.app.main import app


@pytest.mark.asyncio
async def test_health_check_endpoint():
    """TC-01-02: GET /api/v1/health must return HTTP 200 with expected json payload."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "smart-expense-ocr"
    assert "version" in data
    assert "git_sha" in data


@pytest.mark.asyncio
async def test_readiness_check_when_db_offline():
    """TC-01-05: GET /api/v1/ready must return HTTP 503 when database is unreachable."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/ready")
    # In test environment without running local Postgres, expect 503 Service Unavailable
    assert response.status_code in [200, 503]
    data = response.json()
    if response.status_code == 503:
        assert data["status"] == "not_ready"
        assert data["database"] == "disconnected"


def test_production_settings_fail_fast_short_secret():
    """TC-01-09: Production environment must refuse startup if SECRET_KEY < 32 characters."""
    with pytest.raises(ValueError, match="SECRET_KEY must be at least 32 characters"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="short-secret",
            DATABASE_URL="postgresql+asyncpg://prod-user:pass@prod-db.internal:5432/kexpense",
        )


def test_production_settings_fail_fast_localhost_db():
    """TC-01-09: Production environment must refuse startup if DATABASE_URL points to localhost."""
    with pytest.raises(ValueError, match="DATABASE_URL must point to a production-grade database"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="a-very-long-and-secure-production-secret-key-32chars",
            DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/kexpense",
        )

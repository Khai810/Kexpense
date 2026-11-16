"""Pytest configuration and global fixtures."""

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import app


@pytest.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

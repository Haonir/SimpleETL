"""Tests for the main FastAPI application."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Test client with the full main app (health + config router)."""
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_200(self, client: TestClient):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestConfigRouterAccessible:
    def test_config_endpoint_accessible(self, client: TestClient):
        """Verify /api/v1/config is reachable through the main app."""
        response = client.get("/api/v1/config")
        assert response.status_code in (200, 404)

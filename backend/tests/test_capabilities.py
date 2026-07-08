"""Tests for the /api/v1/capabilities endpoint."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Test client with the full main app."""
    return TestClient(app)


class TestCapabilitiesEndpoint:
    def test_capabilities_returns_200(self, client: TestClient):
        response = client.get("/api/v1/capabilities")
        assert response.status_code == 200

    def test_capabilities_has_ocr_available_field(self, client: TestClient):
        """Response must contain 'ocr_available' boolean field."""
        response = client.get("/api/v1/capabilities")
        data = response.json()
        assert "ocr_available" in data
        assert isinstance(data["ocr_available"], bool)

    def test_capabilities_has_supported_input_formats(self, client: TestClient):
        """Response must contain 'supported_input_formats' list field."""
        response = client.get("/api/v1/capabilities")
        data = response.json()
        assert "supported_input_formats" in data
        assert isinstance(data["supported_input_formats"], list)

"""
Pytest configuration and fixtures.
"""
import pytest
from fastapi.testclient import TestClient
from src.main import app


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
def mock_charger_metrics():
    """Mock charger metrics for testing."""
    return {
        "charger_id": "test-charger-1",
        "connector_status": "AVAILABLE",
        "energy_delivered": 100.5,
        "power": 7.2,
        "temperature": 25.0,
        "error_codes": [],
        "uptime_hours": 720.5,
        "total_sessions": 150,
    }


@pytest.fixture
def auth_headers(monkeypatch):
    """Auth headers for API tests."""
    from src.config.settings import settings

    monkeypatch.setattr(settings, "api_key", "test-api-key")
    return {
        "X-API-Key": "test-api-key",
        "X-Tenant-ID": "test-tenant",
    }

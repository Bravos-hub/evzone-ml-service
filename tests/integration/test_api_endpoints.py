"""
Integration tests for API endpoints.
"""
import pytest
from fastapi.testclient import TestClient


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_predictions_endpoint_requires_auth(client):
    """Test that predictions require authentication."""
    response = client.post("/api/v1/predictions/failure", json={})
    assert response.status_code == 401  # Unauthorized


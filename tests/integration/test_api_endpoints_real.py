"""
Integration tests for API endpoints using real models and cache paths.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from src.config.settings import settings
from src.main import app


def _auth_headers(tenant_id: str = "real-tenant") -> dict:
    return {
        settings.api_key_header: settings.api_key,
        settings.tenant_header: tenant_id,
    }


def test_predict_failure_real_models(client, mock_charger_metrics):
    headers = _auth_headers()
    payload = {
        "charger_id": "real-failure-1",
        "metrics": {**mock_charger_metrics, "charger_id": "real-failure-1"},
    }

    response = client.post("/api/v1/predictions/failure", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["charger_id"] == "real-failure-1"
    assert data["tenant_id"] == "real-tenant"
    assert 0.0 <= data["failure_probability"] <= 1.0
    assert data["recommended_action"] in {"IMMEDIATE", "WITHIN_7_DAYS", "WITHIN_30_DAYS"}
    assert data["predicted_failure_window"]["start"] is not None
    assert data["predicted_failure_window"]["end"] is not None


def test_predict_maintenance_real_models(client, mock_charger_metrics):
    headers = _auth_headers()
    payload = {
        "charger_id": "real-maintenance-1",
        "metrics": {**mock_charger_metrics, "charger_id": "real-maintenance-1"},
    }

    response = client.post("/api/v1/predictions/maintenance", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["charger_id"] == "real-maintenance-1"
    assert data["tenant_id"] == "real-tenant"
    assert data["urgency"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    assert data["estimated_downtime_hours"] >= 0.0
    assert data["recommended_date"] is not None


def test_detect_anomaly_real_models(client, mock_charger_metrics):
    headers = _auth_headers()
    hot_metrics = {**mock_charger_metrics, "charger_id": "real-anomaly-1", "temperature": 70.0}
    payload = {
        "charger_id": "real-anomaly-1",
        "metrics": hot_metrics,
    }

    response = client.post("/api/v1/predictions/anomaly", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["charger_id"] == "real-anomaly-1"
    assert data["tenant_id"] == "real-tenant"
    assert data["is_anomaly"] is True
    assert data["anomaly_type"] == "OVER_TEMPERATURE_CRITICAL"


def test_cached_prediction_roundtrip_real_cache(mock_charger_metrics):
    with TestClient(app) as local_client:
        health = local_client.get("/api/v1/health")
        assert health.status_code == 200
        cache_health = health.json().get("checks", {}).get("cache", {})
        if not cache_health.get("healthy"):
            pytest.skip("Redis cache not available; start Redis to run cache integration test.")

        tenant_id = "real-cache-tenant"
        headers = _auth_headers(tenant_id=tenant_id)
        charger_id = "real-cache-1"
        payload = {
            "charger_id": charger_id,
            "metrics": {**mock_charger_metrics, "charger_id": charger_id},
        }

        response = local_client.post("/api/v1/predictions/failure", json=payload, headers=headers)
        assert response.status_code == 200
        first = response.json()

        cached_response = local_client.get(f"/api/v1/predictions/{charger_id}", headers=headers)
        assert cached_response.status_code == 200
        cached = cached_response.json()

        assert cached["charger_id"] == charger_id
        assert cached["tenant_id"] == tenant_id
        assert cached["failure_probability"] == pytest.approx(first["failure_probability"])

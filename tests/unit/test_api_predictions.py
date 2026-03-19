"""
Unit tests for prediction API routes.
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

def test_predict_failure_success(client, auth_headers):
    mock_result = {
        "charger_id": "test-charger",
        "failure_probability": 0.1,
        "confidence": 0.9,
        "recommended_action": "WITHIN_30_DAYS",
        "recommendations": ["Check cable"],
        "predicted_failure_date": datetime.now(timezone.utc).isoformat(),
        "model_version": "v1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    from src.main import app
    from src.api.dependencies import get_prediction_service, get_model_manager, get_cache_service, get_feature_extractor

    mock_ps = MagicMock()
    async def async_predict_failure(*args, **kwargs):
        return mock_result
    mock_ps.predict_failure = async_predict_failure

    app.dependency_overrides[get_prediction_service] = lambda: mock_ps
    app.dependency_overrides[get_model_manager] = MagicMock()
    app.dependency_overrides[get_cache_service] = MagicMock()
    app.dependency_overrides[get_feature_extractor] = MagicMock()

    try:
        payload = {
            "charger_id": "test-charger",
            "metrics": {
                "charger_id": "test-charger",
                "connector_status": "AVAILABLE",
                "temperature": 25.0
            }
        }

        response = client.post("/api/v1/predictions/failure", json=payload, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["charger_id"] == "test-charger"
        assert data["failure_probability"] == 0.1
        assert data["recommended_action"] == "WITHIN_30_DAYS"
    finally:
        app.dependency_overrides.clear()

def test_predict_maintenance_success(client, auth_headers):
    mock_result = {
        "charger_id": "test-charger",
        "urgency": "LOW",
        "recommended_maintenance_datetime": datetime.now(timezone.utc).isoformat(),
        "estimated_downtime_hours": 2.0,
        "rationale": ["Routine check"],
        "model_version": "v1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    from src.main import app
    from src.api.dependencies import get_prediction_service, get_model_manager, get_cache_service, get_feature_extractor

    mock_ps = MagicMock()
    async def async_predict_maintenance(*args, **kwargs):
        return mock_result
    mock_ps.predict_maintenance = async_predict_maintenance
    app.dependency_overrides[get_prediction_service] = lambda: mock_ps
    app.dependency_overrides[get_model_manager] = MagicMock()
    app.dependency_overrides[get_cache_service] = MagicMock()
    app.dependency_overrides[get_feature_extractor] = MagicMock()

    try:
        payload = {
            "charger_id": "test-charger",
            "metrics": {
                "charger_id": "test-charger",
                "connector_status": "AVAILABLE"
            }
        }

        response = client.post("/api/v1/predictions/maintenance", json=payload, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["urgency"] == "LOW"
        assert data["estimated_downtime_hours"] == 2.0
    finally:
        app.dependency_overrides.clear()

def test_get_cached_prediction_success(client, auth_headers):
    mock_result = {
        "charger_id": "test-charger",
        "failure_probability": 0.1,
        "confidence": 0.9,
        "recommended_action_window": "WITHIN_30_DAYS",
        "model_version": "v1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    from src.main import app
    from src.api.dependencies import get_cache_service, get_model_manager, get_feature_extractor, get_prediction_service

    mock_cs = MagicMock()
    async def async_get_prediction(*args, **kwargs):
        return mock_result
    mock_cs.get_prediction = async_get_prediction
    app.dependency_overrides[get_cache_service] = lambda: mock_cs
    app.dependency_overrides[get_model_manager] = MagicMock()
    app.dependency_overrides[get_feature_extractor] = MagicMock()
    app.dependency_overrides[get_prediction_service] = MagicMock()

    try:
        response = client.get("/api/v1/predictions/test-charger", headers=auth_headers)

        assert response.status_code == 200
        assert response.json()["charger_id"] == "test-charger"
    finally:
        app.dependency_overrides.clear()

def test_get_cached_prediction_not_found(client, auth_headers):
    from src.main import app
    from src.api.dependencies import get_cache_service, get_model_manager, get_feature_extractor, get_prediction_service

    mock_cs = MagicMock()
    async def async_get_prediction(*args, **kwargs):
        return None
    mock_cs.get_prediction = async_get_prediction
    app.dependency_overrides[get_cache_service] = lambda: mock_cs
    app.dependency_overrides[get_model_manager] = MagicMock()
    app.dependency_overrides[get_feature_extractor] = MagicMock()
    app.dependency_overrides[get_prediction_service] = MagicMock()

    try:
        response = client.get("/api/v1/predictions/unknown", headers=auth_headers)

        assert response.status_code == 404
        assert "No cached prediction found" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()

def test_detect_anomaly_success(client, auth_headers):
    mock_result = {
        "charger_id": "test-charger",
        "is_anomaly": True,
        "anomaly_score": 85.5,
        "anomaly_type": "OVER_TEMPERATURE",
        "model_version": "v1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    from src.main import app
    from src.api.dependencies import get_prediction_service, get_model_manager, get_cache_service, get_feature_extractor

    mock_ps = MagicMock()
    async def async_detect_anomaly(*args, **kwargs):
        return mock_result
    mock_ps.detect_anomaly = async_detect_anomaly
    app.dependency_overrides[get_prediction_service] = lambda: mock_ps
    app.dependency_overrides[get_model_manager] = MagicMock()
    app.dependency_overrides[get_cache_service] = MagicMock()
    app.dependency_overrides[get_feature_extractor] = MagicMock()

    try:
        payload = {
            "charger_id": "test-charger",
            "metrics": {
                "charger_id": "test-charger",
                "connector_status": "CHARGING",
                "temperature": 65.0
            }
        }

        response = client.post("/api/v1/predictions/anomaly", json=payload, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["is_anomaly"] is True
        assert data["anomaly_type"] == "OVER_TEMPERATURE"
    finally:
        app.dependency_overrides.clear()

def test_batch_predictions_success(client, auth_headers):
    mock_result_1 = {
        "charger_id": "CHG_001",
        "failure_probability": 0.1,
        "confidence": 0.9,
        "recommended_action": "WITHIN_30_DAYS",
        "model_version": "v1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    mock_result_2 = {
        "charger_id": "CHG_002",
        "failure_probability": 0.8,
        "confidence": 0.85,
        "recommended_action": "IMMEDIATE",
        "model_version": "v1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    from src.main import app
    from src.api.dependencies import get_prediction_service, get_model_manager, get_cache_service, get_feature_extractor

    mock_ps = MagicMock()
    import asyncio
    async def async_mock(charger_id, *args, **kwargs):
        return mock_result_1 if charger_id == "CHG_001" else mock_result_2
    mock_ps.predict_failure = async_mock
    app.dependency_overrides[get_prediction_service] = lambda: mock_ps
    app.dependency_overrides[get_model_manager] = MagicMock()
    app.dependency_overrides[get_cache_service] = MagicMock()
    app.dependency_overrides[get_feature_extractor] = MagicMock()

    try:
        payload = {
            "prediction_type": "failure",
            "chargers": [
                {"charger_id": "CHG_001", "connector_status": "AVAILABLE"},
                {"charger_id": "CHG_002", "connector_status": "CHARGING"}
            ]
        }

        response = client.post("/api/v1/predictions/batch", json=payload, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["predictions"]) == 2
        assert data["predictions"][0]["charger_id"] == "CHG_001"
        assert data["predictions"][1]["charger_id"] == "CHG_002"
    finally:
        app.dependency_overrides.clear()

def test_prediction_failure_handles_exception(client, auth_headers):
    from src.main import app
    from src.api.dependencies import get_prediction_service, get_model_manager, get_cache_service, get_feature_extractor

    mock_ps = MagicMock()
    async def async_predict_failure(*args, **kwargs):
        raise Exception("Internal error")
    mock_ps.predict_failure = async_predict_failure
    app.dependency_overrides[get_prediction_service] = lambda: mock_ps
    app.dependency_overrides[get_model_manager] = MagicMock()
    app.dependency_overrides[get_cache_service] = MagicMock()
    app.dependency_overrides[get_feature_extractor] = MagicMock()

    try:
        payload = {
            "charger_id": "test-charger",
            "metrics": {
                "charger_id": "test-charger",
                "connector_status": "AVAILABLE"
            }
        }

        response = client.post("/api/v1/predictions/failure", json=payload, headers=auth_headers)

        assert response.status_code == 500
        assert "Prediction failed" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()

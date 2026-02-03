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

    with patch("src.services.prediction_service.PredictionService.predict_failure") as mock_predict:
        mock_predict.return_value = mock_result

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

    with patch("src.services.prediction_service.PredictionService.predict_maintenance") as mock_predict:
        mock_predict.return_value = mock_result

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

def test_get_cached_prediction_success(client, auth_headers):
    mock_result = {
        "charger_id": "test-charger",
        "failure_probability": 0.1,
        "confidence": 0.9,
        "recommended_action_window": "WITHIN_30_DAYS",
        "model_version": "v1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    with patch("src.services.cache_service.CacheService.get_prediction") as mock_get:
        mock_get.return_value = mock_result

        response = client.get("/api/v1/predictions/test-charger", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["charger_id"] == "test-charger"

def test_get_cached_prediction_not_found(client, auth_headers):
    with patch("src.services.cache_service.CacheService.get_prediction") as mock_get:
        mock_get.return_value = None

        response = client.get("/api/v1/predictions/unknown", headers=auth_headers)

    assert response.status_code == 404
    assert "No cached prediction found" in response.json()["detail"]

def test_detect_anomaly_success(client, auth_headers):
    mock_result = {
        "charger_id": "test-charger",
        "is_anomaly": True,
        "anomaly_score": 85.5,
        "anomaly_type": "OVER_TEMPERATURE",
        "model_version": "v1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    with patch("src.services.prediction_service.PredictionService.detect_anomaly") as mock_detect:
        mock_detect.return_value = mock_result

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

def test_batch_predictions_success(client, auth_headers):
    # Current implementation is a stub, but we mock the service for future-proofing
    with patch("src.services.prediction_service.PredictionService") as mock_service:
        payload = {
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

def test_prediction_failure_handles_exception(client, auth_headers):
    with patch("src.services.prediction_service.PredictionService.predict_failure") as mock_predict:
        mock_predict.side_effect = Exception("Internal error")

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

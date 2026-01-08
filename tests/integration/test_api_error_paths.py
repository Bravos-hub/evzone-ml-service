"""
Integration tests for API error handling paths.
"""
import pytest

from src.api.routes import models as models_routes
from src.api.routes import predictions as predictions_routes


def _payload(charger_id, metrics):
    return {"charger_id": charger_id, "metrics": metrics}


def test_models_list_error(client, auth_headers, monkeypatch):
    async def boom(self):
        raise RuntimeError("boom")

    monkeypatch.setattr("src.services.model_manager.ModelManager.list_models", boom)

    response = client.get("/api/v1/models", headers=auth_headers)
    assert response.status_code == 500


def test_models_reload_error(client, auth_headers, monkeypatch):
    class BadDateTime:
        @staticmethod
        def utcnow():
            raise RuntimeError("boom")

    monkeypatch.setattr(models_routes, "datetime", BadDateTime)

    response = client.post("/api/v1/models/reload", headers=auth_headers)
    assert response.status_code == 500


def test_predict_failure_error(client, auth_headers, mock_charger_metrics, monkeypatch):
    async def boom(self, *args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("src.services.prediction_service.PredictionService.predict_failure", boom)

    response = client.post(
        "/api/v1/predictions/failure",
        json=_payload("c1", mock_charger_metrics),
        headers=auth_headers,
    )
    assert response.status_code == 500


def test_predict_maintenance_error(client, auth_headers, mock_charger_metrics, monkeypatch):
    async def boom(self, *args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("src.services.prediction_service.PredictionService.predict_maintenance", boom)

    response = client.post(
        "/api/v1/predictions/maintenance",
        json=_payload("c1", mock_charger_metrics),
        headers=auth_headers,
    )
    assert response.status_code == 500


def test_cached_prediction_error(client, auth_headers, monkeypatch):
    async def boom(self, *args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("src.services.cache_service.CacheService.get_prediction", boom)

    response = client.get("/api/v1/predictions/c1", headers=auth_headers)
    assert response.status_code == 500


def test_batch_predictions_error(client, auth_headers, mock_charger_metrics, monkeypatch):
    class ExplodingWindow:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("boom")

    monkeypatch.setattr(predictions_routes, "PredictedFailureWindow", ExplodingWindow)

    response = client.post(
        "/api/v1/predictions/batch",
        json={"chargers": [mock_charger_metrics]},
        headers=auth_headers,
    )
    assert response.status_code == 500


def test_detect_anomaly_detector_missing(client, auth_headers, mock_charger_metrics, monkeypatch):
    async def no_detector(self, name):
        return None

    monkeypatch.setattr("src.services.model_manager.ModelManager.get_model", no_detector)

    response = client.post(
        "/api/v1/predictions/anomaly",
        json=_payload("c1", mock_charger_metrics),
        headers=auth_headers,
    )
    assert response.status_code == 503


def test_detect_anomaly_error(client, auth_headers, mock_charger_metrics, monkeypatch):
    class BoomDetector:
        def detect(self, *args, **kwargs):
            raise RuntimeError("boom")

    async def detector(self, name):
        return BoomDetector()

    monkeypatch.setattr("src.services.model_manager.ModelManager.get_model", detector)

    response = client.post(
        "/api/v1/predictions/anomaly",
        json=_payload("c1", mock_charger_metrics),
        headers=auth_headers,
    )
    assert response.status_code == 500


def test_detect_anomaly_flat_detector_missing(client, auth_headers, mock_charger_metrics, monkeypatch):
    async def no_detector(self, name):
        return None

    monkeypatch.setattr("src.services.model_manager.ModelManager.get_model", no_detector)

    response = client.post(
        "/api/v1/anomaly/detect",
        json={
            "charger_id": "c1",
            "connector_status": mock_charger_metrics["connector_status"],
            "energy_delivered": mock_charger_metrics["energy_delivered"],
            "power": mock_charger_metrics["power"],
            "temperature": mock_charger_metrics["temperature"],
            "error_codes": [],
            "metadata": {},
        },
        headers=auth_headers,
    )
    assert response.status_code == 503


def test_detect_anomaly_flat_error(client, auth_headers, mock_charger_metrics, monkeypatch):
    class BoomDetector:
        def detect(self, *args, **kwargs):
            raise RuntimeError("boom")

    async def detector(self, name):
        return BoomDetector()

    monkeypatch.setattr("src.services.model_manager.ModelManager.get_model", detector)

    response = client.post(
        "/api/v1/anomaly/detect",
        json={
            "charger_id": "c1",
            "connector_status": mock_charger_metrics["connector_status"],
            "energy_delivered": mock_charger_metrics["energy_delivered"],
            "power": mock_charger_metrics["power"],
            "temperature": mock_charger_metrics["temperature"],
            "error_codes": [],
            "metadata": {},
        },
        headers=auth_headers,
    )
    assert response.status_code == 500


def test_recommend_maintenance_error(client, auth_headers, mock_charger_metrics, monkeypatch):
    async def boom(self, *args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("src.services.prediction_service.PredictionService.predict_maintenance", boom)

    response = client.post(
        "/api/v1/maintenance/recommend",
        json=_payload("c1", mock_charger_metrics),
        headers=auth_headers,
    )
    assert response.status_code == 500

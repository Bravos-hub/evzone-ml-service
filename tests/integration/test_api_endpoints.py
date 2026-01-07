"""
Integration tests for API endpoints.
"""
import pytest

TEST_TIMESTAMP = "2026-01-07T00:00:00Z"
WINDOW_START = "2026-01-10T00:00:00Z"
WINDOW_END = "2026-01-12T00:00:00Z"


def _failure_result(charger_id: str, invalid_action: bool = False) -> dict:
    return {
        "charger_id": charger_id,
        "failure_probability": 0.42,
        "predicted_failure_date": WINDOW_START,
        "predicted_failure_window": {
            "start": WINDOW_START,
            "end": WINDOW_END,
        },
        "confidence": None,
        "confidence_score": 0.6,
        "recommended_action": "NOT_VALID" if invalid_action else "WITHIN_7_DAYS",
        "recommended_action_window": "NOT_VALID" if invalid_action else "WITHIN_7_DAYS",
        "recommended_actions": ["Inspect"],
        "top_contributing_factors": ["High temperature"],
        "model_version": "v-test",
        "timestamp": TEST_TIMESTAMP,
    }


def _maintenance_result(charger_id: str, invalid_urgency: bool = False) -> dict:
    return {
        "charger_id": charger_id,
        "recommended_date": WINDOW_START,
        "recommended_maintenance_datetime": WINDOW_START,
        "urgency": "NOT_VALID" if invalid_urgency else "HIGH",
        "urgency_level": None,
        "estimated_downtime_hours": 4.0,
        "cost_benefit": {
            "preventive_maintenance_cost": 10.0,
            "expected_failure_cost": 20.0,
            "net_savings": 10.0,
        },
        "rationale": ["Test rationale"],
        "model_version": "v-test",
        "timestamp": TEST_TIMESTAMP,
    }


def _anomaly_result(charger_id: str) -> dict:
    return {
        "charger_id": charger_id,
        "is_anomaly": True,
        "anomaly_score": 85.0,
        "anomaly_type": "OVER_TEMPERATURE_CRITICAL",
        "deviation": {"temperature": 3.0},
        "model_version": "v-test",
        "timestamp": TEST_TIMESTAMP,
    }


class DummyPredictionService:
    def __init__(self, model_manager, feature_extractor, cache_service) -> None:
        self.model_manager = model_manager
        self.feature_extractor = feature_extractor
        self.cache_service = cache_service

    async def predict_failure(self, charger_id, metrics, tenant_id=None):
        return _failure_result(charger_id)

    async def predict_maintenance(self, charger_id, metrics, tenant_id=None):
        return _maintenance_result(charger_id)


class DummyAnomalyDetector:
    def detect(self, metrics, tenant_id=None):
        return _anomaly_result(metrics.get("charger_id"))


class DummyModelManager:
    async def list_models(self):
        return {
            "failure_predictor": {
                "name": "failure_predictor",
                "version": "v1.0.0",
                "status": "LOADED",
                "type": "FailurePredictor",
            },
            "anomaly_detector": {
                "name": "anomaly_detector",
                "version": "v1.0.0",
                "status": "LOADED",
                "type": "AnomalyDetector",
            },
        }

    async def get_model(self, model_name: str):
        if model_name == "anomaly_detector":
            return DummyAnomalyDetector()
        return None


@pytest.fixture
def patch_prediction_service(monkeypatch):
    import src.services.prediction_service as prediction_service

    monkeypatch.setattr(prediction_service, "PredictionService", DummyPredictionService)


@pytest.fixture
def patch_model_manager(monkeypatch):
    import src.services.model_manager as model_manager

    monkeypatch.setattr(model_manager, "ModelManager", DummyModelManager)


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_detailed_health_endpoint(client, monkeypatch):
    """Test detailed health endpoint with cache health."""
    import src.services.cache_service as cache_service

    async def fake_health_check(cls):
        return {"status": "healthy", "healthy": True}

    monkeypatch.setattr(cache_service.CacheService, "health_check", classmethod(fake_health_check))

    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["checks"]["cache"]["status"] == "healthy"


def test_models_endpoint_list(client, auth_headers, patch_model_manager):
    response = client.get("/api/v1/models", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert {m["name"] for m in data["models"]} == {"failure_predictor", "anomaly_detector"}


def test_models_endpoint_reload(client, auth_headers):
    response = client.post("/api/v1/models/reload?model_name=failure_predictor", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["model_name"] == "failure_predictor"


def test_predictions_endpoint_requires_auth(client, mock_charger_metrics, monkeypatch):
    """Test that predictions require authentication."""
    from src.config.settings import settings

    monkeypatch.setattr(settings, "api_key", "test-api-key")
    payload = {
        "charger_id": "test-charger-1",
        "metrics": mock_charger_metrics,
    }
    response = client.post(
        "/api/v1/predictions/failure",
        json=payload,
        headers={"X-API-Key": "invalid-key"},
    )
    assert response.status_code == 401


def test_predict_failure_endpoint(
    client,
    auth_headers,
    mock_charger_metrics,
    patch_prediction_service,
    patch_model_manager,
):
    payload = {
        "charger_id": "test-charger-1",
        "metrics": mock_charger_metrics,
    }
    response = client.post("/api/v1/predictions/failure", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["charger_id"] == "test-charger-1"
    assert data["tenant_id"] == "test-tenant"
    assert data["failure_probability"] == pytest.approx(0.42)
    assert data["recommended_action"] == "WITHIN_7_DAYS"


def test_predict_maintenance_endpoint(
    client,
    auth_headers,
    mock_charger_metrics,
    patch_prediction_service,
    patch_model_manager,
):
    payload = {
        "charger_id": "test-charger-1",
        "metrics": mock_charger_metrics,
    }
    response = client.post("/api/v1/predictions/maintenance", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["charger_id"] == "test-charger-1"
    assert data["tenant_id"] == "test-tenant"
    assert data["urgency"] == "HIGH"
    assert data["cost_benefit"]["net_savings"] == pytest.approx(10.0)


def test_cached_prediction_endpoint(client, auth_headers, monkeypatch):
    import src.services.cache_service as cache_service

    async def fake_get_prediction(self, cache_type, charger_id, tenant_id=None):
        return _failure_result(charger_id, invalid_action=True)

    monkeypatch.setattr(cache_service.CacheService, "get_prediction", fake_get_prediction)

    response = client.get("/api/v1/predictions/test-charger-1", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["recommended_action"] == "WITHIN_30_DAYS"
    assert data["recommended_action_window"] == "WITHIN_30_DAYS"


def test_cached_prediction_not_found(client, auth_headers, monkeypatch):
    import src.services.cache_service as cache_service

    async def fake_get_prediction(self, cache_type, charger_id, tenant_id=None):
        return None

    monkeypatch.setattr(cache_service.CacheService, "get_prediction", fake_get_prediction)

    response = client.get("/api/v1/predictions/test-charger-1", headers=auth_headers)
    assert response.status_code == 404


def test_batch_predictions_endpoint(client, auth_headers, mock_charger_metrics):
    payload = {"chargers": [mock_charger_metrics, {**mock_charger_metrics, "charger_id": "test-2"}]}
    response = client.post("/api/v1/predictions/batch", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["predictions"]) == 2


def test_detect_anomaly_endpoint(client, auth_headers, mock_charger_metrics, patch_model_manager):
    payload = {
        "charger_id": "test-charger-1",
        "metrics": mock_charger_metrics,
    }
    response = client.post("/api/v1/predictions/anomaly", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["charger_id"] == "test-charger-1"
    assert data["is_anomaly"] is True
    assert data["anomaly_score"] == pytest.approx(85.0)


def test_detect_anomaly_flat_endpoint(client, auth_headers, mock_charger_metrics, patch_model_manager):
    payload = {
        "charger_id": "test-charger-1",
        "connector_status": mock_charger_metrics["connector_status"],
        "energy_delivered": mock_charger_metrics["energy_delivered"],
        "power": mock_charger_metrics["power"],
        "temperature": mock_charger_metrics["temperature"],
        "error_codes": mock_charger_metrics["error_codes"],
        "metadata": {},
    }
    response = client.post("/api/v1/anomaly/detect", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["charger_id"] == "test-charger-1"
    assert data["anomaly_type"] == "OVER_TEMPERATURE_CRITICAL"


def test_recommend_maintenance_endpoint(
    client,
    auth_headers,
    mock_charger_metrics,
    patch_prediction_service,
    patch_model_manager,
):
    payload = {
        "charger_id": "test-charger-1",
        "metrics": mock_charger_metrics,
    }
    response = client.post("/api/v1/maintenance/recommend", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["urgency"] == "HIGH"

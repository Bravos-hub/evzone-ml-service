"""
Unit tests for PredictionService.
"""
from datetime import datetime, timezone

import pytest

from src.services.prediction_service import PredictionService
from src.utils.errors import PredictionError


class DummyCacheService:
    def __init__(self):
        self.store = {}
        self.get_calls = []
        self.set_calls = []

    async def get_prediction(self, cache_type, charger_id, tenant_id=None):
        self.get_calls.append((cache_type, charger_id, tenant_id))
        return self.store.get((cache_type, charger_id, tenant_id))

    async def set_prediction(self, cache_type, charger_id, value, tenant_id=None):
        self.set_calls.append((cache_type, charger_id, tenant_id))
        self.store[(cache_type, charger_id, tenant_id)] = value
        return True


class DummyFailureModel:
    def __init__(self, result):
        self.result = dict(result)
        self.calls = []

    def predict(self, metrics, tenant_id=None):
        self.calls.append((metrics, tenant_id))
        return dict(self.result)


class DummyMaintenanceModel:
    def __init__(self):
        self.calls = []

    def recommend(self, metrics, failure_prediction, tenant_id=None):
        self.calls.append((metrics, failure_prediction, tenant_id))
        return {
            "charger_id": metrics.get("charger_id"),
            "recommended_date": datetime.now(timezone.utc).isoformat(),
            "urgency": "HIGH",
            "estimated_downtime_hours": 2.0,
            "cost_benefit": {
                "preventive_maintenance_cost": 10.0,
                "expected_failure_cost": 20.0,
                "net_savings": 10.0,
            },
            "model_version": "v-test",
        }


class DummyModelManager:
    def __init__(self, failure_model=None, maintenance_model=None):
        self.failure_model = failure_model
        self.maintenance_model = maintenance_model
        self.calls = []

    async def get_model(self, model_name):
        self.calls.append(model_name)
        if model_name == "failure_predictor":
            return self.failure_model
        if model_name == "maintenance_optimizer":
            return self.maintenance_model
        return None


@pytest.mark.asyncio
async def test_predict_failure_cache_hit():
    cached = {"charger_id": "c1", "failure_probability": 0.2}
    cache = DummyCacheService()
    cache.store[("failure", "c1", "t1")] = cached

    failure_model = DummyFailureModel({"charger_id": "c1", "failure_probability": 0.9})
    model_manager = DummyModelManager(failure_model=failure_model)

    service = PredictionService(model_manager, object(), cache)
    result = await service.predict_failure("c1", {"charger_id": "c1"}, tenant_id="t1")

    assert result == cached
    assert failure_model.calls == []
    assert cache.set_calls == []


@pytest.mark.asyncio
async def test_predict_failure_cache_miss_sets_cache():
    cache = DummyCacheService()
    failure_model = DummyFailureModel({"charger_id": "c1", "failure_probability": 0.55})
    model_manager = DummyModelManager(failure_model=failure_model)

    service = PredictionService(model_manager, object(), cache)
    result = await service.predict_failure("c1", {"charger_id": "c1"}, tenant_id="t1")

    assert result["failure_probability"] == pytest.approx(0.55)
    assert result["tenant_id"] == "t1"
    assert "timestamp" in result
    assert len(failure_model.calls) == 1
    assert cache.set_calls == [("failure", "c1", "t1")]


@pytest.mark.asyncio
async def test_predict_failure_missing_model_raises():
    cache = DummyCacheService()
    model_manager = DummyModelManager(failure_model=None)

    service = PredictionService(model_manager, object(), cache)
    with pytest.raises(PredictionError):
        await service.predict_failure("c1", {"charger_id": "c1"}, tenant_id="t1")


@pytest.mark.asyncio
async def test_predict_maintenance_parses_failure_date():
    cache = DummyCacheService()
    failure_model = DummyFailureModel(
        {
            "charger_id": "c1",
            "failure_probability": 0.4,
            "predicted_failure_date": "2026-01-01T00:00:00Z",
        }
    )
    maintenance_model = DummyMaintenanceModel()
    model_manager = DummyModelManager(
        failure_model=failure_model,
        maintenance_model=maintenance_model,
    )

    service = PredictionService(model_manager, object(), cache)
    result = await service.predict_maintenance("c1", {"charger_id": "c1"}, tenant_id="t1")

    assert result["tenant_id"] == "t1"
    assert "timestamp" in result
    assert len(maintenance_model.calls) == 1
    failure_pred = maintenance_model.calls[0][1]
    assert isinstance(failure_pred.get("predicted_failure_date"), datetime)


@pytest.mark.asyncio
async def test_predict_maintenance_missing_optimizer_raises():
    cache = DummyCacheService()
    failure_model = DummyFailureModel(
        {
            "charger_id": "c1",
            "failure_probability": 0.4,
            "predicted_failure_date": "2026-01-01T00:00:00Z",
        }
    )
    model_manager = DummyModelManager(
        failure_model=failure_model,
        maintenance_model=None,
    )

    service = PredictionService(model_manager, object(), cache)
    with pytest.raises(PredictionError):
        await service.predict_maintenance("c1", {"charger_id": "c1"}, tenant_id="t1")


@pytest.mark.asyncio
async def test_predict_maintenance_invalid_failure_date():
    cache = DummyCacheService()
    failure_model = DummyFailureModel(
        {
            "charger_id": "c1",
            "failure_probability": 0.4,
            "predicted_failure_date": "not-a-date",
        }
    )
    maintenance_model = DummyMaintenanceModel()
    model_manager = DummyModelManager(
        failure_model=failure_model,
        maintenance_model=maintenance_model,
    )

    service = PredictionService(model_manager, object(), cache)
    result = await service.predict_maintenance("c1", {"charger_id": "c1"}, tenant_id="t1")

    assert result["charger_id"] == "c1"

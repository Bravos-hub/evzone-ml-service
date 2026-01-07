"""
Unit tests for ModelManager.
"""
import pytest

from src.services.model_manager import ModelManager
from src.utils.errors import ModelLoadError


def test_model_manager_initializes_models():
    manager = ModelManager()
    assert set(manager.models.keys()) == {
        "failure_predictor",
        "anomaly_detector",
        "maintenance_optimizer",
    }


@pytest.mark.asyncio
async def test_model_manager_list_models():
    manager = ModelManager()
    models = await manager.list_models()

    assert "failure_predictor" in models
    info = models["failure_predictor"]
    assert info["status"] == "LOADED"
    assert info["version"] == "v1.0.0"
    assert info["type"] == "FailurePredictor"


@pytest.mark.asyncio
async def test_model_manager_unload_reload():
    manager = ModelManager()
    unloaded = await manager.unload_model("failure_predictor")

    assert unloaded is True
    assert "failure_predictor" not in manager.models

    reloaded = await manager.reload_model("failure_predictor")
    assert reloaded is True
    assert "failure_predictor" in manager.models


@pytest.mark.asyncio
async def test_model_manager_load_unknown_raises():
    manager = ModelManager()
    with pytest.raises(ModelLoadError):
        await manager.load_model("unknown_model")

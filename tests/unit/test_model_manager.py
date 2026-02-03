"""
Unit tests for ModelManager.
"""
import builtins
from pathlib import Path

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
async def test_model_manager_load_existing_model():
    manager = ModelManager()
    loaded = await manager.load_model("failure_predictor")

    assert loaded is True


@pytest.mark.asyncio
async def test_model_manager_load_unknown_raises():
    manager = ModelManager()
    with pytest.raises(ModelLoadError):
        await manager.load_model("unknown_model")


def test_model_manager_initialize_failure(monkeypatch):
    manager = ModelManager.__new__(ModelManager)
    manager.models = {}
    manager.model_base_path = Path("models")

    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if "src.ml.models" in name:
            raise ImportError("boom")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(ModelLoadError):
        manager._initialize_models()

    assert manager.models == {}

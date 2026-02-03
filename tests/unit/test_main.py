"""
Unit tests for main app setup and lifespan.
"""
import asyncio
import runpy
import sys
import types

import pytest
from fastapi.testclient import TestClient

import src.main as main
from src.config.settings import settings


def test_root_endpoint():
    with TestClient(main.app) as client:
        response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"


def test_global_exception_handler(monkeypatch):
    def boom():
        raise RuntimeError("boom")

    main.app.add_api_route("/__raise__", boom, methods=["GET"])
    with TestClient(main.app, raise_server_exceptions=False) as client:
        response = client.get("/__raise__")

    assert response.status_code == 500
    assert response.json()["error"] == "Internal server error"


def test_lifespan_with_kafka_consumer(monkeypatch):
    monkeypatch.setattr(settings, "enable_kafka_consumer", True)

    class DummyKafkaConsumer:
        def __init__(self, *args, **kwargs):
            self.started = False
            self.stopped = False

        async def start(self):
            self.started = True
            try:
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                raise

        async def stop(self):
            self.stopped = True

    class DummyCacheService:
        @classmethod
        async def initialize(cls):
            return None

        @classmethod
        async def close(cls):
            return None

    monkeypatch.setattr(main, "KafkaConsumer", DummyKafkaConsumer)
    monkeypatch.setattr("src.services.cache_service.CacheService", DummyCacheService)

    class DummyModelManager:
        @classmethod
        def get_instance(cls):
            return object()

    monkeypatch.setattr(main, "ModelManager", DummyModelManager)
    monkeypatch.setattr(main, "FeatureExtractor", lambda: object())
    monkeypatch.setattr(main, "PredictionService", lambda *args, **kwargs: object())
    monkeypatch.setattr(main, "DataCollector", lambda: object())

    with TestClient(main.app) as client:
        response = client.get("/health")
        assert response.status_code == 200


def test_main_entrypoint(monkeypatch):
    dummy_uvicorn = types.SimpleNamespace()
    calls = {}

    def run(*args, **kwargs):
        calls["args"] = args
        calls["kwargs"] = kwargs

    dummy_uvicorn.run = run
    monkeypatch.setitem(sys.modules, "uvicorn", dummy_uvicorn)
    sys.modules.pop("src.main", None)

    runpy.run_module("src.main", run_name="__main__")

    assert calls["args"][0] == "src.main:app"

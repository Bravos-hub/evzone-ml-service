"""
Unit tests for CacheService.
"""
import fnmatch
import runpy
from pathlib import Path

import builtins

import pytest

from src.config.settings import settings
from src.services import cache_service
from src.services.cache_service import CacheService


class DummyConnectionPool:
    @classmethod
    def from_url(cls, *args, **kwargs):
        return {"args": args, "kwargs": kwargs}


class DummyRedis:
    def __init__(self, connection_pool=None, should_fail_ping=False, **kwargs):
        self.connection_pool = connection_pool
        self.should_fail_ping = should_fail_ping
        self.store = {}
        self.closed = False

    async def ping(self):
        if self.should_fail_ping:
            raise RuntimeError("ping failed")
        return True

    async def get(self, key):
        return self.store.get(key)

    async def setex(self, key, ttl, value):
        self.store[key] = value
        return True

    async def delete(self, *keys):
        deleted = 0
        for key in keys:
            if key in self.store:
                del self.store[key]
                deleted += 1
        return deleted

    async def keys(self, pattern):
        return [k for k in self.store.keys() if fnmatch.fnmatch(k, pattern)]

    async def aclose(self):
        self.closed = True

    async def close(self):
        self.closed = True


class DummyRedisModule:
    ConnectionPool = DummyConnectionPool
    Redis = DummyRedis


@pytest.fixture(autouse=True)
def reset_cache_state():
    CacheService._instance = None
    CacheService._client = None
    CacheService._is_healthy = False
    CacheService._cache_hits = 0
    CacheService._cache_misses = 0
    CacheService._cache_errors = 0
    yield
    CacheService._instance = None
    CacheService._client = None
    CacheService._is_healthy = False
    CacheService._cache_hits = 0
    CacheService._cache_misses = 0
    CacheService._cache_errors = 0


@pytest.mark.asyncio
async def test_initialize_skips_when_cache_disabled(monkeypatch):
    monkeypatch.setattr(settings, "cache_enabled", False)
    monkeypatch.setattr(cache_service, "REDIS_AVAILABLE", True)

    await CacheService.initialize()
    assert CacheService._client is None

    health = await CacheService.health_check()
    assert health["status"] == "disabled"


@pytest.mark.asyncio
async def test_initialize_skips_when_redis_unavailable(monkeypatch):
    monkeypatch.setattr(settings, "cache_enabled", True)
    monkeypatch.setattr(cache_service, "REDIS_AVAILABLE", False)

    await CacheService.initialize()
    assert CacheService._client is None

    health = await CacheService.health_check()
    assert health["status"] == "disabled"


@pytest.mark.asyncio
async def test_cache_get_set_and_invalidate(monkeypatch):
    monkeypatch.setattr(settings, "cache_enabled", True)
    monkeypatch.setattr(cache_service, "REDIS_AVAILABLE", True)
    monkeypatch.setattr(cache_service, "redis", DummyRedisModule)

    await CacheService.initialize()
    assert CacheService._is_healthy is True

    cache = CacheService()
    value = {"charger_id": "c1", "score": 0.5}

    ok = await cache.set_prediction("failure", "c1", value, tenant_id="t1")
    assert ok is True

    cached = await cache.get_prediction("failure", "c1", tenant_id="t1")
    assert cached["charger_id"] == "c1"
    assert cached["score"] == pytest.approx(0.5)
    assert cache._cache_hits == 1
    assert cache._cache_misses == 0

    miss = await cache.get_prediction("failure", "missing", tenant_id="t1")
    assert miss is None
    assert cache._cache_misses == 1

    deleted = await cache.invalidate_prediction("failure", "c1", tenant_id="t1")
    assert deleted is True

    await CacheService.close()


@pytest.mark.asyncio
async def test_cache_get_skips_when_unhealthy(monkeypatch):
    monkeypatch.setattr(cache_service, "REDIS_AVAILABLE", True)
    monkeypatch.setattr(cache_service, "redis", DummyRedisModule)
    CacheService._client = DummyRedis()
    CacheService._is_healthy = False

    cache = CacheService()
    result = await cache.get("key")

    assert result is None
    assert cache._cache_misses == 1


def test_cache_service_import_error_branch(monkeypatch):
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name.startswith("redis"):
            raise ImportError("no redis")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    module_globals = runpy.run_path(Path(cache_service.__file__))

    assert module_globals["REDIS_AVAILABLE"] is False


@pytest.mark.asyncio
async def test_initialize_ping_failure(monkeypatch):
    class DummyRedisFail(DummyRedis):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs, should_fail_ping=True)

    class DummyRedisFailModule(DummyRedisModule):
        Redis = DummyRedisFail

    monkeypatch.setattr(settings, "cache_enabled", True)
    monkeypatch.setattr(cache_service, "REDIS_AVAILABLE", True)
    monkeypatch.setattr(cache_service, "redis", DummyRedisFailModule)

    await CacheService.initialize()
    assert CacheService._is_healthy is False


@pytest.mark.asyncio
async def test_health_check_unhealthy(monkeypatch):
    monkeypatch.setattr(cache_service, "REDIS_AVAILABLE", True)
    CacheService._client = DummyRedis(should_fail_ping=True)
    CacheService._is_healthy = True

    health = await CacheService.health_check()
    assert health["status"] == "unhealthy"
    assert CacheService._is_healthy is False


def test_build_key_without_tenant():
    key = CacheService._build_key("failure", "c1")
    assert key.endswith(":c1")


@pytest.mark.asyncio
async def test_cache_get_handles_redis_error(monkeypatch):
    class DummyRedisError(Exception):
        pass

    class ExplodingRedis(DummyRedis):
        async def get(self, key):
            raise DummyRedisError("boom")

    monkeypatch.setattr(cache_service, "RedisError", DummyRedisError)
    monkeypatch.setattr(cache_service, "TimeoutError", DummyRedisError)
    monkeypatch.setattr(cache_service, "ConnectionError", DummyRedisError)

    CacheService._client = ExplodingRedis()
    CacheService._is_healthy = True

    cache = CacheService()
    result = await cache.get("key")

    assert result is None
    assert cache._cache_errors == 1


@pytest.mark.asyncio
async def test_cache_get_handles_generic_error():
    class ExplodingRedis(DummyRedis):
        async def get(self, key):
            raise ValueError("boom")

    CacheService._client = ExplodingRedis()
    CacheService._is_healthy = True

    cache = CacheService()
    result = await cache.get("key")

    assert result is None
    assert cache._cache_errors == 1


@pytest.mark.asyncio
async def test_cache_set_handles_redis_error(monkeypatch):
    class DummyRedisError(Exception):
        pass

    class ExplodingRedis(DummyRedis):
        async def setex(self, key, ttl, value):
            raise DummyRedisError("boom")

    monkeypatch.setattr(cache_service, "RedisError", DummyRedisError)
    monkeypatch.setattr(cache_service, "TimeoutError", DummyRedisError)
    monkeypatch.setattr(cache_service, "ConnectionError", DummyRedisError)

    CacheService._client = ExplodingRedis()
    CacheService._is_healthy = True

    cache = CacheService()
    ok = await cache.set("key", {"a": 1})
    assert ok is False
    assert cache._cache_errors == 1


@pytest.mark.asyncio
async def test_cache_set_handles_generic_error():
    class ExplodingRedis(DummyRedis):
        async def setex(self, key, ttl, value):
            raise ValueError("boom")

    CacheService._client = ExplodingRedis()
    CacheService._is_healthy = True

    cache = CacheService()
    ok = await cache.set("key", {"a": 1})
    assert ok is False
    assert cache._cache_errors == 1


@pytest.mark.asyncio
async def test_invalidate_prediction_unhealthy():
    CacheService._client = None
    CacheService._is_healthy = False

    cache = CacheService()
    ok = await cache.invalidate_prediction("failure", "c1")
    assert ok is False


@pytest.mark.asyncio
async def test_invalidate_prediction_exception():
    class ExplodingRedis(DummyRedis):
        async def delete(self, *keys):
            raise RuntimeError("boom")

    CacheService._client = ExplodingRedis()
    CacheService._is_healthy = True

    cache = CacheService()
    ok = await cache.invalidate_prediction("failure", "c1")
    assert ok is False


@pytest.mark.asyncio
async def test_invalidate_all_versions_branches():
    class RedisWithKeys(DummyRedis):
        async def keys(self, pattern):
            return ["k1", "k2"]

    redis_client = RedisWithKeys()
    redis_client.store["k1"] = "v1"
    redis_client.store["k2"] = "v2"
    CacheService._client = redis_client
    CacheService._is_healthy = True

    cache = CacheService()
    deleted = await cache.invalidate_all_versions("c1")
    assert deleted == 2

    CacheService._client = DummyRedis()
    CacheService._is_healthy = True
    deleted = await cache.invalidate_all_versions("c1")
    assert deleted == 0

    CacheService._client = None
    CacheService._is_healthy = False
    deleted = await cache.invalidate_all_versions("c1")
    assert deleted == 0


@pytest.mark.asyncio
async def test_invalidate_all_versions_exception():
    class ExplodingRedis(DummyRedis):
        async def keys(self, pattern):
            raise RuntimeError("boom")

    CacheService._client = ExplodingRedis()
    CacheService._is_healthy = True

    cache = CacheService()
    deleted = await cache.invalidate_all_versions("c1")
    assert deleted == 0

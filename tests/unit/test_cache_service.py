"""
Unit tests for CacheService.
"""
import fnmatch

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

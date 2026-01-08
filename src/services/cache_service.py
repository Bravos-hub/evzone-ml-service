"""Production-ready Redis cache service with timeouts, retries, and metrics."""
import json
import logging
from typing import Optional, Any, Literal
from datetime import datetime

try:
    import redis.asyncio as redis
    from redis.exceptions import RedisError, TimeoutError, ConnectionError
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("redis package not available, cache will be disabled")

from src.config.settings import settings

logger = logging.getLogger(__name__)

CacheType = Literal["failure", "maintenance", "anomaly"]


class CacheService:
    """Production-ready Redis cache with resilience and observability."""
    
    _instance: Optional['CacheService'] = None
    _client: Optional["redis.Redis"] = None
    _is_healthy: bool = False
    _cache_hits: int = 0
    _cache_misses: int = 0
    _cache_errors: int = 0
    
    def __new__(cls):
        """Singleton pattern for connection pooling."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    async def initialize(cls):
        """Initialize Redis connection pool (call on app startup)."""
        if not REDIS_AVAILABLE or not settings.cache_enabled:
            logger.warning("Cache disabled or Redis not available")
            return
        
        try:
            cls._client = redis.Redis(
                connection_pool=redis.ConnectionPool.from_url(
                    settings.redis_url,
                    password=settings.redis_password or None,
                    db=settings.redis_db,
                    max_connections=settings.redis_max_connections,
                    socket_connect_timeout=settings.redis_socket_connect_timeout,
                    socket_timeout=settings.redis_socket_timeout,
                    retry_on_timeout=settings.redis_retry_on_timeout,
                    decode_responses=False,
                )
            )
            # Test connection
            await cls._client.ping()
            cls._is_healthy = True
            logger.info(f"✓ Redis connected: {settings.redis_url}")
        except Exception as e:
            logger.error(f"✗ Redis connection failed: {e}. Cache disabled.")
            cls._is_healthy = False
    
    @classmethod
    async def close(cls):
        """Close Redis connection (call on app shutdown)."""
        if cls._client:
            await cls._client.aclose()
            logger.info("Redis connection closed")
    
    @classmethod
    async def health_check(cls) -> dict:
        """Check cache health for /health endpoint."""
        if not cls._client:
            return {
                "status": "disabled",
                "healthy": False,
                "message": "Cache not initialized"
            }
        
        try:
            await cls._client.ping()
            cls._is_healthy = True
            return {
                "status": "healthy",
                "healthy": True,
                "hits": cls._cache_hits,
                "misses": cls._cache_misses,
                "errors": cls._cache_errors,
                "hit_rate": f"{cls._get_hit_rate():.1%}"
            }
        except Exception as e:
            cls._is_healthy = False
            return {
                "status": "unhealthy",
                "healthy": False,
                "error": str(e)
            }
    
    @classmethod
    def _get_hit_rate(cls) -> float:
        """Calculate cache hit rate."""
        total = cls._cache_hits + cls._cache_misses
        return cls._cache_hits / total if total > 0 else 0.0
    
    @classmethod
    def _build_key(cls, cache_type: CacheType, charger_id: str, tenant_id: Optional[str] = None) -> str:
        """Build versioned cache key."""
        if tenant_id:
            return f"prediction:{cache_type}:{settings.cache_version}:{tenant_id}:{charger_id}"
        return f"prediction:{cache_type}:{settings.cache_version}:{charger_id}"
    
    @classmethod
    def _get_ttl(cls, cache_type: CacheType) -> int:
        """Get TTL for cache type."""
        ttl_map = {
            "failure": settings.cache_ttl_failure_prediction,
            "maintenance": settings.cache_ttl_maintenance,
            "anomaly": settings.cache_ttl_anomaly,
        }
        return ttl_map.get(cache_type, 3600)
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache (non-blocking on failure)."""
        if not self._client or not self._is_healthy:
            self._cache_misses += 1
            return None
        
        try:
            value = await self._client.get(key)
            if value:
                self._cache_hits += 1
                logger.debug(f"Cache HIT: {key}")
                return json.loads(value)
            else:
                self._cache_misses += 1
                logger.debug(f"Cache MISS: {key}")
                return None
        except (RedisError, TimeoutError, ConnectionError) as e:
            self._cache_errors += 1
            logger.warning(f"Cache get error (non-blocking): {e}")
            return None
        except Exception as e:
            self._cache_errors += 1
            logger.error(f"Unexpected cache error: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache (non-blocking on failure)."""
        if not self._client or not self._is_healthy:
            return False
        
        try:
            ttl = ttl or 3600
            # Add timestamp for debugging
            if isinstance(value, dict):
                value["_cached_at"] = datetime.utcnow().isoformat()
            
            serialized = json.dumps(value, default=str)
            await self._client.setex(key, ttl, serialized)
            logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
            return True
        except (RedisError, TimeoutError, ConnectionError) as e:
            self._cache_errors += 1
            logger.warning(f"Cache set error (non-blocking): {e}")
            return False
        except Exception as e:
            self._cache_errors += 1
            logger.error(f"Unexpected cache set error: {e}")
            return False
    
    async def get_prediction(self, cache_type: CacheType, charger_id: str, tenant_id: Optional[str] = None) -> Optional[dict]:
        """Get prediction from cache with versioned key."""
        key = self._build_key(cache_type, charger_id, tenant_id=tenant_id)
        return await self.get(key)
    
    async def set_prediction(self, cache_type: CacheType, charger_id: str, value: dict, tenant_id: Optional[str] = None) -> bool:
        """Set prediction in cache with versioned key and type-specific TTL."""
        key = self._build_key(cache_type, charger_id, tenant_id=tenant_id)
        ttl = self._get_ttl(cache_type)
        return await self.set(key, value, ttl)
    
    async def invalidate_prediction(self, cache_type: CacheType, charger_id: str, tenant_id: Optional[str] = None) -> bool:
        """Invalidate cached prediction."""
        if not self._client or not self._is_healthy:
            return False
        
        try:
            key = self._build_key(cache_type, charger_id, tenant_id=tenant_id)
            await self._client.delete(key)
            logger.info(f"Cache INVALIDATED: {key}")
            return True
        except Exception as e:
            logger.warning(f"Cache invalidation error (non-blocking): {e}")
            return False
    
    async def invalidate_all_versions(self, charger_id: str) -> int:
        """Invalidate all cache versions for a charger (e.g., on model update)."""
        if not self._client or not self._is_healthy:
            return 0
        
        try:
            pattern = f"prediction:*:*:{charger_id}"
            keys = await self._client.keys(pattern)
            if keys:
                deleted = await self._client.delete(*keys)
                logger.info(f"Invalidated {deleted} cache entries for {charger_id}")
                return deleted
            return 0
        except Exception as e:
            logger.warning(f"Bulk invalidation error: {e}")
            return 0

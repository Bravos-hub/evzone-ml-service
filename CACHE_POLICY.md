# Redis Cache Policy & Configuration

## 🎯 **Cache Strategy**

### **What We Cache**
| Prediction Type | Cache Key Pattern | TTL | Reason |
|----------------|-------------------|-----|--------|
| **Failure Prediction** | `prediction:failure:v1:{charger_id}` | 1 hour | Charger state changes slowly |
| **Maintenance Schedule** | `prediction:maintenance:v1:{charger_id}` | 30 min | Depends on failure prediction |
| **Anomaly Detection** | `prediction:anomaly:v1:{charger_id}` | 5 min | Real-time monitoring needs fresh data |

### **Key Schema**
```
prediction:{type}:{version}:{charger_id}

Examples:
- prediction:failure:v1:CHG_001
- prediction:maintenance:v1:CHG_002
- prediction:anomaly:v1:CHG_003
```

**Why versioned keys?**
- Easy cache invalidation on model updates
- A/B testing different model versions
- Rollback capability

---

## ⚙️ **Configuration**

### **.env Settings**
```bash
# Redis Connection
REDIS_URL=redis://localhost:6380
REDIS_PASSWORD=                          # Optional, for production
REDIS_DB=0                               # Database index
REDIS_SOCKET_CONNECT_TIMEOUT=5           # Connection timeout (seconds)
REDIS_SOCKET_TIMEOUT=5                   # Socket timeout (seconds)
REDIS_MAX_CONNECTIONS=50                 # Connection pool size
REDIS_RETRY_ON_TIMEOUT=true              # Retry on timeout

# Cache Policy
CACHE_VERSION=v1                         # Cache key version
CACHE_TTL_FAILURE_PREDICTION=3600        # 1 hour
CACHE_TTL_MAINTENANCE=1800               # 30 minutes
CACHE_TTL_ANOMALY=300                    # 5 minutes
CACHE_ENABLED=true                       # Enable/disable cache
```

### **Production Settings**
```bash
# Use TLS for remote Redis
REDIS_URL=rediss://your-redis-host:6380  # Note: rediss:// for TLS

# Set password
REDIS_PASSWORD=your-secure-redis-password

# Increase timeouts for remote connections
REDIS_SOCKET_CONNECT_TIMEOUT=10
REDIS_SOCKET_TIMEOUT=10

# Increase pool size for high traffic
REDIS_MAX_CONNECTIONS=100
```

---

## 🛡️ **Resilience Features**

### **1. Non-Blocking Cache**
Cache failures **never block predictions**:
```python
# Cache miss or error → prediction still runs
cached = await cache.get_prediction("failure", charger_id)
if cached:
    return cached  # Fast path
# Slow path: run prediction
result = model.predict(metrics)
```

### **2. Graceful Degradation**
```python
# Redis down? Service continues without cache
if not cache._is_healthy:
    logger.warning("Cache unhealthy, running without cache")
    return None  # Prediction proceeds
```

### **3. Timeouts & Retries**
- **Connection timeout:** 5s (configurable)
- **Socket timeout:** 5s (configurable)
- **Retry on timeout:** Enabled
- **Max retries:** 3 (Redis client default)

### **4. Connection Pooling**
- **Singleton pattern:** One connection pool per app
- **Max connections:** 50 (configurable)
- **Initialize on startup:** Prevents per-request overhead
- **Close on shutdown:** Clean resource cleanup

---

## 📊 **Observability**

### **Cache Metrics**
```python
# Tracked automatically
cache_hits: int       # Successful cache retrievals
cache_misses: int     # Cache not found
cache_errors: int     # Redis errors
hit_rate: float       # hits / (hits + misses)
```

### **Health Check**
```bash
curl http://localhost:8000/api/v1/health
```

Response:
```json
{
  "status": "healthy",
  "checks": {
    "cache": {
      "status": "healthy",
      "healthy": true,
      "hits": 150,
      "misses": 50,
      "errors": 2,
      "hit_rate": "75.0%"
    }
  }
}
```

### **Logs**
```
# Cache hits/misses
DEBUG - Cache HIT: prediction:failure:v1:CHG_001
DEBUG - Cache MISS: prediction:failure:v1:CHG_002

# Cache operations
DEBUG - Cache SET: prediction:failure:v1:CHG_001 (TTL: 3600s)
INFO  - Cache INVALIDATED: prediction:failure:v1:CHG_001

# Errors (non-blocking)
WARNING - Cache get error (non-blocking): Connection timeout
WARNING - Cache set error (non-blocking): Redis unavailable
```

---

## 🔄 **Cache Invalidation**

### **1. Automatic Expiration**
TTL-based expiration (no manual cleanup needed):
```python
# Failure predictions expire after 1 hour
# Maintenance schedules expire after 30 minutes
# Anomaly detections expire after 5 minutes
```

### **2. Manual Invalidation**
```python
from src.services.cache_service import CacheService

cache = CacheService()

# Invalidate specific prediction
await cache.invalidate_prediction("failure", "CHG_001")

# Invalidate all versions for a charger (e.g., after model update)
deleted = await cache.invalidate_all_versions("CHG_001")
```

### **3. Version Bump**
Update cache version to invalidate all old caches:
```bash
# In .env
CACHE_VERSION=v2  # All v1 caches become stale
```

### **4. When to Invalidate**
- ✅ Model updated/retrained
- ✅ Charger maintenance performed
- ✅ Charger configuration changed
- ✅ Manual override needed
- ❌ Don't invalidate on every prediction (defeats purpose)

---

## 🚀 **Usage Examples**

### **Basic Usage**
```python
from src.services.cache_service import CacheService

cache = CacheService()

# Get cached prediction
cached = await cache.get_prediction("failure", "CHG_001")
if cached:
    return cached

# Run prediction
result = model.predict(metrics)

# Cache result
await cache.set_prediction("failure", "CHG_001", result)
```

### **With Custom TTL**
```python
# Cache for 10 minutes instead of default
await cache.set("custom:key", data, ttl=600)
```

### **Bulk Invalidation**
```python
# After model update, invalidate all caches
charger_ids = ["CHG_001", "CHG_002", "CHG_003"]
for charger_id in charger_ids:
    await cache.invalidate_all_versions(charger_id)
```

---

## 🔧 **Troubleshooting**

### **Cache Not Working**
```bash
# Check Redis is running
docker ps | grep redis

# Test Redis connection
redis-cli -p 6380 ping
# Should return: PONG

# Check health endpoint
curl http://localhost:8000/api/v1/health
```

### **High Cache Miss Rate**
```bash
# Check TTL settings (might be too short)
# Check if keys are being invalidated too often
# Check logs for cache errors
```

### **Redis Connection Errors**
```bash
# Check .env settings
REDIS_URL=redis://localhost:6380  # Correct port?
REDIS_PASSWORD=                    # Correct password?

# Increase timeouts for slow networks
REDIS_SOCKET_CONNECT_TIMEOUT=10
REDIS_SOCKET_TIMEOUT=10
```

### **Disable Cache Temporarily**
```bash
# In .env
CACHE_ENABLED=false

# Or set invalid Redis URL
REDIS_URL=redis://invalid:9999
```

---

## 📈 **Performance Impact**

### **With Cache (Hit)**
```
Request → Cache HIT → Return (5-10ms)
```

### **Without Cache (Miss)**
```
Request → Model Prediction → Cache SET → Return (50-200ms)
```

### **Expected Hit Rates**
- **Failure predictions:** 70-80% (chargers checked frequently)
- **Maintenance schedules:** 50-60% (depends on failure predictions)
- **Anomaly detection:** 30-40% (real-time monitoring)

---

## 🔐 **Security**

### **Production Checklist**
- [ ] Use TLS (`rediss://` instead of `redis://`)
- [ ] Set strong Redis password
- [ ] Use separate Redis DB per environment
- [ ] Restrict Redis network access (firewall)
- [ ] Enable Redis AUTH
- [ ] Monitor cache access patterns
- [ ] Rotate Redis passwords regularly

### **Example Production Config**
```bash
REDIS_URL=rediss://prod-redis.example.com:6380
REDIS_PASSWORD=your-strong-password-here
REDIS_DB=1
REDIS_SOCKET_CONNECT_TIMEOUT=10
REDIS_SOCKET_TIMEOUT=10
REDIS_MAX_CONNECTIONS=100
```

---

## 📚 **Additional Resources**

- **Redis Best Practices:** https://redis.io/docs/manual/patterns/
- **Cache Patterns:** https://docs.aws.amazon.com/whitepapers/latest/database-caching-strategies-using-redis/caching-patterns.html
- **Health Check:** `GET /api/v1/health`
- **Metrics:** Check logs for cache hit/miss rates

---

**Cache is production-ready!** ✅ Non-blocking, resilient, observable, and versioned.

# Credentials & Docker Setup Guide

## 🔑 Credentials Configuration

### 1. **API_KEY** (Required)
This secures YOUR ML service endpoints. Clients must send this key to access the API.

**Generate a secure key:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Example output:**
```
xK9mP2vL8nQ4wR7tY5uZ3aB6cD1eF0gH2iJ4kL6mN8oP
```

**Update in `.env`:**
```bash
API_KEY=xK9mP2vL8nQ4wR7tY5uZ3aB6cD1eF0gH2iJ4kL6mN8oP
```

**Usage by clients:**
```bash
curl -H "X-API-Key: xK9mP2vL8nQ4wR7tY5uZ3aB6cD1eF0gH2iJ4kL6mN8oP" \
  http://localhost:8000/api/v1/predictions/failure
```

---

### 2. **API_KEY_HEADER** (Already Configured)
The HTTP header name for the API key.

**Current value:** `X-API-Key` ✓ (Standard, no change needed)

---

### 3. **MAIN_API_URL** (Optional - for NestJS integration)
URL of your main NestJS backend API.

**Options:**

| Environment | URL | When to Use |
|------------|-----|-------------|
| **Local Development** | `http://localhost:3000` | NestJS running locally |
| **Docker Network** | `http://nestjs-api:3000` | Both services in Docker |
| **Production** | `https://api.evzone.com` | Production deployment |

**Update in `.env`:**
```bash
# For local development
MAIN_API_URL=http://localhost:3000

# Or for Docker network
MAIN_API_URL=http://nestjs-api:3000

# Or for production
MAIN_API_URL=https://api.evzone.com
```

---

### 4. **MAIN_API_KEY** (Optional - for calling NestJS)
API key to authenticate when ML service calls the main backend.

**How to get it:**

**Option A: From NestJS Backend Team**
```bash
# Ask your backend team for the integration API key
# They should provide something like:
MAIN_API_KEY=backend-integration-key-xyz123
```

**Option B: Generate in NestJS Admin Panel**
1. Login to NestJS admin panel
2. Go to API Keys section
3. Create new key with name "ML Service Integration"
4. Copy the generated key

**Option C: Check NestJS .env**
```bash
# Look for API_KEY or INTEGRATION_KEY in NestJS .env file
cd ../backend
cat .env | grep API_KEY
```

**Update in `.env`:**
```bash
MAIN_API_KEY=your-nestjs-backend-api-key-here
```

---

## 🐳 Docker Setup

### Current Configuration

**`docker-compose.yml` now runs ONLY infrastructure:**
- ✅ PostgreSQL (port 5434)
- ✅ Redis (port 6380)
- ✅ Kafka (port 9093)
- ✅ Zookeeper (port 2182)
- ❌ ML Service (commented out - run locally)

### Usage

**1. Start Infrastructure Services:**
```bash
docker compose up -d
```

**2. Verify Services Running:**
```bash
docker compose ps
```

Expected output:
```
NAME                    STATUS    PORTS
evzone-ml-postgres      Up        0.0.0.0:5434->5432/tcp
evzone-ml-redis         Up        0.0.0.0:6380->6379/tcp
evzone-ml-kafka         Up        0.0.0.0:9093->9092/tcp
evzone-ml-zookeeper     Up        0.0.0.0:2182->2181/tcp
```

**3. Run ML Service Locally:**
```bash
# Activate virtual environment
source venv/bin/activate

# Run the service
uvicorn src.main:app --reload --port 8000
```

**4. Stop Infrastructure:**
```bash
docker compose down
```

**5. Stop and Remove Volumes:**
```bash
docker compose down -v
```

---

## 🔌 Connection Details

### PostgreSQL
```bash
Host: localhost
Port: 5434
User: postgres
Password: postgres
Database: evzone_ml

# Connection string
DATABASE_URL=postgresql://postgres:postgres@localhost:5434/evzone_ml
```

**Test connection:**
```bash
psql -h localhost -p 5434 -U postgres -d evzone_ml
```

### Redis
```bash
Host: localhost
Port: 6380

# Connection string
REDIS_URL=redis://localhost:6380
```

**Test connection:**
```bash
redis-cli -p 6380 ping
# Should return: PONG
```

### Kafka
```bash
Host: localhost
Port: 9093

# Connection string
KAFKA_BROKERS=localhost:9093
```

**Test connection:**
```bash
# List topics
docker exec evzone-ml-kafka kafka-topics --list --bootstrap-server localhost:9092
```

---

## 📝 Complete .env Configuration

```bash
# Application Configuration
APP_NAME=evzone-ml-service
APP_VERSION=1.0.0
ENVIRONMENT=development
DEBUG=false
LOG_LEVEL=INFO

# Server Configuration
HOST=0.0.0.0
PORT=8000

# API Authentication (REQUIRED)
# Generate with: python3 -c "import secrets; print(secrets.token_urlsafe(32))"
API_KEY=dev-ml-service-key-change-in-production
API_KEY_HEADER=X-API-Key

# Database Configuration (Docker)
DATABASE_URL=postgresql://postgres:postgres@localhost:5434/evzone_ml
DATABASE_POOL_SIZE=10

# Kafka Configuration (Docker)
KAFKA_BROKERS=localhost:9093
KAFKA_CLIENT_ID=evzone-ml-service
KAFKA_GROUP_ID=ml-service-group
KAFKA_TOPIC_CHARGER_METRICS=charger.metrics
KAFKA_TOPIC_PREDICTIONS=ml.predictions

# Redis Configuration (Docker)
REDIS_URL=redis://localhost:6380
REDIS_PASSWORD=
REDIS_DB=0
CACHE_TTL=3600

# ML Models Configuration
MODEL_BASE_PATH=./models
MODEL_FAILURE_PREDICTOR=failure_predictor
MODEL_MAINTENANCE_SCHEDULER=maintenance_scheduler
MODEL_ANOMALY_DETECTOR=anomaly_detector

# TensorFlow Configuration
TF_CPP_MIN_LOG_LEVEL=2
TF_FORCE_GPU_ALLOW_GROWTH=true

# Monitoring Configuration
PROMETHEUS_PORT=9090
ENABLE_METRICS=true

# Main API Integration (Optional)
MAIN_API_URL=http://localhost:3000
MAIN_API_KEY=

# Feature Flags
ENABLE_PREDICTIONS=true
ENABLE_TRAINING=false
ENABLE_BATCH_PREDICTIONS=true
```

---

## 🚀 Quick Start

### Step 1: Generate API Key
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Step 2: Update .env
```bash
# Edit .env and set:
API_KEY=<generated-key-from-step-1>
MAIN_API_URL=http://localhost:3000  # or your NestJS URL
MAIN_API_KEY=<get-from-nestjs-team>  # optional
```

### Step 3: Start Infrastructure
```bash
docker compose up -d
```

### Step 4: Run ML Service
```bash
source venv/bin/activate
uvicorn src.main:app --reload --port 8000
```

### Step 5: Test
```bash
# Health check
curl http://localhost:8000/health

# Test prediction (use your API key)
curl -X POST http://localhost:8000/api/v1/predictions/failure \
  -H "X-API-Key: your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{
    "charger_id": "test_001",
    "metrics": {
      "charger_id": "test_001",
      "connector_status": "CHARGING",
      "energy_delivered": 45.5,
      "power": 7.2,
      "temperature": 35.0,
      "error_codes": [],
      "uptime_hours": 1500,
      "total_sessions": 300,
      "last_maintenance": "2024-06-01T10:00:00Z",
      "metadata": {}
    }
  }'
```

---

## 🔧 Troubleshooting

### Issue: Port Already in Use
```bash
# Check what's using the port
sudo lsof -i :5434  # PostgreSQL
sudo lsof -i :6380  # Redis
sudo lsof -i :9093  # Kafka

# Change ports in docker-compose.yml if needed
```

### Issue: Cannot Connect to Database
```bash
# Check if PostgreSQL is running
docker compose ps postgres

# Check logs
docker compose logs postgres

# Verify connection
psql -h localhost -p 5434 -U postgres -d evzone_ml
```

### Issue: Kafka Not Working
```bash
# Check Kafka logs
docker compose logs kafka

# Restart Kafka
docker compose restart kafka

# Wait 30 seconds for Kafka to fully start
```

---

## 📦 Optional: Run ML Service in Docker

If you want to run the ML service in Docker too:

**1. Uncomment the ml-service section in `docker-compose.yml`**

**2. Update .env for Docker network:**
```bash
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/evzone_ml
KAFKA_BROKERS=kafka:29092
REDIS_URL=redis://redis:6379
```

**3. Start all services:**
```bash
docker compose up -d
```

**4. Access ML service:**
```
http://localhost:8000
```

---

## 🔐 Security Best Practices

1. **Never commit .env to git** (already in .gitignore)
2. **Use strong API keys in production** (32+ characters)
3. **Rotate API keys regularly** (every 90 days)
4. **Use HTTPS in production** (not HTTP)
5. **Restrict API access by IP** (firewall rules)
6. **Monitor API usage** (check logs regularly)

---

## 📚 Additional Resources

- **API Documentation:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health
- **Metrics:** http://localhost:9090 (if Prometheus enabled)
- **Integration Guide:** ML_INTEGRATION.md
- **Quick Start:** QUICKSTART_INTEGRATED.md

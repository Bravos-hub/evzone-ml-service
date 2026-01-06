# Quick Reference Card

## 🚀 Start Development

```bash
# 1. Start infrastructure
docker compose up -d

# 2. Activate venv
source venv/bin/activate

# 3. Run ML service
uvicorn src.main:app --reload --port 8000
```

## 🔑 Generate API Key

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

## 🔌 Service Ports

| Service | Port | URL |
|---------|------|-----|
| ML Service | 8000 | http://localhost:8000 |
| PostgreSQL | 5434 | localhost:5434 |
| Redis | 6380 | localhost:6380 |
| Kafka | 9093 | localhost:9093 |
| Zookeeper | 2182 | localhost:2182 |

## 📝 .env Quick Setup

```bash
# Required
API_KEY=<generate-with-command-above>

# Docker infrastructure
DATABASE_URL=postgresql://postgres:postgres@localhost:5434/evzone_ml
KAFKA_BROKERS=localhost:9093
REDIS_URL=redis://localhost:6380

# Optional (NestJS integration)
MAIN_API_URL=http://localhost:3000
MAIN_API_KEY=<get-from-nestjs-team>
```

## 🧪 Test Commands

```bash
# Health check
curl http://localhost:8000/health

# Test with API key
curl -H "X-API-Key: your-key" http://localhost:8000/api/v1/models

# API docs
open http://localhost:8000/docs
```

## 🐳 Docker Commands

```bash
# Start
docker compose up -d

# Status
docker compose ps

# Logs
docker compose logs -f

# Stop
docker compose down

# Stop + remove data
docker compose down -v
```

## 🔧 Troubleshooting

```bash
# Check ports
sudo lsof -i :5434  # PostgreSQL
sudo lsof -i :6380  # Redis
sudo lsof -i :9093  # Kafka

# Test PostgreSQL
psql -h localhost -p 5434 -U postgres -d evzone_ml

# Test Redis
redis-cli -p 6380 ping

# Check Docker logs
docker compose logs postgres
docker compose logs redis
docker compose logs kafka
```

## 📚 Documentation

- **Full Guide:** CREDENTIALS_DOCKER_GUIDE.md
- **Integration:** ML_INTEGRATION.md
- **Quick Start:** QUICKSTART_INTEGRATED.md

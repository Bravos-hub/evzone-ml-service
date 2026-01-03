# EVzone ML Service

Standalone Python/FastAPI microservice for predictive maintenance and ML-powered analytics for the EVzone platform.

## Overview

This service provides machine learning capabilities for:
- **Predictive Maintenance** - Predict charger failures before they occur
- **Maintenance Scheduling** - Optimize maintenance schedules based on usage patterns
- **Anomaly Detection** - Detect unusual patterns in charger behavior

## Architecture

- **Framework:** FastAPI (Python 3.11+)
- **ML Framework:** TensorFlow 2.x
- **Message Queue:** Kafka (consumes charger metrics)
- **Cache:** Redis (prediction caching)
- **Database:** PostgreSQL (metadata and training data)

## Getting Started

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Access to Kafka, Redis, PostgreSQL (shared with main backend)

### Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your configuration
```

### Running Locally

```bash
# Using Docker Compose (recommended)
docker-compose up -d

# Or run directly
uvicorn src.main:app --reload --port 8000
```

### API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### Predictions

- `POST /api/v1/predictions/failure` - Predict charger failure
- `POST /api/v1/predictions/maintenance` - Get maintenance schedule
- `GET /api/v1/predictions/{chargerId}` - Get cached prediction
- `POST /api/v1/predictions/batch` - Batch predictions

### Model Management

- `GET /api/v1/models` - List loaded models
- `POST /api/v1/models/reload` - Reload models (admin)

### Health

- `GET /health` - Health check
- `GET /api/v1/health` - Detailed health status

## Data Flow

```
Charger Metrics → Kafka → ML Service → Predictions → Kafka → Main API
```

## Model Training

Models are trained separately and deployed to the service:

```bash
# Train failure prediction model
python -m src.ml.training.train_failure_model

# Deploy model
./scripts/deploy_model.sh failure_predictor v1.0.0
```

## Development

### Project Structure

```
src/
├── api/          # API routes and dependencies
├── services/      # Business logic services
├── ml/           # ML models and training
├── kafka/        # Kafka integration
├── database/     # Database models and migrations
└── utils/        # Utilities
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html
```

## Environment Variables

See `.env.example` for all required environment variables.

## Integration

This service integrates with the main NestJS API via:
- REST API (HTTP)
- Kafka (event streaming)
- Redis (shared cache)

The NestJS client is located at: `backend/apps/api/src/integrations/ml/`

## Deployment

The service is designed to be deployed as a separate microservice:
- Kubernetes deployment
- Horizontal scaling support
- GPU nodes for training, CPU nodes for inference
- Model versioning and A/B testing

## License

Proprietary - EVzone Platform


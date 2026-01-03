# ML Service Integration Guide

This document describes how to integrate the ML service with the main NestJS backend.

## Overview

The ML service is a standalone Python/FastAPI microservice that provides predictive maintenance capabilities. It can be developed and deployed separately, then integrated with the main backend via HTTP API and Kafka.

## Architecture

```
┌─────────────────┐         HTTP/REST         ┌──────────────────┐
│  NestJS Backend │ ────────────────────────> │   ML Service     │
│                 │ <──────────────────────── │  (FastAPI/Python)│
└─────────────────┘                           └──────────────────┘
         │                                             │
         │                                             │
         └────────────── Kafka ────────────────────────┘
                    (Event Streaming)
```

## Setup

### 1. ML Service Setup

```bash
cd evzone-ml-service
python -m venv venv
source venv/bin/activate  #OR
windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your configuration
```

### 2. NestJS Integration

The ML client is already integrated in the backend at:
- `backend/apps/api/src/integrations/ml/`

To enable it:

1. **Add environment variables** to your `.env`:
```env
ML_SERVICE_URL=http://localhost:8000
ML_SERVICE_API_KEY=your-api-key-here
ML_SERVICE_ENABLED=true
ML_SERVICE_TIMEOUT=5000
```

2. **Uncomment MLClientModule** in `app.module.ts`:
```typescript
import { MLClientModule } from './integrations/ml/ml-client.module'

@Module({
  imports: [
    // ... other modules
    MLClientModule, // Uncomment this line
  ],
})
```

### 3. Using the ML Client

Inject `MLClientService` into your services:

```typescript
import { MLClientService } from '../integrations/ml/ml-client.service'

@Injectable()
export class YourService {
  constructor(private mlClient: MLClientService) {}

  async someMethod() {
    // Predict failure
    const prediction = await this.mlClient.predictFailure({
      charger_id: 'charger-123',
      metrics: {
        charger_id: 'charger-123',
        connector_status: 'AVAILABLE',
        energy_delivered: 100.5,
        power: 7.2,
        temperature: 25.0,
        error_codes: [],
        uptime_hours: 720.5,
        total_sessions: 150,
      },
    })

    // Get maintenance schedule
    const maintenance = await this.mlClient.predictMaintenance({
      charger_id: 'charger-123',
      metrics: { /* ... */ },
    })
  }
}
```

## Features

### Circuit Breaker

The ML client includes a circuit breaker pattern:
- Opens after 5 consecutive failures
- Resets after 1 minute
- Prevents cascading failures

### Caching

Predictions are cached in Redis:
- Cache key: `ml:prediction:failure:{chargerId}`
- TTL: 1 hour (configurable)
- Automatic cache invalidation

### Error Handling

- Automatic retry with exponential backoff
- Graceful degradation (service continues if ML service is down)
- Comprehensive error logging

## API Endpoints

### ML Service Endpoints

- `POST /api/v1/predictions/failure` - Predict charger failure
- `POST /api/v1/predictions/maintenance` - Get maintenance schedule
- `GET /api/v1/predictions/{chargerId}` - Get cached prediction
- `POST /api/v1/predictions/batch` - Batch predictions
- `GET /health` - Health check
- `GET /api/v1/models` - List loaded models

### NestJS Client Methods

- `healthCheck()` - Check ML service health
- `predictFailure(request)` - Predict failure
- `predictMaintenance(request)` - Get maintenance schedule
- `getCachedPrediction(chargerId)` - Get cached prediction
- `batchPredictions(request)` - Batch predictions
- `listModels()` - List available models
- `invalidateCache(chargerId)` - Invalidate cache

## Kafka Integration

The ML service consumes charger metrics from Kafka:
- Topic: `charger.metrics` (configurable)
- Automatically triggers predictions
- Publishes predictions to `ml.predictions` topic

## Development Workflow

1. **Develop ML service independently**
   - Train models
   - Test predictions
   - Deploy to staging

2. **Integrate with backend**
   - Enable ML client in backend
   - Test integration
   - Monitor performance

3. **Production deployment**
   - Deploy ML service separately
   - Enable in backend with feature flag
   - Monitor and scale as needed

## Testing

### ML Service Tests

```bash
cd evzone-ml-service
pytest
```

### NestJS Client Tests

```bash
cd backend
npm test -- ml-client.service.spec.ts
```

## Monitoring

- Health checks: `/health` endpoint
- Metrics: Prometheus metrics in ML service
- Logs: Structured logging in both services
- Circuit breaker status: Logged in NestJS

## Troubleshooting

### ML Service Not Available

- Check `ML_SERVICE_ENABLED=true` in backend `.env`
- Verify ML service is running: `curl http://localhost:8000/health`
- Check API key matches in both services
- Review circuit breaker logs

### Predictions Not Working

- Check ML service logs
- Verify Kafka topics are configured
- Check Redis connection for caching
- Review model loading status: `GET /api/v1/models`

## Next Steps

1. Train initial models with historical data
2. Deploy ML service to staging
3. Enable ML client in backend staging
4. Test end-to-end flow
5. Deploy to production with feature flag
6. Monitor and optimize


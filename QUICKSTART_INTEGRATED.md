# Quick Start - Integrated ML Service

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Or if you have Python 3.11 specifically
python3.11 -m pip install -r requirements.txt
```

## Verify Integration

```bash
# Run integration tests
python3 test_integration.py
```

Expected output:
```
============================================================
ML MODELS INTEGRATION TEST
============================================================

Testing feature engineering...
  ✓ Features extracted: 8 features
  ✓ Vector created: 8 dimensions
  ✓ Feature engineering working!

Testing failure predictor...
  ✓ Charger ID: test_001
  ✓ Failure probability: XX.XX%
  ✓ Confidence: XX.XX%
  ✓ Action window: WITHIN_30_DAYS
  ✓ Recommendations: X actions
  ✓ Contributing factors: X factors
  ✓ Failure predictor working!

... (more tests)

============================================================
RESULTS: 6 passed, 0 failed
============================================================
✓ All tests passed! Integration successful!
```

## Start the Service

```bash
# Development mode
uvicorn src.main:app --reload --port 8000

# Or using the settings
python -m src.main
```

## Test API Endpoints

### 1. Health Check
```bash
curl http://localhost:8000/health
```

### 2. List Models
```bash
curl http://localhost:8000/api/v1/models \
  -H "X-API-Key: your-api-key-here"
```

### 3. Predict Failure
```bash
curl -X POST http://localhost:8000/api/v1/predictions/failure \
  -H "X-API-Key: your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{
    "charger_id": "charger_001",
    "metrics": {
      "charger_id": "charger_001",
      "connector_status": "CHARGING",
      "energy_delivered": 45.5,
      "power": 7.2,
      "temperature": 42.0,
      "error_codes": ["E_OVER_TEMP"],
      "uptime_hours": 2100,
      "total_sessions": 450,
      "last_maintenance": "2024-06-01T10:00:00Z",
      "metadata": {}
    }
  }'
```

### 4. Detect Anomaly
```bash
curl -X POST http://localhost:8000/api/v1/predictions/anomaly \
  -H "X-API-Key: your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{
    "charger_id": "charger_001",
    "metrics": {
      "charger_id": "charger_001",
      "connector_status": "CHARGING",
      "energy_delivered": 45.5,
      "power": 0.1,
      "temperature": 65.0,
      "error_codes": ["E_OVER_TEMP"],
      "uptime_hours": 2100,
      "total_sessions": 450,
      "last_maintenance": "2024-06-01T10:00:00Z",
      "metadata": {}
    }
  }'
```

### 5. Get Maintenance Schedule
```bash
curl -X POST http://localhost:8000/api/v1/predictions/maintenance \
  -H "X-API-Key: your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{
    "charger_id": "charger_001",
    "metrics": {
      "charger_id": "charger_001",
      "connector_status": "AVAILABLE",
      "energy_delivered": 45.5,
      "power": 7.2,
      "temperature": 35.0,
      "error_codes": [],
      "uptime_hours": 1800,
      "total_sessions": 350,
      "last_maintenance": "2024-01-01T10:00:00Z",
      "metadata": {"cost_per_kwh": 3000}
    }
  }'
```

## Generate Test Data

```python
from src.ml.data import save_datasets
from pathlib import Path

# Generate synthetic datasets
datasets = save_datasets(Path("./data/synthetic"))
print(f"Generated: {list(datasets.keys())}")
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## What's Integrated

✅ **3 ML Models**: FailurePredictor, AnomalyDetector, MaintenanceOptimizer  
✅ **Feature Engineering**: Automatic feature extraction from metrics  
✅ **Synthetic Data**: Test data generation for development  
✅ **API Endpoints**: Full REST API with validation  
✅ **Caching**: Redis integration for performance  
✅ **Monitoring**: Prometheus metrics  
✅ **Documentation**: Comprehensive API docs  

## Next Steps

1. **Install dependencies**: `pip install -r requirements.txt`
2. **Run tests**: `python3 test_integration.py`
3. **Start service**: `uvicorn src.main:app --reload`
4. **Test endpoints**: Use curl or Swagger UI
5. **Generate data**: Create synthetic datasets for testing
6. **Train models**: Implement training scripts for production models

## Troubleshooting

### Dependencies Missing
```bash
pip install numpy pandas scikit-learn joblib
```

### API Key Error
Set in `.env`:
```
API_KEY=your-secure-api-key-here
```

### Model Not Found
Models use rule-based fallbacks by default. To use trained models:
1. Train models using training data
2. Save as `.joblib` files
3. Place in `./models/` directory

## Support

- Full documentation: `ML_INTEGRATION.md`
- Test script: `test_integration.py`
- API docs: http://localhost:8000/docs

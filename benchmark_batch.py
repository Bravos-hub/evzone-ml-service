import time
import asyncio
from fastapi.testclient import TestClient
from src.main import app

# Assuming some models exist in the app so we can use them for testing predictions.
# Actually we can mock the prediction logic or just use the current stub first.

from unittest.mock import patch

def run_benchmark():
    client = TestClient(app)
    auth_headers = {'X-API-Key': 'your-api-key-here'}

    # generate many chargers
    num_chargers = 100
    chargers = [
        {
            "charger_id": f"CHG_{i:03d}",
            "connector_status": "AVAILABLE",
            "temperature": 25.0 + i % 10
        } for i in range(num_chargers)
    ]

    payload = {
        "prediction_type": "failure",
        "chargers": chargers
    }

    mock_result = {
        "charger_id": "test-charger",
        "failure_probability": 0.1,
        "confidence": 0.9,
        "recommended_action": "WITHIN_30_DAYS",
        "recommendations": ["Check cable"],
        "predicted_failure_date": "2023-12-01T00:00:00+00:00",
        "model_version": "v1.0.0",
        "timestamp": "2023-11-01T00:00:00+00:00"
    }

    with patch("src.services.model_manager.ModelManager._initialize_models"):
        with patch("src.services.prediction_service.PredictionService.predict_failure") as mock_predict:
            async def async_mock(*args, **kwargs):
                await asyncio.sleep(0.1) # Simulate real world inference time
                return mock_result
            mock_predict.side_effect = async_mock

            start_time = time.time()
            response = client.post("/api/v1/predictions/batch", json=payload, headers=auth_headers)
            end_time = time.time()

    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        print(response.json())
        return

    print(f"Time taken for {num_chargers} chargers: {end_time - start_time:.4f} seconds")
    return end_time - start_time

if __name__ == "__main__":
    run_benchmark()

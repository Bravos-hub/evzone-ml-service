import asyncio
import time
from typing import Dict, Any, Optional

from src.services.prediction_service import PredictionService
from src.services.model_manager import ModelManager
from src.services.feature_extractor import FeatureExtractor
from src.services.cache_service import CacheService
from src.kafka.producer import KafkaProducer

class DummyModel:
    def predict(self, metrics: Dict[str, Any], tenant_id: Optional[str] = None):
        # Simulate a blocking machine learning prediction
        time.sleep(0.1)
        return {"failure_probability": 0.5}

    def recommend(self, metrics: Dict[str, Any], failure_pred: Dict[str, Any], tenant_id: Optional[str] = None):
        time.sleep(0.1)
        return {"urgency": "NORMAL", "recommended_date": "2024-01-01T00:00:00Z"}

    def detect(self, metrics: Dict[str, Any], tenant_id: Optional[str] = None):
        time.sleep(0.1)
        return {"is_anomaly": False}

class DummyModelManager(ModelManager):
    def __init__(self):
        pass

    async def get_model(self, model_name: str, tenant_id: Optional[str] = None):
        return DummyModel()

class DummyCacheService(CacheService):
    def __init__(self):
        pass

    async def get_prediction(self, *args, **kwargs):
        return None

    async def set_prediction(self, *args, **kwargs):
        pass

class DummyKafkaProducer(KafkaProducer):
    def __init__(self):
        pass

    async def publish(self, *args, **kwargs):
        pass

async def main():
    manager = DummyModelManager()
    cache = DummyCacheService()
    producer = DummyKafkaProducer()

    # Passing None for feature_extractor as it is not used directly in predict_failure
    service = PredictionService(manager, None, cache, producer)

    metrics = {"status_int": 1, "energy_delivered": 100.0}

    print("Starting concurrent predictions...")
    start_time = time.time()

    # We will simulate 50 concurrent requests
    tasks = []
    for i in range(50):
        tasks.append(service.predict_failure(f"c{i}", metrics))

    await asyncio.gather(*tasks)

    end_time = time.time()
    duration = end_time - start_time

    print(f"Total time for 50 concurrent predictions: {duration:.4f} seconds")

if __name__ == "__main__":
    asyncio.run(main())

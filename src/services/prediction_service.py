"""
Main prediction service orchestrating all prediction logic.
"""
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from src.config.settings import settings
from src.services.model_manager import ModelManager
from src.services.feature_extractor import FeatureExtractor
from src.services.cache_service import CacheService
from src.kafka.producer import KafkaProducer
from src.utils.errors import PredictionError, ModelNotFoundError
from src.utils.metrics import prediction_requests, prediction_duration

logger = logging.getLogger(__name__)


class PredictionService:
    """Main service for orchestrating predictions."""
    
    def __init__(
        self,
        model_manager: ModelManager,
        feature_extractor: FeatureExtractor,
        cache_service: CacheService,
        kafka_producer: Optional[KafkaProducer] = None,
    ):
        self.model_manager = model_manager
        self.feature_extractor = feature_extractor
        self.cache_service = cache_service
        self.kafka_producer = kafka_producer or KafkaProducer.get_instance()
    
    async def predict_failure(
        self,
        charger_id: str,
        metrics: Dict[str, Any],
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Predict charger failure.
        
        Args:
            charger_id: Charger identifier
            metrics: Charger metrics dictionary
            
        Returns:
            Prediction result with failure probability and recommendations
        """
        try:
            # Check cache first (non-blocking)
            cached = await self.cache_service.get_prediction("failure", charger_id, tenant_id=tenant_id)
            if cached:
                logger.info(f"Cache HIT for charger {charger_id}")
                return cached
            
            # Load model
            model = await self.model_manager.get_model("failure_predictor")
            if not model:
                raise ModelNotFoundError("Failure predictor model not loaded")
            
            # Run prediction using integrated model
            result = model.predict(metrics, tenant_id=tenant_id)
            result["timestamp"] = datetime.utcnow().isoformat()
            if tenant_id:
                result["tenant_id"] = tenant_id
            
            # Cache result (non-blocking)
            await self.cache_service.set_prediction("failure", charger_id, result, tenant_id=tenant_id)
            
            prediction_requests.labels(model_type="failure_predictor", status="success").inc()
            
            # Notify if high failure probability
            if result.get("failure_probability", 0.0) >= 0.8:
                await self.kafka_producer.publish(settings.kafka_topic_failure_alerts, result)
                logger.info(f"Published failure alert for charger {charger_id}")

            return result
            
        except Exception as e:
            logger.error(f"Prediction failed for charger {charger_id}: {e}")
            prediction_requests.labels(model_type="failure_predictor", status="error").inc()
            raise PredictionError(f"Failed to predict failure: {str(e)}")
    
    async def predict_maintenance(
        self,
        charger_id: str,
        metrics: Dict[str, Any],
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Predict optimal maintenance schedule.
        
        Args:
            charger_id: Charger identifier
            metrics: Charger metrics dictionary
            
        Returns:
            Maintenance schedule recommendation
        """
        try:
            # First get failure prediction
            failure_pred = await self.predict_failure(charger_id, metrics, tenant_id=tenant_id)
            predicted_date = failure_pred.get("predicted_failure_date")
            if isinstance(predicted_date, str):
                try:
                    failure_pred["predicted_failure_date"] = datetime.fromisoformat(predicted_date.replace("Z", "+00:00"))
                except ValueError:
                    pass
            
            # Load maintenance optimizer
            optimizer = await self.model_manager.get_model("maintenance_optimizer")
            if not optimizer:
                raise ModelNotFoundError("Maintenance optimizer model not loaded")
            
            # Generate maintenance recommendation
            result = optimizer.recommend(metrics, failure_pred, tenant_id=tenant_id)
            result["timestamp"] = datetime.utcnow().isoformat()
            if tenant_id:
                result["tenant_id"] = tenant_id
            
            prediction_requests.labels(model_type="maintenance_scheduler", status="success").inc()
            
            # Notify if critical urgency
            if result.get("urgency") == "CRITICAL":
                # We can reuse the failure alerts topic or use a generic alert topic
                # Using failure alerts for now as it's critical maintenance
                await self.kafka_producer.publish(settings.kafka_topic_failure_alerts, {
                    "type": "MAINTENANCE_CRITICAL",
                    **result
                })
                logger.info(f"Published critical maintenance alert for charger {charger_id}")

            return result
            
        except Exception as e:
            logger.error(f"Maintenance prediction failed for charger {charger_id}: {e}")
            prediction_requests.labels(model_type="maintenance_scheduler", status="error").inc()
            raise PredictionError(f"Failed to predict maintenance: {str(e)}")

    async def detect_anomaly(
        self,
        charger_id: str,
        metrics: Dict[str, Any],
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Detect anomalies in real-time charger metrics.

        Args:
            charger_id: Charger identifier
            metrics: Charger metrics dictionary
            tenant_id: Optional tenant identifier

        Returns:
            Anomaly detection result
        """
        try:
            # Load anomaly detector
            detector = await self.model_manager.get_model("anomaly_detector")
            if not detector:
                raise ModelNotFoundError("Anomaly detector model not loaded")

            # Detect anomaly
            result = detector.detect(metrics, tenant_id=tenant_id)
            result["timestamp"] = datetime.utcnow().isoformat()
            if tenant_id:
                result["tenant_id"] = tenant_id

            prediction_requests.labels(model_type="anomaly_detector", status="success").inc()

            # If an anomaly is detected, publish to Kafka
            if result.get("is_anomaly"):
                await self.kafka_producer.publish(settings.kafka_topic_anomalies, result)
                logger.info(f"Published anomaly detection alert for charger {charger_id}")

            return result

        except Exception as e:
            logger.error(f"Anomaly detection failed for charger {charger_id}: {e}")
            prediction_requests.labels(model_type="anomaly_detector", status="error").inc()
            raise PredictionError(f"Failed to detect anomaly: {str(e)}")

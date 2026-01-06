"""
Main prediction service orchestrating all prediction logic.
"""
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from src.services.model_manager import ModelManager
from src.services.feature_extractor import FeatureExtractor
from src.services.cache_service import CacheService
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
    ):
        self.model_manager = model_manager
        self.feature_extractor = feature_extractor
        self.cache_service = cache_service
    
    async def predict_failure(
        self,
        charger_id: str,
        metrics: Dict[str, Any],
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
            cached = await self.cache_service.get_prediction("failure", charger_id)
            if cached:
                logger.info(f"Cache HIT for charger {charger_id}")
                return cached
            
            # Load model
            model = await self.model_manager.get_model("failure_predictor")
            if not model:
                raise ModelNotFoundError("Failure predictor model not loaded")
            
            # Run prediction using integrated model
            result = model.predict(metrics)
            result["timestamp"] = datetime.utcnow().isoformat()
            
            # Cache result (non-blocking)
            await self.cache_service.set_prediction("failure", charger_id, result)
            
            prediction_requests.labels(model_type="failure_predictor", status="success").inc()
            
            return result
            
        except Exception as e:
            logger.error(f"Prediction failed for charger {charger_id}: {e}")
            prediction_requests.labels(model_type="failure_predictor", status="error").inc()
            raise PredictionError(f"Failed to predict failure: {str(e)}")
    
    async def predict_maintenance(
        self,
        charger_id: str,
        metrics: Dict[str, Any],
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
            failure_pred = await self.predict_failure(charger_id, metrics)
            
            # Load maintenance optimizer
            optimizer = await self.model_manager.get_model("maintenance_optimizer")
            if not optimizer:
                raise ModelNotFoundError("Maintenance optimizer model not loaded")
            
            # Generate maintenance recommendation
            result = optimizer.recommend(metrics, failure_pred)
            result["timestamp"] = datetime.utcnow().isoformat()
            
            prediction_requests.labels(model_type="maintenance_scheduler", status="success").inc()
            
            return result
            
        except Exception as e:
            logger.error(f"Maintenance prediction failed for charger {charger_id}: {e}")
            prediction_requests.labels(model_type="maintenance_scheduler", status="error").inc()
            raise PredictionError(f"Failed to predict maintenance: {str(e)}")


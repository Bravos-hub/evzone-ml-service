"""
Prediction API endpoints.
"""
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict
from datetime import datetime

from src.api.dependencies import verify_api_key
from src.utils.errors import PredictionError

router = APIRouter()


class ChargerMetrics(BaseModel):
    """Charger metrics for prediction."""
    charger_id: str
    connector_status: str
    energy_delivered: float
    power: float
    temperature: Optional[float] = None
    error_codes: List[str] = []
    uptime_hours: float
    total_sessions: int
    last_maintenance: Optional[datetime] = None
    metadata: Optional[dict] = None


class FailurePredictionRequest(BaseModel):
    """Request for failure prediction."""
    charger_id: str
    metrics: ChargerMetrics


class FailurePredictionResponse(BaseModel):
    """Failure prediction response."""
    model_config = ConfigDict(protected_namespaces=())
    
    charger_id: str
    failure_probability: float
    predicted_failure_date: Optional[datetime] = None
    confidence: float
    recommended_action: str
    model_version: str
    timestamp: datetime


class MaintenanceScheduleRequest(BaseModel):
    """Request for maintenance schedule."""
    charger_id: str
    metrics: ChargerMetrics


class MaintenanceScheduleResponse(BaseModel):
    """Maintenance schedule response."""
    model_config = ConfigDict(protected_namespaces=())
    
    charger_id: str
    recommended_date: datetime
    urgency: str  # LOW, MEDIUM, HIGH, CRITICAL
    estimated_downtime_hours: float
    model_version: str
    timestamp: datetime


class BatchPredictionRequest(BaseModel):
    """Batch prediction request."""
    chargers: List[ChargerMetrics]


class BatchPredictionResponse(BaseModel):
    """Batch prediction response."""
    predictions: List[FailurePredictionResponse]
    total: int
    timestamp: datetime


class AnomalyDetectionRequest(BaseModel):
    """Request for anomaly detection."""
    charger_id: str
    metrics: ChargerMetrics


class AnomalyDetectionResponse(BaseModel):
    """Anomaly detection response."""
    model_config = ConfigDict(protected_namespaces=())
    
    charger_id: str
    is_anomaly: bool
    anomaly_score: float
    anomaly_type: str
    deviation: Dict[str, float] = {}
    model_version: str
    timestamp: datetime


@router.post("/predictions/failure", response_model=FailurePredictionResponse)
async def predict_failure(
    request: FailurePredictionRequest,
    api_key: str = Depends(verify_api_key),
):
    """
    Predict charger failure probability.
    
    Returns failure probability, predicted failure date, and recommended actions.
    """
    try:
        from src.services.model_manager import ModelManager
        from src.services.cache_service import CacheService
        from src.services.feature_extractor import FeatureExtractor
        from src.services.prediction_service import PredictionService
        
        # Initialize services (in production, use dependency injection)
        model_manager = ModelManager()
        cache_service = CacheService()
        feature_extractor = FeatureExtractor()
        prediction_service = PredictionService(model_manager, feature_extractor, cache_service)
        
        # Convert Pydantic model to dict
        metrics_dict = request.metrics.model_dump()
        
        # Get prediction
        result = await prediction_service.predict_failure(
            request.charger_id,
            metrics_dict
        )
        
        return FailurePredictionResponse(
            charger_id=result["charger_id"],
            failure_probability=result["failure_probability"],
            predicted_failure_date=result.get("predicted_failure_date"),
            confidence=result["confidence"],
            recommended_action=result["recommended_action"],
            model_version=result["model_version"],
            timestamp=datetime.fromisoformat(result["timestamp"]),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction failed: {str(e)}"
        )


@router.post("/predictions/maintenance", response_model=MaintenanceScheduleResponse)
async def predict_maintenance(
    request: MaintenanceScheduleRequest,
    api_key: str = Depends(verify_api_key),
):
    """
    Get optimal maintenance schedule for a charger.
    
    Returns recommended maintenance date and urgency level.
    """
    try:
        from src.services.model_manager import ModelManager
        from src.services.cache_service import CacheService
        from src.services.feature_extractor import FeatureExtractor
        from src.services.prediction_service import PredictionService
        
        # Initialize services
        model_manager = ModelManager()
        cache_service = CacheService()
        feature_extractor = FeatureExtractor()
        prediction_service = PredictionService(model_manager, feature_extractor, cache_service)
        
        # Convert Pydantic model to dict
        metrics_dict = request.metrics.model_dump()
        
        # Get maintenance recommendation
        result = await prediction_service.predict_maintenance(
            request.charger_id,
            metrics_dict
        )
        
        # Handle datetime conversion safely
        recommended_date = result["recommended_date"]
        if isinstance(recommended_date, str):
            recommended_date = datetime.fromisoformat(recommended_date.replace('Z', '+00:00'))
        
        timestamp = result["timestamp"]
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        
        return MaintenanceScheduleResponse(
            charger_id=result["charger_id"],
            recommended_date=recommended_date,
            urgency=result["urgency"],
            estimated_downtime_hours=result["estimated_downtime_hours"],
            model_version=result["model_version"],
            timestamp=timestamp,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Maintenance prediction failed: {str(e)}"
        )


@router.get("/predictions/{charger_id}", response_model=FailurePredictionResponse)
async def get_cached_prediction(
    charger_id: str,
    api_key: str = Depends(verify_api_key),
):
    """
    Get cached prediction for a charger.
    
    Returns the most recent prediction if available in cache.
    """
    try:
        from src.services.cache_service import CacheService
        
        cache_service = CacheService()
        cached = await cache_service.get_prediction("failure", charger_id)
        
        if not cached:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No cached prediction found for charger {charger_id}. Run a prediction first."
            )
        
        # Convert cached data to response
        predicted_failure_date = cached.get("predicted_failure_date")
        if isinstance(predicted_failure_date, str):
            predicted_failure_date = datetime.fromisoformat(predicted_failure_date.replace('Z', '+00:00'))
        
        timestamp = cached.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        
        return FailurePredictionResponse(
            charger_id=cached["charger_id"],
            failure_probability=cached["failure_probability"],
            predicted_failure_date=predicted_failure_date,
            confidence=cached["confidence"],
            recommended_action=cached["recommended_action"],
            model_version=cached["model_version"],
            timestamp=timestamp,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve cached prediction: {str(e)}"
        )


@router.post("/predictions/batch", response_model=BatchPredictionResponse)
async def batch_predictions(
    request: BatchPredictionRequest,
    api_key: str = Depends(verify_api_key),
):
    """
    Get predictions for multiple chargers in a single request.
    
    Optimized for batch processing.
    """
    try:
        # TODO: Implement batch prediction logic
        predictions = []
        
        for charger in request.chargers:
            # Placeholder prediction
            predictions.append(
                FailurePredictionResponse(
                    charger_id=charger.charger_id,
                    failure_probability=0.15,
                    predicted_failure_date=None,
                    confidence=0.85,
                    recommended_action="Monitor",
                    model_version="v1.0.0",
                    timestamp=datetime.utcnow(),
                )
            )
        
        return BatchPredictionResponse(
            predictions=predictions,
            total=len(predictions),
            timestamp=datetime.utcnow(),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch prediction failed: {str(e)}"
        )


@router.post("/predictions/anomaly", response_model=AnomalyDetectionResponse)
async def detect_anomaly(
    request: AnomalyDetectionRequest,
    api_key: str = Depends(verify_api_key),
):
    """
    Detect anomalies in charger behavior.
    
    Returns anomaly score and classification.
    """
    try:
        from src.services.model_manager import ModelManager
        
        # Initialize model manager
        model_manager = ModelManager()
        
        # Get anomaly detector
        detector = await model_manager.get_model("anomaly_detector")
        if not detector:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Anomaly detector not available"
            )
        
        # Convert Pydantic model to dict
        metrics_dict = request.metrics.model_dump()
        
        # Detect anomalies
        result = detector.detect(metrics_dict)
        
        return AnomalyDetectionResponse(
            charger_id=result["charger_id"],
            is_anomaly=result["is_anomaly"],
            anomaly_score=result["anomaly_score"],
            anomaly_type=result["anomaly_type"],
            deviation=result["deviation"],
            model_version=result["model_version"],
            timestamp=datetime.utcnow(),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Anomaly detection failed: {str(e)}"
        )


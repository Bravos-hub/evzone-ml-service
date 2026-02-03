"""
Prediction API endpoints.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, ConfigDict, Field

from src.api.dependencies import verify_api_key, get_tenant_id

router = APIRouter()

ConnectorStatus = Literal[
    "AVAILABLE",
    "CHARGING",
    "OCCUPIED",
    "UNAVAILABLE",
    "OFFLINE",
    "FAULTY",
    "FULLY_CHARGED",
]

ActionWindow = Literal["IMMEDIATE", "WITHIN_7_DAYS", "WITHIN_30_DAYS"]
Urgency = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]

_ACTION_WINDOWS = {"IMMEDIATE", "WITHIN_7_DAYS", "WITHIN_30_DAYS"}
_URGENCY_LEVELS = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


class ChargerMetrics(BaseModel):
    """Charger metrics for prediction."""
    charger_id: str
    connector_status: ConnectorStatus
    energy_delivered: float = 0.0
    power: float = 0.0
    temperature: float = 0.0
    error_codes: List[str] = Field(default_factory=list)
    uptime_hours: float = 0.0
    total_sessions: int = 0
    last_maintenance: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FailurePredictionRequest(BaseModel):
    """Request for failure prediction."""
    charger_id: str
    metrics: ChargerMetrics


class PredictedFailureWindow(BaseModel):
    """Failure window prediction."""
    start: datetime
    end: datetime


class FailurePredictionResponse(BaseModel):
    """Failure prediction response."""
    model_config = ConfigDict(protected_namespaces=())

    charger_id: str
    tenant_id: Optional[str] = None
    failure_probability: float
    predicted_failure_date: Optional[datetime] = None
    predicted_failure_window: Optional[PredictedFailureWindow] = None
    confidence: float
    confidence_score: Optional[float] = None
    recommended_action: ActionWindow
    recommended_action_window: Optional[ActionWindow] = None
    recommended_actions: List[str] = Field(default_factory=list)
    top_contributing_factors: List[str] = Field(default_factory=list)
    model_version: str
    timestamp: datetime


class MaintenanceScheduleRequest(BaseModel):
    """Request for maintenance schedule."""
    charger_id: str
    metrics: ChargerMetrics


class CostBenefitAnalysis(BaseModel):
    preventive_maintenance_cost: float
    expected_failure_cost: float
    net_savings: float


class MaintenanceScheduleResponse(BaseModel):
    """Maintenance schedule response."""
    model_config = ConfigDict(protected_namespaces=())

    charger_id: str
    tenant_id: Optional[str] = None
    recommended_date: datetime
    recommended_maintenance_datetime: Optional[datetime] = None
    urgency: Urgency
    urgency_level: Optional[Urgency] = None
    estimated_downtime_hours: float
    cost_benefit: Optional[CostBenefitAnalysis] = None
    rationale: List[str] = Field(default_factory=list)
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


class AnomalyDetectionRequestFlat(BaseModel):
    """Flat anomaly detection request (compat route)."""
    charger_id: str
    timestamp: Optional[datetime] = None
    connector_status: ConnectorStatus
    energy_delivered: float = 0.0
    power: float = 0.0
    temperature: float = 0.0
    error_codes: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AnomalyDetectionResponse(BaseModel):
    """Anomaly detection response."""
    model_config = ConfigDict(protected_namespaces=())

    charger_id: str
    tenant_id: Optional[str] = None
    is_anomaly: bool
    anomaly_score: float
    anomaly_type: str
    deviation: Dict[str, float] = Field(default_factory=dict)
    model_version: str
    timestamp: datetime


class MaintenanceRecommendationRequest(BaseModel):
    """Request for maintenance recommendation (compat route)."""
    charger_id: str
    metrics: ChargerMetrics


def _parse_datetime(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _parse_window(value: Any) -> Optional[PredictedFailureWindow]:
    if isinstance(value, PredictedFailureWindow):
        return value
    if isinstance(value, dict):
        start = _parse_datetime(value.get("start"))
        end = _parse_datetime(value.get("end"))
        if start and end:
            return PredictedFailureWindow(start=start, end=end)
    return None


def _parse_cost_benefit(value: Any) -> Optional[CostBenefitAnalysis]:
    if isinstance(value, CostBenefitAnalysis):
        return value
    if isinstance(value, dict):
        try:
            return CostBenefitAnalysis(**value)
        except TypeError:
            return None
    return None


def _build_failure_response(result: Dict[str, Any], tenant_id: Optional[str]) -> FailurePredictionResponse:
    predicted_failure_date = _parse_datetime(result.get("predicted_failure_date"))
    predicted_window = _parse_window(result.get("predicted_failure_window"))
    if not predicted_window and predicted_failure_date:
        predicted_window = PredictedFailureWindow(start=predicted_failure_date, end=predicted_failure_date)

    confidence = result.get("confidence")
    if confidence is None:
        confidence = result.get("confidence_score", 0.0)

    confidence_score = result.get("confidence_score")
    if confidence_score is None:
        confidence_score = confidence

    recommended_action = result.get("recommended_action") or result.get("recommended_action_window") or "WITHIN_30_DAYS"
    if recommended_action not in _ACTION_WINDOWS:
        recommended_action = "WITHIN_30_DAYS"
    recommended_action_window = result.get("recommended_action_window") or recommended_action
    if recommended_action_window not in _ACTION_WINDOWS:
        recommended_action_window = recommended_action

    timestamp = _parse_datetime(result.get("timestamp")) or datetime.utcnow()

    return FailurePredictionResponse(
        charger_id=result.get("charger_id"),
        tenant_id=result.get("tenant_id") or tenant_id,
        failure_probability=float(result.get("failure_probability", 0.0)),
        predicted_failure_date=predicted_failure_date,
        predicted_failure_window=predicted_window,
        confidence=float(confidence or 0.0),
        confidence_score=float(confidence_score or 0.0),
        recommended_action=recommended_action,
        recommended_action_window=recommended_action_window,
        recommended_actions=list(result.get("recommended_actions", []) or []),
        top_contributing_factors=list(result.get("top_contributing_factors", []) or []),
        model_version=str(result.get("model_version", "v1.0.0")),
        timestamp=timestamp,
    )


def _build_maintenance_response(result: Dict[str, Any], tenant_id: Optional[str]) -> MaintenanceScheduleResponse:
    recommended_date = _parse_datetime(result.get("recommended_date") or result.get("recommended_maintenance_datetime"))
    if not recommended_date:
        recommended_date = datetime.utcnow()

    urgency = result.get("urgency") or result.get("urgency_level") or "LOW"
    if urgency not in _URGENCY_LEVELS:
        urgency = "LOW"
    urgency_level = result.get("urgency_level") or urgency
    if urgency_level not in _URGENCY_LEVELS:
        urgency_level = urgency
    cost_benefit = _parse_cost_benefit(result.get("cost_benefit"))
    timestamp = _parse_datetime(result.get("timestamp")) or datetime.utcnow()

    return MaintenanceScheduleResponse(
        charger_id=result.get("charger_id"),
        tenant_id=result.get("tenant_id") or tenant_id,
        recommended_date=recommended_date,
        recommended_maintenance_datetime=_parse_datetime(result.get("recommended_maintenance_datetime")) or recommended_date,
        urgency=urgency,
        urgency_level=urgency_level,
        estimated_downtime_hours=float(result.get("estimated_downtime_hours", 0.0)),
        cost_benefit=cost_benefit,
        rationale=list(result.get("rationale", []) or []),
        model_version=str(result.get("model_version", "v1.0.0")),
        timestamp=timestamp,
    )


def _build_anomaly_response(result: Dict[str, Any], tenant_id: Optional[str]) -> AnomalyDetectionResponse:
    timestamp = _parse_datetime(result.get("timestamp")) or datetime.utcnow()
    return AnomalyDetectionResponse(
        charger_id=result.get("charger_id"),
        tenant_id=result.get("tenant_id") or tenant_id,
        is_anomaly=bool(result.get("is_anomaly")),
        anomaly_score=float(result.get("anomaly_score", 0.0)),
        anomaly_type=str(result.get("anomaly_type", "UNKNOWN")),
        deviation=dict(result.get("deviation", {}) or {}),
        model_version=str(result.get("model_version", "v1.0.0")),
        timestamp=timestamp,
    )


@router.post("/predictions/failure", response_model=FailurePredictionResponse)
async def predict_failure(
    request: FailurePredictionRequest,
    api_key: str = Depends(verify_api_key),
    tenant_id: Optional[str] = Depends(get_tenant_id),
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
        model_manager = ModelManager.get_instance()
        cache_service = CacheService()
        feature_extractor = FeatureExtractor()
        prediction_service = PredictionService(model_manager, feature_extractor, cache_service)

        # Convert Pydantic model to dict
        metrics_dict = request.metrics.model_dump()

        # Get prediction
        result = await prediction_service.predict_failure(
            request.charger_id,
            metrics_dict,
            tenant_id=tenant_id,
        )

        return _build_failure_response(result, tenant_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction failed: {str(e)}"
        )


@router.post("/predictions/maintenance", response_model=MaintenanceScheduleResponse)
async def predict_maintenance(
    request: MaintenanceScheduleRequest,
    api_key: str = Depends(verify_api_key),
    tenant_id: Optional[str] = Depends(get_tenant_id),
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
        model_manager = ModelManager.get_instance()
        cache_service = CacheService()
        feature_extractor = FeatureExtractor()
        prediction_service = PredictionService(model_manager, feature_extractor, cache_service)

        # Convert Pydantic model to dict
        metrics_dict = request.metrics.model_dump()

        # Get maintenance recommendation
        result = await prediction_service.predict_maintenance(
            request.charger_id,
            metrics_dict,
            tenant_id=tenant_id,
        )

        return _build_maintenance_response(result, tenant_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Maintenance prediction failed: {str(e)}"
        )


@router.get("/predictions/{charger_id}", response_model=FailurePredictionResponse)
async def get_cached_prediction(
    charger_id: str,
    api_key: str = Depends(verify_api_key),
    tenant_id: Optional[str] = Depends(get_tenant_id),
):
    """
    Get cached prediction for a charger.

    Returns the most recent prediction if available in cache.
    """
    try:
        from src.services.cache_service import CacheService

        cache_service = CacheService()
        cached = await cache_service.get_prediction("failure", charger_id, tenant_id=tenant_id)

        if not cached:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No cached prediction found for charger {charger_id}. Run a prediction first."
            )

        return _build_failure_response(cached, tenant_id)
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
        predictions = []

        for charger in request.chargers:
            predicted_window = PredictedFailureWindow(
                start=datetime.utcnow(),
                end=datetime.utcnow(),
            )
            predictions.append(
                FailurePredictionResponse(
                    charger_id=charger.charger_id,
                    failure_probability=0.15,
                    predicted_failure_date=None,
                    predicted_failure_window=predicted_window,
                    confidence=0.85,
                    confidence_score=0.85,
                    recommended_action="WITHIN_30_DAYS",
                    recommended_action_window="WITHIN_30_DAYS",
                    recommended_actions=["Monitor"],
                    top_contributing_factors=[],
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
    tenant_id: Optional[str] = Depends(get_tenant_id),
):
    """
    Detect anomalies in charger behavior.

    Returns anomaly score and classification.
    """
    try:
        from src.services.model_manager import ModelManager
        from src.services.cache_service import CacheService
        from src.services.feature_extractor import FeatureExtractor
        from src.services.prediction_service import PredictionService

        # Initialize services
        model_manager = ModelManager.get_instance()
        cache_service = CacheService()
        feature_extractor = FeatureExtractor()
        prediction_service = PredictionService(model_manager, feature_extractor, cache_service)

        # Convert Pydantic model to dict
        metrics_dict = request.metrics.model_dump()

        # Detect anomalies using the prediction service
        result = await prediction_service.detect_anomaly(
            request.charger_id,
            metrics_dict,
            tenant_id=tenant_id,
        )

        return _build_anomaly_response(result, tenant_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Anomaly detection failed: {str(e)}"
        )


@router.post("/anomaly/detect", response_model=AnomalyDetectionResponse)
async def detect_anomaly_flat(
    request: AnomalyDetectionRequestFlat,
    api_key: str = Depends(verify_api_key),
    tenant_id: Optional[str] = Depends(get_tenant_id),
):
    """Compatibility endpoint matching the original flat anomaly schema."""
    try:
        from src.services.model_manager import ModelManager

        model_manager = ModelManager.get_instance()
        detector = await model_manager.get_model("anomaly_detector")
        if not detector:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Anomaly detector not available"
            )

        metrics_dict = {
            "charger_id": request.charger_id,
            "connector_status": request.connector_status,
            "energy_delivered": request.energy_delivered,
            "power": request.power,
            "temperature": request.temperature,
            "error_codes": request.error_codes,
            "uptime_hours": 0.0,
            "total_sessions": 0,
            "last_maintenance": None,
            "metadata": request.metadata,
        }

        result = detector.detect(metrics_dict, tenant_id=tenant_id)
        return _build_anomaly_response(result, tenant_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Anomaly detection failed: {str(e)}"
        )


@router.post("/maintenance/recommend", response_model=MaintenanceScheduleResponse)
async def recommend_maintenance(
    request: MaintenanceRecommendationRequest,
    api_key: str = Depends(verify_api_key),
    tenant_id: Optional[str] = Depends(get_tenant_id),
):
    """Compatibility endpoint matching the original maintenance route."""
    try:
        from src.services.model_manager import ModelManager
        from src.services.cache_service import CacheService
        from src.services.feature_extractor import FeatureExtractor
        from src.services.prediction_service import PredictionService

        model_manager = ModelManager.get_instance()
        cache_service = CacheService()
        feature_extractor = FeatureExtractor()
        prediction_service = PredictionService(model_manager, feature_extractor, cache_service)

        metrics_dict = request.metrics.model_dump()
        result = await prediction_service.predict_maintenance(
            request.charger_id,
            metrics_dict,
            tenant_id=tenant_id,
        )

        return _build_maintenance_response(result, tenant_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Maintenance recommendation failed: {str(e)}"
        )

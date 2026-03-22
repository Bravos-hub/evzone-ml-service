"""
API dependencies (authentication, rate limiting, etc.).
"""
from typing import Optional
from fastapi import Depends, Header, HTTPException, status
from src.config.settings import settings


async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    """Verify API key from header."""
    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return x_api_key


async def get_tenant_id(
    x_tenant_id: Optional[str] = Header(default=None, alias=settings.tenant_header),
) -> Optional[str]:
    """Get tenant identifier from request headers."""
    return x_tenant_id


async def get_model_manager():
    from src.services.model_manager import ModelManager
    return ModelManager.get_instance()


async def get_cache_service():
    from src.services.cache_service import CacheService
    return CacheService()


async def get_feature_extractor():
    from src.services.feature_extractor import FeatureExtractor
    return FeatureExtractor()


async def get_prediction_service(
    model_manager=Depends(get_model_manager),
    cache_service=Depends(get_cache_service),
    feature_extractor=Depends(get_feature_extractor)
):
    from src.services.prediction_service import PredictionService
    return PredictionService(model_manager, feature_extractor, cache_service)

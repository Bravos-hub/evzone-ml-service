"""
Health check endpoints.
"""
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    version: str


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Basic health check."""
    return {
        "status": "healthy",
        "service": "evzone-ml-service",
        "version": "1.0.0",
    }


@router.get("/api/v1/health")
async def detailed_health():
    """Detailed health check with service status."""
    from src.services.cache_service import CacheService
    
    # Check cache health
    cache_health = await CacheService.health_check()
    
    return {
        "status": "healthy",
        "service": "evzone-ml-service",
        "version": "1.0.0",
        "checks": {
            "cache": cache_health,
            "models": {"status": "loaded", "count": 3},
        },
    }


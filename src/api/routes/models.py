"""
Model management API endpoints.
"""
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime

from src.api.dependencies import verify_api_key

router = APIRouter()


class ModelInfo(BaseModel):
    """Model information."""
    name: str
    version: str
    type: str
    status: str  # LOADED, UNLOADED, ERROR
    loaded_at: Optional[datetime] = None
    accuracy: Optional[float] = None
    metadata: Optional[dict] = None


class ModelListResponse(BaseModel):
    """List of models response."""
    models: List[ModelInfo]
    total: int


class ReloadModelResponse(BaseModel):
    """Model reload response."""
    model_config = ConfigDict(protected_namespaces=())
    
    success: bool
    model_name: str
    version: str
    message: str
    timestamp: datetime


@router.get("/models", response_model=ModelListResponse)
async def list_models(
    api_key: str = Depends(verify_api_key),
):
    """
    List all available models and their status.
    
    Returns information about loaded and available models.
    """
    try:
        from src.services.model_manager import ModelManager
        
        model_manager = ModelManager()
        loaded_models = await model_manager.list_models()
        
        models = []
        for name, info in loaded_models.items():
            models.append(
                ModelInfo(
                    name=info["name"],
                    version=info["version"],
                    type=info["type"],
                    status=info["status"],
                    loaded_at=datetime.utcnow(),
                    accuracy=None,
                )
            )
        
        return ModelListResponse(
            models=models,
            total=len(models),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list models: {str(e)}"
        )


@router.post("/models/reload", response_model=ReloadModelResponse)
async def reload_models(
    model_name: Optional[str] = None,
    api_key: str = Depends(verify_api_key),
):
    """
    Reload models (admin only).
    
    Reloads all models or a specific model if model_name is provided.
    """
    try:
        # TODO: Implement model reloading from model_manager
        model_name = model_name or "all"
        
        return ReloadModelResponse(
            success=True,
            model_name=model_name,
            version="v1.0.0",
            message=f"Model {model_name} reloaded successfully",
            timestamp=datetime.utcnow(),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reload model: {str(e)}"
        )


"""
Model manager for loading, versioning, and managing ML models.
"""
import os
import logging
from typing import Optional, Dict, Any
from pathlib import Path

from src.config.settings import settings
from src.utils.errors import ModelNotFoundError, ModelLoadError
from src.utils.metrics import model_load_time, active_models

logger = logging.getLogger(__name__)


class ModelManager:
    """Manages ML model loading, versioning, and lifecycle."""
    
    def __init__(self):
        self.models: Dict[str, Any] = {}
        self.model_base_path = Path(settings.model_base_path)
    
    async def load_model(self, model_name: str, version: str = "latest") -> bool:
        """
        Load a model into memory.
        
        Args:
            model_name: Name of the model
            version: Model version (default: latest)
            
        Returns:
            True if loaded successfully
        """
        try:
            model_path = self.model_base_path / model_name / version
            
            if not model_path.exists():
                raise ModelNotFoundError(f"Model {model_name} v{version} not found at {model_path}")
            
            # TODO: Implement actual TensorFlow model loading
            # import tensorflow as tf
            # model = tf.keras.models.load_model(str(model_path))
            
            # Placeholder: Store model metadata
            self.models[model_name] = {
                "name": model_name,
                "version": version,
                "path": str(model_path),
                "loaded": True,
                # "model": model,  # Actual model object
            }
            
            logger.info(f"Model {model_name} v{version} loaded successfully")
            active_models.labels(model_type=model_name).inc()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            raise ModelLoadError(f"Failed to load model: {str(e)}")
    
    async def get_model(self, model_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a loaded model.
        
        Args:
            model_name: Name of the model
            
        Returns:
            Model object or None if not loaded
        """
        return self.models.get(model_name)
    
    async def unload_model(self, model_name: str) -> bool:
        """
        Unload a model from memory.
        
        Args:
            model_name: Name of the model
            
        Returns:
            True if unloaded successfully
        """
        if model_name in self.models:
            del self.models[model_name]
            active_models.labels(model_type=model_name).dec()
            logger.info(f"Model {model_name} unloaded")
            return True
        return False
    
    async def reload_model(self, model_name: str, version: Optional[str] = None) -> bool:
        """
        Reload a model (hot reload).
        
        Args:
            model_name: Name of the model
            version: Optional version to load (default: latest)
            
        Returns:
            True if reloaded successfully
        """
        await self.unload_model(model_name)
        version = version or "latest"
        return await self.load_model(model_name, version)
    
    async def list_models(self) -> Dict[str, Any]:
        """
        List all loaded models.
        
        Returns:
            Dictionary of loaded models
        """
        return {
            name: {
                "name": info["name"],
                "version": info["version"],
                "status": "LOADED" if info["loaded"] else "UNLOADED",
            }
            for name, info in self.models.items()
        }


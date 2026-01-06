"""Model manager for loading, versioning, and managing ML models."""
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
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize ML model instances."""
        try:
            from src.ml.models import FailurePredictor, AnomalyDetector, MaintenanceOptimizer
            
            self.models["failure_predictor"] = FailurePredictor()
            self.models["anomaly_detector"] = AnomalyDetector()
            self.models["maintenance_optimizer"] = MaintenanceOptimizer()
            
            logger.info("ML models initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize models: {e}")
    
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
            # Models are already initialized in __init__
            if model_name in self.models:
                logger.info(f"Model {model_name} already loaded")
                return True
            
            # Reinitialize if needed
            self._initialize_models()
            
            if model_name in self.models:
                active_models.labels(model_type=model_name).inc()
                return True
            
            raise ModelNotFoundError(f"Model {model_name} not available")
            
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            raise ModelLoadError(f"Failed to load model: {str(e)}")
    
    async def get_model(self, model_name: str) -> Optional[Any]:
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
                "name": name,
                "version": "v1.0.0",
                "status": "LOADED",
                "type": type(model).__name__,
            }
            for name, model in self.models.items()
        }


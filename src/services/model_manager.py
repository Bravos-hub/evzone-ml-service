"""Model manager for loading, versioning, and managing ML models."""
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict, Any
from pathlib import Path

from src.config.settings import settings
from src.utils.errors import ModelNotFoundError, ModelLoadError
from src.utils.metrics import model_load_time, active_models

logger = logging.getLogger(__name__)


class ModelManager:
    """Manages ML model loading, versioning, and lifecycle."""
    
    _instance: Optional['ModelManager'] = None

    def __init__(self):
        self.models: Dict[str, Any] = {}
        self.model_base_path = Path(settings.model_base_path)
        self._init_lock = None
        # We do not call _initialize_models() here to prevent blocking in async contexts.
        # It should be called explicitly via `await self.initialize_models()`.

    @classmethod
    def get_instance(cls) -> 'ModelManager':
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = ModelManager()
        return cls._instance
    
    async def initialize_models(self, force: bool = False):
        """Initialize ML model instances asynchronously."""
        import asyncio
        if getattr(self, "_init_lock", None) is None:
            self._init_lock = asyncio.Lock()

        async with self._init_lock:
            if self.models and not force:
                return

            try:
                # Correctly import model classes
                from src.ml.models.failure_predictor import FailurePredictor
                from src.ml.models.anomaly_detector import AnomalyDetector
                from src.ml.models.maintenance_optimizer import MaintenanceOptimizer

                # Construct model paths
                failure_model_path = self.model_base_path / f"{settings.model_failure_predictor}.joblib"
                anomaly_model_path = self.model_base_path / f"{settings.model_anomaly_detector}.joblib"

                maintenance_model_path = self.model_base_path / f"{settings.model_maintenance_scheduler}.joblib"

                import functools
                # Instantiate models with their paths in a thread pool to avoid blocking the event loop
                loop = asyncio.get_running_loop()
                with ThreadPoolExecutor(max_workers=3) as executor:
                    tasks = [
                        loop.run_in_executor(executor, functools.partial(FailurePredictor, model_path=failure_model_path)),
                        loop.run_in_executor(executor, functools.partial(AnomalyDetector, model_path=anomaly_model_path)),
                        loop.run_in_executor(executor, functools.partial(MaintenanceOptimizer, model_path=maintenance_model_path))
                    ]

                    failure_model, anomaly_model, maintenance_model = await asyncio.gather(*tasks)

                self.models["failure_predictor"] = failure_model
                self.models["anomaly_detector"] = anomaly_model
                self.models["maintenance_optimizer"] = maintenance_model

                logger.info("ML models initialized successfully")
                for model_name in self.models:
                    active_models.labels(model_type=model_name).set(1)
            except ImportError as e:
                logger.error(f"Failed to import model class: {e}")
                # This is a critical error, so we should probably exit or handle it gracefully
                raise ModelLoadError(f"Failed to import a model class: {e}") from e
            except Exception as e:
                logger.error(f"Failed to initialize models: {e}")
                raise ModelLoadError(f"Failed to initialize models: {e}") from e
    
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
            # Check if model is already loaded
            if model_name in self.models:
                logger.info(f"Model {model_name} already loaded")
                return True
            
            # Since models are normally loaded altogether, initialize them if missing
            await self.initialize_models()
            
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
        # Note: In our current design all models are loaded together,
        # so unloading one means we will force a re-initialization of all if missing.
        # Calling initialize_models(force=True) to reload everything is safer.
        await self.initialize_models(force=True)
        return True
    
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


"""
Feature extraction service for preparing data for ML models.
"""
import logging
from typing import Dict, Any, List
import numpy as np
from datetime import datetime, timedelta

from src.utils.errors import FeatureExtractionError

logger = logging.getLogger(__name__)


class FeatureExtractor:
    """Extracts and engineers features from charger metrics."""
    
    async def extract_failure_features(
        self,
        charger_id: str,
        metrics: Dict[str, Any],
    ) -> np.ndarray:
        """
        Extract features for failure prediction.
        
        Args:
            charger_id: Charger identifier
            metrics: Raw charger metrics
            
        Returns:
            Feature vector as numpy array
        """
        try:
            # TODO: Implement comprehensive feature engineering
            # This is a placeholder structure
            
            features = [
                metrics.get("uptime_hours", 0),
                metrics.get("total_sessions", 0),
                metrics.get("energy_delivered", 0),
                len(metrics.get("error_codes", [])),
                metrics.get("temperature", 25.0),
                metrics.get("power", 0),
            ]
            
            # Normalize features (placeholder)
            # In production, use trained scaler
            
            return np.array(features, dtype=np.float32)
            
        except Exception as e:
            logger.error(f"Feature extraction failed: {e}")
            raise FeatureExtractionError(f"Failed to extract features: {str(e)}")
    
    async def extract_maintenance_features(
        self,
        charger_id: str,
        metrics: Dict[str, Any],
    ) -> np.ndarray:
        """
        Extract features for maintenance scheduling.
        
        Args:
            charger_id: Charger identifier
            metrics: Raw charger metrics
            
        Returns:
            Feature vector as numpy array
        """
        try:
            # TODO: Implement maintenance-specific feature engineering
            
            last_maintenance = metrics.get("last_maintenance")
            days_since_maintenance = 0
            if last_maintenance:
                if isinstance(last_maintenance, str):
                    last_maintenance = datetime.fromisoformat(last_maintenance)
                days_since_maintenance = (datetime.utcnow() - last_maintenance).days
            
            features = [
                metrics.get("uptime_hours", 0),
                metrics.get("total_sessions", 0),
                days_since_maintenance,
                len(metrics.get("error_codes", [])),
                metrics.get("energy_delivered", 0),
            ]
            
            return np.array(features, dtype=np.float32)
            
        except Exception as e:
            logger.error(f"Maintenance feature extraction failed: {e}")
            raise FeatureExtractionError(f"Failed to extract maintenance features: {str(e)}")
    
    async def extract_anomaly_features(
        self,
        charger_id: str,
        metrics: Dict[str, Any],
        historical_data: List[Dict[str, Any]],
    ) -> np.ndarray:
        """
        Extract features for anomaly detection.
        
        Args:
            charger_id: Charger identifier
            metrics: Current charger metrics
            historical_data: Historical metrics for comparison
            
        Returns:
            Feature vector as numpy array
        """
        try:
            # TODO: Implement anomaly detection feature engineering
            # Compare current metrics with historical patterns
            
            features = [
                metrics.get("power", 0),
                metrics.get("temperature", 25.0),
                metrics.get("energy_delivered", 0),
            ]
            
            return np.array(features, dtype=np.float32)
            
        except Exception as e:
            logger.error(f"Anomaly feature extraction failed: {e}")
            raise FeatureExtractionError(f"Failed to extract anomaly features: {str(e)}")


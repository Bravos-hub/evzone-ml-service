"""
Feature extraction service for preparing data for ML models.
"""
import logging
from typing import Dict, Any, List
import numpy as np
from datetime import datetime, timedelta

from src.utils.errors import FeatureExtractionError
from src.ml.preprocessing.feature_engineering import extract_features, features_to_vector

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
            # Base features from standard feature extraction
            base_features = extract_features(metrics)
            feature_list = features_to_vector(base_features)

            # Derive failure probability, similar to training
            failure_prob = 0.0
            for col in ["failure_probability_synth", "failure_probability", "failure_prob", "failure_within_30d_label"]:
                if col in metrics and metrics[col] is not None:
                    try:
                        failure_prob = float(metrics[col])
                        break
                    except (ValueError, TypeError):
                        continue

            feature_list.append(failure_prob)
            
            return np.array(feature_list, dtype=np.float32)
            
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


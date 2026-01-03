"""
Feature engineering utilities.
"""
import numpy as np
from typing import List, Dict, Any


def normalize_features(features: np.ndarray, mean: np.ndarray, std: np.ndarray) -> np.ndarray:
    """
    Normalize features using mean and standard deviation.
    
    Args:
        features: Raw features
        mean: Mean values for normalization
        std: Standard deviation values for normalization
        
    Returns:
        Normalized features
    """
    return (features - mean) / (std + 1e-8)


def create_time_features(timestamp) -> List[float]:
    """
    Create time-based features.
    
    Args:
        timestamp: Datetime object
        
    Returns:
        List of time features (hour, day_of_week, month, etc.)
    """
    return [
        timestamp.hour / 24.0,
        timestamp.weekday() / 7.0,
        timestamp.month / 12.0,
    ]


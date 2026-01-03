"""
Custom exception classes.
"""


class MLServiceError(Exception):
    """Base exception for ML service."""
    pass


class ModelNotFoundError(MLServiceError):
    """Raised when a model is not found."""
    pass


class ModelLoadError(MLServiceError):
    """Raised when model loading fails."""
    pass


class PredictionError(MLServiceError):
    """Raised when prediction fails."""
    pass


class FeatureExtractionError(MLServiceError):
    """Raised when feature extraction fails."""
    pass


class CacheError(MLServiceError):
    """Raised when cache operation fails."""
    pass


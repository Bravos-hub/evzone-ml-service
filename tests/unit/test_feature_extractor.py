"""
Unit tests for feature extractor.
"""
import pytest
import numpy as np
from src.services.feature_extractor import FeatureExtractor


@pytest.mark.asyncio
async def test_extract_failure_features(mock_charger_metrics):
    """Test failure feature extraction."""
    extractor = FeatureExtractor()
    features = await extractor.extract_failure_features(
        "test-charger-1",
        mock_charger_metrics,
    )
    
    assert isinstance(features, np.ndarray)
    assert len(features) > 0


@pytest.mark.asyncio
async def test_extract_maintenance_features(mock_charger_metrics):
    """Test maintenance feature extraction."""
    extractor = FeatureExtractor()
    features = await extractor.extract_maintenance_features(
        "test-charger-1",
        mock_charger_metrics,
    )
    
    assert isinstance(features, np.ndarray)
    assert len(features) > 0


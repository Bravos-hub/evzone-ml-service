"""
Unit tests for feature extractor.
"""
from datetime import datetime

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


@pytest.mark.asyncio
async def test_extract_maintenance_features_parses_string_date():
    extractor = FeatureExtractor()
    metrics = {
        "uptime_hours": 10.0,
        "total_sessions": 2,
        "error_codes": [],
        "energy_delivered": 5.0,
        "last_maintenance": datetime.utcnow().isoformat(),
    }

    features = await extractor.extract_maintenance_features("test-charger-2", metrics)

    assert isinstance(features, np.ndarray)
    assert len(features) == 5


@pytest.mark.asyncio
async def test_extract_anomaly_features():
    extractor = FeatureExtractor()
    metrics = {
        "power": 3.0,
        "temperature": 30.0,
        "energy_delivered": 12.0,
    }

    features = await extractor.extract_anomaly_features("test-charger-3", metrics, [])

    assert isinstance(features, np.ndarray)
    assert len(features) == 3


@pytest.mark.asyncio
async def test_extract_failure_features_error():
    extractor = FeatureExtractor()
    with pytest.raises(Exception):
        await extractor.extract_failure_features("test-charger-1", None)


@pytest.mark.asyncio
async def test_extract_maintenance_features_error():
    extractor = FeatureExtractor()
    with pytest.raises(Exception):
        await extractor.extract_maintenance_features("test-charger-1", {"last_maintenance": "bad-date"})


@pytest.mark.asyncio
async def test_extract_anomaly_features_error():
    extractor = FeatureExtractor()
    with pytest.raises(Exception):
        await extractor.extract_anomaly_features("test-charger-1", None, [])

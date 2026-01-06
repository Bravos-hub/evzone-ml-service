#!/usr/bin/env python3
"""Test script to validate ML model integration."""
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

def test_feature_engineering():
    """Test feature engineering module."""
    print("Testing feature engineering...")
    from src.ml.preprocessing import extract_features, features_to_vector
    
    metrics = {
        "charger_id": "test_001",
        "connector_status": "CHARGING",
        "temperature": 45.0,
        "error_codes": ["E_OVER_TEMP"],
        "uptime_hours": 2000,
        "total_sessions": 400,
        "energy_delivered": 50.0,
        "power": 7.2,
        "last_maintenance": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "metadata": {}
    }
    
    features = extract_features(metrics)
    vector = features_to_vector(features)
    
    print(f"  ✓ Features extracted: {len(features)} features")
    print(f"  ✓ Vector created: {len(vector)} dimensions")
    assert len(vector) == 8, "Expected 8 features"
    print("  ✓ Feature engineering working!\n")


def test_failure_predictor():
    """Test failure predictor model."""
    print("Testing failure predictor...")
    from src.ml.models import FailurePredictor
    
    predictor = FailurePredictor()
    
    metrics = {
        "charger_id": "test_001",
        "connector_status": "CHARGING",
        "temperature": 55.0,
        "error_codes": ["E_OVER_TEMP", "E_CONTACTOR"],
        "uptime_hours": 2500,
        "total_sessions": 600,
        "energy_delivered": 50.0,
        "power": 7.2,
        "last_maintenance": datetime(2023, 6, 1, tzinfo=timezone.utc),
        "metadata": {}
    }
    
    result = predictor.predict(metrics)
    
    print(f"  ✓ Charger ID: {result['charger_id']}")
    print(f"  ✓ Failure probability: {result['failure_probability']:.2%}")
    print(f"  ✓ Confidence: {result['confidence']:.2%}")
    print(f"  ✓ Action window: {result['recommended_action']}")
    print(f"  ✓ Recommendations: {len(result['recommended_actions'])} actions")
    print(f"  ✓ Contributing factors: {len(result['top_contributing_factors'])} factors")
    
    assert 0 <= result['failure_probability'] <= 1, "Probability out of range"
    assert result['charger_id'] == "test_001", "Charger ID mismatch"
    print("  ✓ Failure predictor working!\n")


def test_anomaly_detector():
    """Test anomaly detector model."""
    print("Testing anomaly detector...")
    from src.ml.models import AnomalyDetector
    
    detector = AnomalyDetector()
    
    # Normal metrics
    normal_metrics = {
        "charger_id": "test_002",
        "connector_status": "CHARGING",
        "temperature": 30.0,
        "error_codes": [],
        "uptime_hours": 1000,
        "total_sessions": 200,
        "energy_delivered": 40.0,
        "power": 7.2,
        "metadata": {}
    }
    
    # Anomalous metrics
    anomalous_metrics = {
        "charger_id": "test_003",
        "connector_status": "CHARGING",
        "temperature": 70.0,
        "error_codes": ["E_OVER_TEMP", "E_GFCI_TRIP"],
        "uptime_hours": 3000,
        "total_sessions": 800,
        "energy_delivered": 40.0,
        "power": 0.1,  # Low power during charging
        "metadata": {}
    }
    
    normal_result = detector.detect(normal_metrics)
    anomaly_result = detector.detect(anomalous_metrics)
    
    print(f"  Normal case:")
    print(f"    - Is anomaly: {normal_result['is_anomaly']}")
    print(f"    - Score: {normal_result['anomaly_score']:.1f}")
    print(f"    - Type: {normal_result['anomaly_type']}")
    
    print(f"  Anomalous case:")
    print(f"    - Is anomaly: {anomaly_result['is_anomaly']}")
    print(f"    - Score: {anomaly_result['anomaly_score']:.1f}")
    print(f"    - Type: {anomaly_result['anomaly_type']}")
    
    assert 0 <= normal_result['anomaly_score'] <= 100, "Score out of range"
    print("  ✓ Anomaly detector working!\n")


def test_maintenance_optimizer():
    """Test maintenance optimizer model."""
    print("Testing maintenance optimizer...")
    from src.ml.models import MaintenanceOptimizer, FailurePredictor
    
    optimizer = MaintenanceOptimizer()
    predictor = FailurePredictor()
    
    metrics = {
        "charger_id": "test_004",
        "connector_status": "AVAILABLE",
        "temperature": 48.0,
        "error_codes": ["E_OVER_TEMP"],
        "uptime_hours": 2200,
        "total_sessions": 500,
        "energy_delivered": 45.0,
        "power": 7.2,
        "last_maintenance": datetime(2023, 1, 1, tzinfo=timezone.utc),
        "metadata": {"cost_per_kwh": 3000, "utilization_factor": 0.4}
    }
    
    # Get failure prediction first
    failure_pred = predictor.predict(metrics)
    
    # Get maintenance recommendation
    result = optimizer.recommend(metrics, failure_pred)
    
    print(f"  ✓ Charger ID: {result['charger_id']}")
    print(f"  ✓ Urgency: {result['urgency']}")
    print(f"  ✓ Recommended date: {result['recommended_date']}")
    print(f"  ✓ Estimated downtime: {result['estimated_downtime_hours']:.1f} hours")
    print(f"  ✓ Cost-benefit analysis:")
    print(f"    - Preventive cost: ${result['cost_benefit']['preventive_maintenance_cost']:.2f}")
    print(f"    - Expected failure cost: ${result['cost_benefit']['expected_failure_cost']:.2f}")
    print(f"    - Net savings: ${result['cost_benefit']['net_savings']:.2f}")
    print(f"  ✓ Rationale: {len(result['rationale'])} points")
    
    assert result['urgency'] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"], "Invalid urgency"
    print("  ✓ Maintenance optimizer working!\n")


def test_model_manager():
    """Test model manager."""
    print("Testing model manager...")
    from src.services.model_manager import ModelManager
    
    manager = ModelManager()
    
    # Check models are loaded
    models = manager.models
    print(f"  ✓ Loaded models: {list(models.keys())}")
    
    assert "failure_predictor" in models, "Failure predictor not loaded"
    assert "anomaly_detector" in models, "Anomaly detector not loaded"
    assert "maintenance_optimizer" in models, "Maintenance optimizer not loaded"
    
    print("  ✓ Model manager working!\n")


def test_synthetic_data():
    """Test synthetic data generation."""
    print("Testing synthetic data generation...")
    from src.ml.data import generate_synthetic_charger_metrics
    
    df = generate_synthetic_charger_metrics(n_rows=100, n_chargers=5, seed=42)
    
    print(f"  ✓ Generated {len(df)} rows")
    print(f"  ✓ Columns: {list(df.columns)}")
    print(f"  ✓ Unique chargers: {df['charger_id'].nunique()}")
    print(f"  ✓ Status distribution:")
    for status, count in df['connector_status'].value_counts().head(3).items():
        print(f"    - {status}: {count}")
    
    assert len(df) == 100, "Expected 100 rows"
    print("  ✓ Synthetic data generation working!\n")


def main():
    """Run all tests."""
    print("=" * 60)
    print("ML MODELS INTEGRATION TEST")
    print("=" * 60)
    print()
    
    tests = [
        test_feature_engineering,
        test_failure_predictor,
        test_anomaly_detector,
        test_maintenance_optimizer,
        test_model_manager,
        test_synthetic_data,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  ✗ Test failed: {e}\n")
            failed += 1
    
    print("=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("✓ All tests passed! Integration successful!")
        return 0
    else:
        print("✗ Some tests failed. Please review errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

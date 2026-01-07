"""
Unit tests for ML models.
"""
from datetime import datetime, timedelta, timezone

import joblib
import numpy as np
import pytest

from src.ml.models import FailurePredictor, AnomalyDetector, MaintenanceOptimizer
from src.ml.preprocessing.feature_engineering import FEATURE_ORDER


class DummyFailureModel:
    def __init__(self, proba: float = 0.8) -> None:
        self.proba = float(proba)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return np.array([[1.0 - self.proba, self.proba] for _ in range(len(X))], dtype=float)


class DummyAnomalyModel:
    def __init__(self, normality: float = -2.0) -> None:
        self.normality = float(normality)

    def score_samples(self, X: np.ndarray) -> np.ndarray:
        return np.array([self.normality for _ in range(len(X))], dtype=float)


class DummyMaintenanceModel:
    def __init__(self, label: str = "HIGH") -> None:
        self.label = str(label)

    def predict(self, X: np.ndarray) -> np.ndarray:
        return np.array([self.label for _ in range(len(X))], dtype=object)


def test_failure_predictor_uses_trained_model(tmp_path, mock_charger_metrics):
    model_path = tmp_path / "failure_model.joblib"
    joblib.dump(DummyFailureModel(proba=0.8), model_path)

    predictor = FailurePredictor(model_path=model_path)
    metrics = dict(mock_charger_metrics)
    metrics["last_maintenance"] = datetime.now(timezone.utc) - timedelta(days=10)

    result = predictor.predict(metrics)

    assert isinstance(predictor.model, DummyFailureModel)
    assert result["failure_probability"] == pytest.approx(0.8)


def test_failure_predictor_rule_based_higher_for_risky_metrics(tmp_path, mock_charger_metrics):
    predictor = FailurePredictor(model_path=tmp_path / "missing_failure_model.joblib")
    now = datetime.now(timezone.utc)

    low_metrics = dict(mock_charger_metrics)
    low_metrics.update(
        {
            "connector_status": "AVAILABLE",
            "temperature": 10.0,
            "error_codes": [],
            "uptime_hours": 10.0,
            "total_sessions": 1,
            "last_maintenance": now - timedelta(days=3),
        }
    )

    high_metrics = dict(mock_charger_metrics)
    high_metrics.update(
        {
            "connector_status": "FAULTY",
            "temperature": 70.0,
            "error_codes": ["E1", "E2"],
            "uptime_hours": 5000.0,
            "total_sessions": 1000,
            "last_maintenance": now - timedelta(days=400),
        }
    )

    low = predictor.predict(low_metrics)
    high = predictor.predict(high_metrics)

    assert high["failure_probability"] > low["failure_probability"] + 0.1
    assert high["recommended_action_window"] == "IMMEDIATE"


def test_anomaly_detector_rule_based_flags_overtemp(tmp_path, mock_charger_metrics):
    detector = AnomalyDetector(model_path=tmp_path / "missing_anomaly_model.joblib")

    hot_metrics = dict(mock_charger_metrics)
    hot_metrics.update({"temperature": 65.0, "connector_status": "AVAILABLE", "error_codes": []})

    result = detector.detect(hot_metrics)
    assert result["is_anomaly"] is True
    assert result["anomaly_type"] == "OVER_TEMPERATURE_CRITICAL"
    assert result["anomaly_score"] >= 60.0
    assert result["deviation"] == {}

    normal = detector.detect(dict(mock_charger_metrics))
    assert normal["is_anomaly"] is False
    assert normal["anomaly_type"] == "NORMAL"


def test_anomaly_detector_loaded_model_bundle(tmp_path, mock_charger_metrics):
    model_path = tmp_path / "anomaly_model.joblib"
    bundle = {
        "model": DummyAnomalyModel(normality=-2.0),
        "raw_min": 0.0,
        "raw_max": 4.0,
        "mean": [0.0] * 5,
        "std": [1.0] * 5,
    }
    joblib.dump(bundle, model_path)

    detector = AnomalyDetector(model_path=model_path)
    result = detector.detect(dict(mock_charger_metrics))

    assert result["anomaly_score"] == pytest.approx(50.0)
    assert result["is_anomaly"] is False
    assert set(result["deviation"].keys()) == {
        "status_int",
        "energy_delivered",
        "power",
        "temperature",
        "error_count",
    }
    assert all(isinstance(v, float) for v in result["deviation"].values())


def test_maintenance_optimizer_fallback_urgency(tmp_path, mock_charger_metrics):
    optimizer = MaintenanceOptimizer(model_path=tmp_path / "missing_maintenance_model.joblib")
    predicted_failure_date = datetime.now(timezone.utc) + timedelta(days=10)

    result = optimizer.recommend(
        dict(mock_charger_metrics),
        {
            "failure_probability": 0.9,
            "predicted_failure_date": predicted_failure_date,
        },
    )

    assert result["urgency"] == "CRITICAL"
    assert result["recommended_maintenance_datetime"] < predicted_failure_date
    assert 1.0 <= result["estimated_downtime_hours"] <= 12.0


def test_maintenance_optimizer_loaded_model_predicts(tmp_path, mock_charger_metrics):
    model_path = tmp_path / "maintenance_model.joblib"
    joblib.dump(
        {
            "model": DummyMaintenanceModel(label="HIGH"),
            "feature_order": FEATURE_ORDER + ["failure_probability"],
        },
        model_path,
    )

    optimizer = MaintenanceOptimizer(model_path=model_path)
    predicted_failure_date = datetime.now(timezone.utc) + timedelta(days=30)

    result = optimizer.recommend(
        dict(mock_charger_metrics),
        {
            "failure_probability": 0.1,
            "predicted_failure_date": predicted_failure_date,
        },
    )

    assert result["urgency"] == "HIGH"

"""
Unit tests for ML models.
"""
import builtins
import runpy
from datetime import datetime, timedelta, timezone
from pathlib import Path

import joblib
import numpy as np
import pytest

from src.ml.models import FailurePredictor, AnomalyDetector, MaintenanceOptimizer
from src.ml.models import failure_predictor as failure_module
from src.ml.models import anomaly_detector as anomaly_module
from src.ml.models import maintenance_optimizer as maintenance_module
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


class DummyNoScoreModel:
    pass


class DummyNumericModel:
    def __init__(self, value: float) -> None:
        self.value = float(value)

    def predict(self, X: np.ndarray) -> np.ndarray:
        return np.array([self.value for _ in range(len(X))], dtype=float)


class DummyPredictErrorModel:
    def predict(self, X: np.ndarray) -> np.ndarray:
        raise RuntimeError("predict failed")


def _run_joblib_import_error(monkeypatch, module):
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name.startswith("joblib"):
            raise ImportError("no joblib")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    module_globals = runpy.run_path(Path(module.__file__))

    assert module_globals["JOBLIB_AVAILABLE"] is False


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


def test_failure_predictor_joblib_import_error_branch(monkeypatch):
    _run_joblib_import_error(monkeypatch, failure_module)


def test_failure_predictor_load_exception_fallback(tmp_path, monkeypatch):
    model_path = tmp_path / "failure_model.joblib"
    model_path.write_bytes(b"invalid")

    def raise_error(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(failure_module.joblib, "load", raise_error)

    predictor = failure_module.FailurePredictor(model_path=model_path)
    assert isinstance(predictor.model, failure_module._RuleBasedFailureModel)


def test_failure_predictor_recommend_actions_temperature_and_maintenance():
    now = datetime.now(timezone.utc)
    metrics = {
        "connector_status": "AVAILABLE",
        "temperature": 45.0,
        "error_codes": [],
        "last_maintenance": now - timedelta(days=100),
        "total_sessions": 10,
    }

    actions = FailurePredictor._recommend_actions(0.3, metrics)

    assert any("Monitor temperature trend" in action for action in actions)
    assert any("Plan routine maintenance" in action for action in actions)


def test_anomaly_detector_joblib_import_error_branch(monkeypatch):
    _run_joblib_import_error(monkeypatch, anomaly_module)


def test_rule_based_anomaly_model_scoring_branches():
    model = anomaly_module._RuleBasedAnomalyModel()
    X = np.array(
        [
            [5.0, 0.0, -1.0, 65.0, 2.0],
            [0.0, 0.0, 1.0, 55.0, 0.0],
        ],
        dtype=float,
    )

    scores = model.score_samples(X)
    assert scores.shape == (2,)


def test_anomaly_detector_loads_non_bundle_object(tmp_path, mock_charger_metrics):
    model_path = tmp_path / "anomaly_model.joblib"
    joblib.dump(DummyNoScoreModel(), model_path)

    detector = AnomalyDetector(model_path=model_path)
    result = detector.detect(dict(mock_charger_metrics))

    assert isinstance(detector.model, DummyNoScoreModel)
    assert 0.0 <= result["anomaly_score"] <= 100.0


def test_anomaly_detector_load_exception_fallback(tmp_path, monkeypatch):
    model_path = tmp_path / "anomaly_model.joblib"
    model_path.write_bytes(b"invalid")

    def raise_error(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(anomaly_module.joblib, "load", raise_error)

    detector = anomaly_module.AnomalyDetector(model_path=model_path)
    assert isinstance(detector.model, anomaly_module._RuleBasedAnomalyModel)


def test_anomaly_detector_normalize_score_raw_range(tmp_path):
    detector = AnomalyDetector(model_path=tmp_path / "missing.joblib")
    detector.raw_min = 5.0
    detector.raw_max = 5.0

    score = detector._normalize_score(2.0)
    assert 0.0 <= score <= 100.0


@pytest.mark.parametrize(
    "metrics, score, expected",
    [
        ({"connector_status": "FAULTY", "temperature": 20.0, "error_codes": [], "power": 1.0}, 10.0, "STATUS_FAULT"),
        ({"connector_status": "AVAILABLE", "temperature": 55.0, "error_codes": [], "power": 1.0}, 10.0, "OVER_TEMPERATURE"),
        ({"connector_status": "AVAILABLE", "temperature": 20.0, "error_codes": ["E1"], "power": 1.0}, 10.0, "ERROR_CODE_PRESENT"),
        ({"connector_status": "CHARGING", "temperature": 20.0, "error_codes": [], "power": 0.0}, 10.0, "POWER_DROP_DURING_CHARGING"),
        ({"connector_status": "AVAILABLE", "temperature": 20.0, "error_codes": [], "power": 1.0}, 85.0, "GENERIC_OUTLIER_HIGH"),
    ],
)
def test_anomaly_detector_classify_branches(metrics, score, expected):
    assert anomaly_module.AnomalyDetector._classify(metrics, score) == expected


def test_maintenance_optimizer_joblib_import_error_branch(monkeypatch):
    _run_joblib_import_error(monkeypatch, maintenance_module)


def test_maintenance_optimizer_loads_non_bundle_object(tmp_path):
    model_path = tmp_path / "maintenance_model.joblib"
    joblib.dump(DummyMaintenanceModel(label="LOW"), model_path)

    optimizer = MaintenanceOptimizer(model_path=model_path)
    assert isinstance(optimizer.model, DummyMaintenanceModel)


def test_maintenance_optimizer_load_exception_resets(tmp_path, monkeypatch):
    model_path = tmp_path / "maintenance_model.joblib"
    model_path.write_bytes(b"invalid")

    def raise_error(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(maintenance_module.joblib, "load", raise_error)

    optimizer = maintenance_module.MaintenanceOptimizer(model_path=model_path)
    assert optimizer.model is None
    assert optimizer.feature_order == []


def test_maintenance_optimizer_urgency_branches(tmp_path):
    optimizer = MaintenanceOptimizer(model_path=tmp_path / "missing.joblib")

    assert optimizer._urgency(0.7, "AVAILABLE") == "HIGH"
    assert optimizer._urgency(0.5, "AVAILABLE") == "MEDIUM"
    assert optimizer._urgency(0.2, "AVAILABLE") == "LOW"


def test_maintenance_optimizer_predict_urgency_numeric_branches(tmp_path):
    optimizer = MaintenanceOptimizer(model_path=tmp_path / "missing.joblib")
    metrics = {"connector_status": "AVAILABLE"}

    optimizer.model = DummyNumericModel(2)
    assert optimizer._predict_urgency(metrics, 0.2) == "HIGH"

    optimizer.model = DummyNumericModel(99)
    assert optimizer._predict_urgency(metrics, 0.2) == "LOW"


def test_maintenance_optimizer_predict_urgency_exception_fallback(tmp_path):
    optimizer = MaintenanceOptimizer(model_path=tmp_path / "missing.joblib")
    optimizer.model = DummyPredictErrorModel()

    result = optimizer._predict_urgency({"connector_status": "AVAILABLE"}, 0.9)
    assert result == "CRITICAL"


def test_maintenance_optimizer_estimate_downtime_branches(tmp_path):
    optimizer = MaintenanceOptimizer(model_path=tmp_path / "missing.joblib")

    metrics = {
        "error_codes": ["E1"],
        "temperature": 55.0,
        "total_sessions": 600,
        "connector_status": "FAULTY",
    }
    downtime = optimizer._estimate_downtime_hours(metrics, 0.9)
    assert downtime >= 2.0

    metrics = {
        "error_codes": [],
        "temperature": 45.0,
        "total_sessions": 0,
        "connector_status": "AVAILABLE",
    }
    downtime = optimizer._estimate_downtime_hours(metrics, 0.2)
    assert downtime >= 2.0


def test_maintenance_optimizer_pick_datetime_urgent_before_two_am(tmp_path, monkeypatch):
    optimizer = MaintenanceOptimizer(model_path=tmp_path / "missing.joblib")
    fixed_now = datetime(2026, 1, 1, 1, 0, tzinfo=timezone.utc)

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now if tz else fixed_now.replace(tzinfo=None)

    monkeypatch.setattr(maintenance_module, "datetime", FixedDateTime)

    predicted_failure_date = fixed_now + timedelta(days=1)
    candidate = optimizer._pick_maintenance_datetime(predicted_failure_date, "HIGH")

    assert candidate.hour == 2


def test_maintenance_optimizer_pick_datetime_after_failure(tmp_path, monkeypatch):
    optimizer = MaintenanceOptimizer(model_path=tmp_path / "missing.joblib")
    fixed_now = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now if tz else fixed_now.replace(tzinfo=None)

    monkeypatch.setattr(maintenance_module, "datetime", FixedDateTime)

    predicted_failure_date = fixed_now + timedelta(minutes=30)
    candidate = optimizer._pick_maintenance_datetime(predicted_failure_date, "LOW")

    assert candidate == fixed_now + timedelta(hours=1)


def test_maintenance_optimizer_recommend_rationale_entries(tmp_path):
    optimizer = MaintenanceOptimizer(model_path=tmp_path / "missing.joblib")
    now = datetime.now(timezone.utc)
    metrics = {
        "charger_id": "c1",
        "connector_status": "AVAILABLE",
        "temperature": 45.0,
        "error_codes": ["E1"],
        "last_maintenance": now - timedelta(days=5),
    }
    failure_prediction = {
        "failure_probability": 0.4,
        "predicted_failure_date": now + timedelta(days=10),
    }

    result = optimizer.recommend(metrics, failure_prediction)

    rationale = result["rationale"]
    assert any(entry.startswith("Error codes present:") for entry in rationale)
    assert any(entry.startswith("Elevated temperature:") for entry in rationale)
    assert any(entry.startswith("Last maintenance:") for entry in rationale)

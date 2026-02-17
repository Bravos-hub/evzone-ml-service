"""
Unit tests for training helpers.
"""
import numpy as np
import pandas as pd

from src.ml.training import train_failure_model
from src.ml.training import train_anomaly_model
from src.ml.training import train_maintenance_model
from src.ml.preprocessing.feature_engineering import FEATURE_ORDER


def test_parse_error_codes_failure_model():
    assert train_failure_model.parse_error_codes(None) == []
    assert train_failure_model.parse_error_codes([]) == []
    assert train_failure_model.parse_error_codes("[]") == []
    assert train_failure_model.parse_error_codes("  ") == []
    assert train_failure_model.parse_error_codes('["E1", "E2"]') == ["E1", "E2"]
    assert train_failure_model.parse_error_codes("not-a-list") == []


def test_build_features_failure_model():
    df = pd.DataFrame(
        [
            {
                "connector_status": "AVAILABLE",
                "energy_delivered": 10.0,
                "power": 5.0,
                "temperature": 25.0,
                "error_codes": ["E1"],
                "uptime_hours": 100.0,
                "total_sessions": 10,
                "last_maintenance": "2026-01-01T00:00:00Z",
                "failure_within_30d_label": 0,
            },
            {
                "connector_status": "FAULTY",
                "energy_delivered": 20.0,
                "power": 0.0,
                "temperature": 55.0,
                "error_codes": "[]",
                "uptime_hours": 200.0,
                "total_sessions": 20,
                "last_maintenance": "2025-10-01T00:00:00Z",
                "failure_within_30d_label": 1,
            },
            {
                "connector_status": "AVAILABLE",
                "energy_delivered": 30.0,
                "power": 4.0,
                "temperature": 30.0,
                "error_codes": [],
                "uptime_hours": 300.0,
                "total_sessions": 30,
                "last_maintenance": "bad-date",
                "failure_within_30d_label": 0,
            },
        ]
    )
    X, y = train_failure_model.build_features(df)
    assert X.shape == (3, len(FEATURE_ORDER))
    assert y.tolist() == [0, 1, 0]


def test_parse_error_codes_anomaly_model():
    assert train_anomaly_model.parse_error_codes(None) == []
    assert train_anomaly_model.parse_error_codes(["E1"]) == ["E1"]
    assert train_anomaly_model.parse_error_codes('["E1"]') == ["E1"]
    assert train_anomaly_model.parse_error_codes("  ") == []
    assert train_anomaly_model.parse_error_codes("bad") == []


def test_build_x_anomaly_model():
    df = pd.DataFrame(
        [
            {
                "connector_status": "AVAILABLE",
                "energy_delivered": 5.0,
                "power": 2.0,
                "temperature": 20.0,
                "error_codes": [],
            }
        ]
    )
    X = train_anomaly_model.build_X(df)
    assert X.shape == (1, 5)


def test_parse_error_codes_maintenance_model():
    assert train_maintenance_model.parse_error_codes(None) == []
    assert train_maintenance_model.parse_error_codes(["E2"]) == ["E2"]
    assert train_maintenance_model.parse_error_codes('["E2"]') == ["E2"]
    assert train_maintenance_model.parse_error_codes("  ") == []
    assert train_maintenance_model.parse_error_codes("bad") == []


def test_maintenance_label_helpers():
    assert train_maintenance_model._coerce_label(2) == "HIGH"
    assert train_maintenance_model._coerce_label("low") == "LOW"
    assert train_maintenance_model._coerce_label(np.nan) is None
    assert train_maintenance_model._coerce_label(99) is None
    assert train_maintenance_model._coerce_label("unknown") is None
    assert train_maintenance_model._pick_label_column(pd.DataFrame({"urgency": ["LOW"]})) == "urgency"


def test_maintenance_derive_urgency_branches():
    assert train_maintenance_model.derive_urgency(0.9, "available") == "CRITICAL"
    assert train_maintenance_model.derive_urgency(0.7, "available") == "HIGH"
    assert train_maintenance_model.derive_urgency(0.5, "available") == "MEDIUM"
    assert train_maintenance_model.derive_urgency(0.1, "available") == "LOW"


def test_failure_prob_from_row():
    row = pd.Series({"failure_prob": 0.4})
    assert train_maintenance_model._failure_prob_from_row(row) == 0.4

    row = pd.Series({"failure_within_30d_label": 1})
    assert train_maintenance_model._failure_prob_from_row(row) == 1.0

    row = pd.Series({"failure_probability": "bad", "failure_prob": 0.25})
    assert train_maintenance_model._failure_prob_from_row(row) == 0.25

    row = pd.Series({"failure_within_30d_label": "bad"})
    assert train_maintenance_model._failure_prob_from_row(row) == 0.0

    row = pd.Series({"other": 1})
    assert train_maintenance_model._failure_prob_from_row(row) == 0.0


def test_build_features_and_labels_maintenance_model():
    df = pd.DataFrame(
        [
            {
                "connector_status": "AVAILABLE",
                "energy_delivered": 10.0,
                "power": 2.0,
                "temperature": 25.0,
                "error_codes": [],
                "uptime_hours": 100.0,
                "total_sessions": 10,
                "last_maintenance": "2026-01-01T00:00:00Z",
                "failure_probability": 0.2,
            }
        ]
    )
    X, y = train_maintenance_model.build_features_and_labels(df)
    assert X.shape == (1, len(FEATURE_ORDER) + 1)
    assert y.tolist() == ["LOW"]

    df = pd.DataFrame(
        [
            {
                "connector_status": "AVAILABLE",
                "energy_delivered": 10.0,
                "power": 2.0,
                "temperature": 25.0,
                "error_codes": [],
                "uptime_hours": 100.0,
                "total_sessions": 10,
                "last_maintenance": "bad-date",
                "failure_probability": 0.2,
            }
        ]
    )
    X, y = train_maintenance_model.build_features_and_labels(df)
    assert X.shape == (1, len(FEATURE_ORDER) + 1)
    assert y.tolist() == ["LOW"]


def test_evaluate_model_returns_metrics():
    from src.ml.training import model_evaluator
    from sklearn.ensemble import RandomForestClassifier
    import numpy as np

    # Create a simple dataset
    X = np.array([[1, 2], [1, 2], [10, 20], [10, 20]])
    y = np.array([0, 0, 1, 1])

    # Train a simple model
    model = RandomForestClassifier(n_estimators=10, random_state=42)
    model.fit(X, y)

    # Evaluate
    metrics = model_evaluator.evaluate_model(model, X, y)

    assert "accuracy" in metrics
    assert "precision" in metrics
    assert "recall" in metrics
    assert "f1_score" in metrics

    # For this simple dataset, it should be perfectly accurate
    assert metrics["accuracy"] == 1.0
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1_score"] == 1.0

    # Verify they are floats
    assert isinstance(metrics["accuracy"], float)

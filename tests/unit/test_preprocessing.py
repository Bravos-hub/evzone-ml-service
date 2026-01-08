"""
Unit tests for preprocessing utilities.
"""
from datetime import datetime, timezone

from src.ml.preprocessing import data_validation
from src.ml.preprocessing import feature_engineering


def test_validate_charger_metrics_missing_fields():
    ok, errors = data_validation.validate_charger_metrics({"charger_id": "c1"})
    assert ok is False
    assert "Missing required field: connector_status" in errors
    assert "Missing required field: energy_delivered" in errors


def test_validate_charger_metrics_invalid_energy():
    ok, errors = data_validation.validate_charger_metrics(
        {"charger_id": "c1", "connector_status": "AVAILABLE", "energy_delivered": "bad"}
    )
    assert ok is False
    assert "energy_delivered must be numeric" in errors


def test_validate_charger_metrics_negative_energy():
    ok, errors = data_validation.validate_charger_metrics(
        {"charger_id": "c1", "connector_status": "AVAILABLE", "energy_delivered": -1.0}
    )
    assert ok is False
    assert "energy_delivered must be non-negative" in errors


def test_validate_charger_metrics_valid():
    ok, errors = data_validation.validate_charger_metrics(
        {"charger_id": "c1", "connector_status": "AVAILABLE", "energy_delivered": 1.0}
    )
    assert ok is True
    assert errors == []


def test_days_since_invalid_string_returns_default():
    assert feature_engineering.days_since("not-a-date") == 9999.0


def test_days_since_naive_datetime():
    naive = datetime.utcnow().replace(microsecond=0)
    value = feature_engineering.days_since(naive)
    assert value >= 0.0


def test_days_since_none():
    assert feature_engineering.days_since(None) == 9999.0

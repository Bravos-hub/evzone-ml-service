"""
Unit tests for SQLAlchemy models.
"""
from src.database.models import ChargerMetrics, Prediction, ModelMetadata


def test_charger_metrics_columns():
    cols = set(ChargerMetrics.__table__.columns.keys())
    assert cols == {
        "id",
        "charger_id",
        "timestamp",
        "connector_status",
        "energy_delivered",
        "power",
        "temperature",
        "error_codes",
        "uptime_hours",
        "total_sessions",
        "raw_data",
        "created_at",
    }


def test_prediction_columns():
    cols = set(Prediction.__table__.columns.keys())
    assert cols == {
        "id",
        "charger_id",
        "model_type",
        "model_version",
        "prediction_data",
        "confidence",
        "predicted_at",
        "created_at",
    }


def test_model_metadata_columns():
    cols = set(ModelMetadata.__table__.columns.keys())
    assert cols == {
        "id",
        "name",
        "version",
        "type",
        "accuracy",
        "path",
        "metadata",
        "status",
        "loaded_at",
        "created_at",
        "updated_at",
    }

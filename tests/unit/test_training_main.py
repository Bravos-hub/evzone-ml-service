"""
Unit tests for training script main entrypoints.
"""
from pathlib import Path as RealPath

import pandas as pd
import pytest
from sklearn.ensemble import IsolationForest as SkIsolationForest
from sklearn.ensemble import RandomForestClassifier as SkRandomForestClassifier

from src.ml.training import train_failure_model
from src.ml.training import train_anomaly_model
from src.ml.training import train_maintenance_model


def _write_training_dataset(base_dir: RealPath, rows: int = 10) -> None:
    data_dir = base_dir / "src/ml/data/datasets"
    data_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for i in range(rows):
        records.append(
            {
                "connector_status": "AVAILABLE" if i % 2 == 0 else "FAULTY",
                "energy_delivered": 10.0 + i,
                "power": 5.0 if i % 2 == 0 else 0.2,
                "temperature": 25.0 + i,
                "error_codes": ["E1"] if i % 2 == 1 else [],
                "uptime_hours": 100.0 + i,
                "total_sessions": 10 + i,
                "last_maintenance": "2026-01-01T00:00:00Z",
                "failure_within_30d_label": 0 if i % 2 == 0 else 1,
                "urgency": "LOW" if i % 2 == 0 else "HIGH",
                "failure_probability": 0.2 if i % 2 == 0 else 0.9,
            }
        )
    pd.DataFrame(records).to_csv(data_dir / "training_dataset.csv", index=False)


def _write_anomaly_dataset(base_dir: RealPath, rows: int = 20) -> None:
    data_dir = base_dir / "src/ml/data/datasets"
    data_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for i in range(rows):
        records.append(
            {
                "connector_status": "AVAILABLE",
                "energy_delivered": 5.0 + i,
                "power": 2.0 + (i % 3),
                "temperature": 20.0 + i,
                "error_codes": [],
            }
        )
    pd.DataFrame(records).to_csv(data_dir / "synthetic_charger_metrics.csv", index=False)


def _patch_path(monkeypatch, module, base_dir: RealPath) -> None:
    monkeypatch.setattr(module, "Path", lambda p: base_dir / p)


def _small_rf(*args, **kwargs):
    kwargs["n_estimators"] = 5
    return SkRandomForestClassifier(**kwargs)


def _small_if(*args, **kwargs):
    kwargs["n_estimators"] = 10
    return SkIsolationForest(**kwargs)


def test_train_failure_model_main(tmp_path, monkeypatch):
    _write_training_dataset(tmp_path, rows=10)
    _patch_path(monkeypatch, train_failure_model, tmp_path)

    train_failure_model.main()

    out_path = tmp_path / "models/failure_model.joblib"
    assert out_path.exists()


def test_train_anomaly_model_main(tmp_path, monkeypatch):
    _write_anomaly_dataset(tmp_path, rows=20)
    _patch_path(monkeypatch, train_anomaly_model, tmp_path)
    monkeypatch.setattr(train_anomaly_model, "IsolationForest", _small_if)

    train_anomaly_model.main()

    out_path = tmp_path / "models/anomaly_model.joblib"
    assert out_path.exists()


def test_train_maintenance_model_main(tmp_path, monkeypatch):
    _write_training_dataset(tmp_path, rows=12)
    _patch_path(monkeypatch, train_maintenance_model, tmp_path)
    monkeypatch.setattr(train_maintenance_model, "RandomForestClassifier", _small_rf)

    train_maintenance_model.main()

    out_path = tmp_path / "models/maintenance_model.joblib"
    assert out_path.exists()


def test_train_failure_model_main_missing_dataset(tmp_path, monkeypatch):
    _patch_path(monkeypatch, train_failure_model, tmp_path)
    with pytest.raises(SystemExit):
        train_failure_model.main()


def test_train_anomaly_model_main_missing_dataset(tmp_path, monkeypatch):
    _patch_path(monkeypatch, train_anomaly_model, tmp_path)
    with pytest.raises(SystemExit):
        train_anomaly_model.main()


def test_train_maintenance_model_main_missing_dataset(tmp_path, monkeypatch):
    _patch_path(monkeypatch, train_maintenance_model, tmp_path)
    with pytest.raises(SystemExit):
        train_maintenance_model.main()

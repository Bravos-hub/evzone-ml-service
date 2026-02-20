"""
Training script for failure prediction model.
"""
import ast
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split

from src.ml.preprocessing.feature_engineering import FEATURE_ORDER, STATUS_TO_INT, days_since


def parse_error_codes(val) -> list[str]:
    if val is None:
        return []
    if isinstance(val, list):
        return val
    s = str(val)
    if not s.strip():
        return []
    try:
        parsed = ast.literal_eval(s)
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []


def build_features(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    from datetime import datetime, timezone

    y = df["failure_within_30d_label"].astype(int).values

    # Vectorized connector_status to status_int
    status_series = df["connector_status"].fillna("AVAILABLE").astype(str).str.upper()
    status_int = status_series.map(STATUS_TO_INT).fillna(0).astype(float)

    # Vectorized error_codes to error_count
    error_count = df["error_codes"].apply(parse_error_codes).apply(len).astype(float)

    # Vectorized last_maintenance to days_since_maintenance
    now = datetime.now(timezone.utc)
    lm_series = pd.to_datetime(df["last_maintenance"], errors="coerce", utc=True)
    days_since_maint = (now - lm_series).dt.total_seconds() / 86400.0
    days_since_maint = days_since_maint.fillna(9999.0).clip(lower=0.0).astype(float)

    # Combine into feature matrix following FEATURE_ORDER
    features_dict = {
        "status_int": status_int,
        "energy_delivered": df["energy_delivered"].fillna(0.0).astype(float),
        "power": df["power"].fillna(0.0).astype(float),
        "temperature": df["temperature"].fillna(0.0).astype(float),
        "error_count": error_count,
        "uptime_hours": df["uptime_hours"].fillna(0.0).astype(float),
        "total_sessions": df["total_sessions"].fillna(0.0).astype(float),
        "days_since_maintenance": days_since_maint,
    }

    # Create the feature matrix X
    X = np.column_stack([features_dict[k] for k in FEATURE_ORDER]).astype(float)

    return X, y


def main() -> None:
    data_path = Path("src/ml/data/datasets/training_dataset.csv")
    if not data_path.exists():
        raise SystemExit(f"Missing training dataset: {data_path}. Run scripts/generate_datasets.py first.")

    df = pd.read_csv(data_path)
    X, y = build_features(df)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42,
        stratify=y,
    )

    model = GradientBoostingClassifier(random_state=42)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    print(classification_report(y_test, y_pred))

    out_path = Path("models/failure_model.joblib")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, out_path)
    print(f"Saved model: {out_path}")


if __name__ == "__main__":
    main()

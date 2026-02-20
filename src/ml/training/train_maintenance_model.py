"""
Training script for maintenance scheduling model.
"""
import ast
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split

from src.ml.preprocessing.feature_engineering import FEATURE_ORDER, STATUS_TO_INT

LABEL_COLUMNS = [
    "maintenance_urgency_label",
    "maintenance_urgency",
    "urgency",
]


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


def derive_urgency(failure_prob: float, status: str) -> str:
    status = status.upper()
    if status in {"FAULTY", "OFFLINE", "UNAVAILABLE"} or failure_prob >= 0.85:
        return "CRITICAL"
    if failure_prob >= 0.60:
        return "HIGH"
    if failure_prob >= 0.40:
        return "MEDIUM"
    return "LOW"


def _pick_label_column(df: pd.DataFrame) -> str | None:
    for col in LABEL_COLUMNS:
        if col in df.columns:
            return col
    return None


def _coerce_label(value) -> str | None:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    if isinstance(value, (int, np.integer)):
        label_map = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        idx = int(value)
        if 0 <= idx < len(label_map):
            return label_map[idx]
        return None
    if isinstance(value, str):
        label = value.strip().upper()
        if label in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
            return label
    return None


def _failure_prob_from_row(r: pd.Series) -> float:
    for col in ["failure_probability_synth", "failure_probability", "failure_prob"]:
        if col in r and pd.notna(r[col]):
            try:
                return float(r[col])
            except Exception:
                continue
    if "failure_within_30d_label" in r and pd.notna(r["failure_within_30d_label"]):
        try:
            return float(r["failure_within_30d_label"])
        except Exception:
            return 0.0
    return 0.0


def build_features_and_labels(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    # 1. Vectorized status
    status_series = df.get("connector_status", pd.Series("AVAILABLE", index=df.index))
    status_series = status_series.fillna("AVAILABLE").astype(str).str.upper()
    status_int = status_series.map(STATUS_TO_INT).fillna(0).astype(float)

    # 2. Vectorized error codes
    error_codes_col = df.get("error_codes", pd.Series("[]", index=df.index))
    error_count = error_codes_col.apply(parse_error_codes).apply(len).astype(float)

    # 3. Vectorized maintenance days
    now = datetime.now(timezone.utc)
    lm_col = df.get("last_maintenance")
    if lm_col is not None:
        lm_series = pd.to_datetime(lm_col, errors="coerce", utc=True)
        days_since_maint = (now - lm_series).dt.total_seconds() / 86400.0
        days_since_maint = days_since_maint.fillna(9999.0).clip(lower=0.0)
    else:
        days_since_maint = pd.Series(9999.0, index=df.index)

    # 4. Helper for numeric
    def safe_numeric(col_name):
        series = df.get(col_name, pd.Series(0.0, index=df.index))
        return pd.to_numeric(series, errors="coerce").fillna(0.0).astype(float)

    # 5. Failure probability (vectorized logic from _failure_prob_from_row)
    failure_prob = pd.Series(0.0, index=df.index)
    for col in ["failure_probability_synth", "failure_probability", "failure_prob"]:
        if col in df.columns:
            col_vals = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
            failure_prob = failure_prob.where(failure_prob != 0.0, col_vals)

    if "failure_within_30d_label" in df.columns:
        label_vals = pd.to_numeric(df["failure_within_30d_label"], errors="coerce").fillna(0.0)
        failure_prob = failure_prob.where(failure_prob != 0.0, label_vals)

    # 6. Labels (vectorized logic from _coerce_label and derive_urgency)
    label_col = _pick_label_column(df)
    if label_col:
        y_series = df[label_col].apply(_coerce_label)
    else:
        y_series = pd.Series([None] * len(df), index=df.index)

    # Fill missing labels with derived urgency
    missing_mask = y_series.isna()
    if missing_mask.any():
        # derive_urgency logic
        derived = pd.Series("LOW", index=df.index)
        prob_m = failure_prob
        derived.loc[prob_m >= 0.40] = "MEDIUM"
        derived.loc[prob_m >= 0.60] = "HIGH"
        critical_mask = (status_series.isin({"FAULTY", "OFFLINE", "UNAVAILABLE"})) | (
            prob_m >= 0.85
        )
        derived.loc[critical_mask] = "CRITICAL"
        y_series = y_series.fillna(derived)

    # 7. Combine features
    features_dict = {
        "status_int": status_int,
        "energy_delivered": safe_numeric("energy_delivered"),
        "power": safe_numeric("power"),
        "temperature": safe_numeric("temperature"),
        "error_count": error_count,
        "uptime_hours": safe_numeric("uptime_hours"),
        "total_sessions": safe_numeric("total_sessions"),
        "days_since_maintenance": days_since_maint.astype(float),
        "failure_probability": failure_prob.astype(float),
    }

    X = np.column_stack([features_dict[k] for k in FEATURE_ORDER + ["failure_probability"]])
    y = y_series.values

    return X, y


def main() -> None:
    data_path = Path("src/ml/data/datasets/training_dataset.csv")
    if not data_path.exists():
        raise SystemExit(f"Missing training dataset: {data_path}. Run scripts/generate_datasets.py first.")

    df = pd.read_csv(data_path)
    X, y = build_features_and_labels(df)

    unique, counts = np.unique(y, return_counts=True)
    stratify = y if len(unique) > 1 and counts.min() >= 2 else None

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42,
        stratify=stratify,
    )

    model = RandomForestClassifier(
        n_estimators=300,
        random_state=42,
        class_weight="balanced",
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    print(classification_report(y_test, y_pred))

    out_path = Path("models/maintenance_model.joblib")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": model,
            "feature_order": FEATURE_ORDER + ["failure_probability"],
        },
        out_path,
    )
    print(f"Saved maintenance model: {out_path}")


if __name__ == "__main__":
    main()

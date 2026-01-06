"""
Training script for maintenance scheduling model.
"""
import ast
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split

from src.ml.preprocessing.feature_engineering import FEATURE_ORDER, STATUS_TO_INT, days_since

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
    X_rows = []
    y_rows: list[str] = []

    label_col = _pick_label_column(df)

    for _, r in df.iterrows():
        status = str(r.get("connector_status", "AVAILABLE")).upper()
        error_codes = parse_error_codes(r.get("error_codes"))

        lm_raw = r.get("last_maintenance")
        lm = None
        if isinstance(lm_raw, str) and lm_raw:
            try:
                from datetime import datetime

                lm = datetime.fromisoformat(lm_raw.replace("Z", "+00:00"))
            except Exception:
                lm = None

        feats = {
            "status_int": float(STATUS_TO_INT.get(status, 0)),
            "energy_delivered": float(r.get("energy_delivered", 0.0) or 0.0),
            "power": float(r.get("power", 0.0) or 0.0),
            "temperature": float(r.get("temperature", 0.0) or 0.0),
            "error_count": float(len(error_codes)),
            "uptime_hours": float(r.get("uptime_hours", 0.0) or 0.0),
            "total_sessions": float(r.get("total_sessions", 0.0) or 0.0),
            "days_since_maintenance": float(days_since(lm)),
        }

        failure_prob = _failure_prob_from_row(r)
        feats["failure_probability"] = float(failure_prob)

        X_rows.append([feats[k] for k in FEATURE_ORDER + ["failure_probability"]])

        label = _coerce_label(r.get(label_col)) if label_col else None
        if label is None:
            label = derive_urgency(failure_prob, status)
        y_rows.append(label)

    X = np.array(X_rows, dtype=float)
    y = np.array(y_rows, dtype=object)
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

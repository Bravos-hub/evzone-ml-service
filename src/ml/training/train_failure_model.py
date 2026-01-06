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
    X_rows = []
    y = df["failure_within_30d_label"].astype(int).values

    for _, r in df.iterrows():
        status = str(r.get("connector_status", "AVAILABLE")).upper()
        status_int = float(STATUS_TO_INT.get(status, 0))
        error_codes = parse_error_codes(r.get("error_codes"))
        error_count = float(len(error_codes))

        lm_raw = r.get("last_maintenance")
        lm = None
        if isinstance(lm_raw, str) and lm_raw:
            try:
                from datetime import datetime

                lm = datetime.fromisoformat(lm_raw.replace("Z", "+00:00"))
            except Exception:
                lm = None

        feats = {
            "status_int": status_int,
            "energy_delivered": float(r.get("energy_delivered", 0.0) or 0.0),
            "power": float(r.get("power", 0.0) or 0.0),
            "temperature": float(r.get("temperature", 0.0) or 0.0),
            "error_count": error_count,
            "uptime_hours": float(r.get("uptime_hours", 0.0) or 0.0),
            "total_sessions": float(r.get("total_sessions", 0.0) or 0.0),
            "days_since_maintenance": float(days_since(lm)),
        }

        X_rows.append([feats[k] for k in FEATURE_ORDER])

    X = np.array(X_rows, dtype=float)
    y = np.array(y, dtype=int)
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

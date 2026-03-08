"""
Training script for anomaly detection model.
"""
import ast
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from src.ml.preprocessing.feature_engineering import STATUS_TO_INT


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


def build_X(df: pd.DataFrame) -> np.ndarray:
    # Vectorized connector_status to status_int
    status_series = df.get("connector_status", pd.Series("AVAILABLE", index=df.index))
    status_series = status_series.fillna("AVAILABLE").astype(str).str.upper()
    status_int = status_series.map(STATUS_TO_INT).fillna(0).astype(float)

    # Vectorized error_codes to error_count
    error_codes_col = df.get("error_codes", pd.Series("[]", index=df.index))
    error_count = error_codes_col.apply(parse_error_codes).apply(len).astype(float)

    def safe_numeric(col_name):
        series = df.get(col_name, pd.Series(0.0, index=df.index))
        return pd.to_numeric(series, errors="coerce").fillna(0.0).astype(float)

    X = np.column_stack(
        [
            status_int,
            safe_numeric("energy_delivered"),
            safe_numeric("power"),
            safe_numeric("temperature"),
            error_count,
        ]
    ).astype(float)
    return X


def main() -> None:
    data_path = Path("src/ml/data/datasets/synthetic_charger_metrics.csv")
    if not data_path.exists():
        raise SystemExit(f"Missing dataset: {data_path}. Run scripts/generate_datasets.py first.")

    df = pd.read_csv(data_path)

    # Vectorized filtering for normal rows
    status_series = df.get("connector_status", pd.Series("AVAILABLE", index=df.index))
    status_series = status_series.fillna("AVAILABLE").astype(str).str.upper()
    temp_series = pd.to_numeric(df.get("temperature"), errors="coerce").fillna(0.0)
    error_codes_col = df.get("error_codes", pd.Series("[]", index=df.index))
    error_count = error_codes_col.apply(parse_error_codes).apply(len)

    is_normal = (
        (~status_series.isin({"FAULTY", "OFFLINE", "UNAVAILABLE"}))
        & (temp_series < 50)
        & (error_count == 0)
    )
    normal_df = df[is_normal]
    if len(normal_df) < 100:
        normal_df = df.sample(n=min(500, len(df)), random_state=42)

    X_train = build_X(normal_df)

    model = IsolationForest(
        n_estimators=200,
        contamination=0.05,
        random_state=42,
    )
    model.fit(X_train)

    normality = model.score_samples(X_train)
    raw = -normality
    raw_min = float(np.quantile(raw, 0.05))
    raw_max = float(np.quantile(raw, 0.95))

    mean = X_train.mean(axis=0).tolist()
    std = X_train.std(axis=0).tolist()

    bundle = {
        "model": model,
        "raw_min": raw_min,
        "raw_max": raw_max,
        "mean": mean,
        "std": std,
    }

    out_path = Path("models/anomaly_model.joblib")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, out_path)
    print(f"Saved anomaly model bundle: {out_path}")
    print(f"raw_min={raw_min:.4f}, raw_max={raw_max:.4f}")


if __name__ == "__main__":
    main()

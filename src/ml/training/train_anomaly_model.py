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
    rows = []
    for _, r in df.iterrows():
        status = str(r.get("connector_status", "AVAILABLE")).upper()
        status_int = float(STATUS_TO_INT.get(status, 0))
        err_cnt = float(len(parse_error_codes(r.get("error_codes"))))
        rows.append(
            [
                status_int,
                float(r.get("energy_delivered", 0.0) or 0.0),
                float(r.get("power", 0.0) or 0.0),
                float(r.get("temperature", 0.0) or 0.0),
                err_cnt,
            ]
        )
    return np.array(rows, dtype=float)


def main() -> None:
    data_path = Path("src/ml/data/datasets/synthetic_charger_metrics.csv")
    if not data_path.exists():
        raise SystemExit(f"Missing dataset: {data_path}. Run scripts/generate_datasets.py first.")

    df = pd.read_csv(data_path)

    def is_normal_row(r) -> bool:
        status = str(r.get("connector_status", "AVAILABLE")).upper()
        temp = float(r.get("temperature", 0.0) or 0.0)
        errs = parse_error_codes(r.get("error_codes"))
        if status in {"FAULTY", "OFFLINE", "UNAVAILABLE"}:
            return False
        if temp >= 50:
            return False
        if len(errs) > 0:
            return False
        return True

    normal_df = df[df.apply(is_normal_row, axis=1)]
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

#!/usr/bin/env python3
"""Model evaluation script."""
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score, roc_curve
from src.ml.training.train_failure_model import build_features
from src.ml.training.train_anomaly_model import build_X

print("=" * 60)
print("EVzone ML Service - Model Evaluation")
print("=" * 60)

# Load test data
train_df = pd.read_csv("src/ml/data/datasets/training_dataset.csv")
test_df = train_df.sample(n=500, random_state=99)

# Evaluate Failure Predictor
print("\n[1/2] Evaluating Failure Predictor...")
failure_model = joblib.load("models/failure_model.joblib")
X_test, y_test = build_features(test_df)
y_pred = failure_model.predict(X_test)
y_proba = failure_model.predict_proba(X_test)[:, 1]

print("\nClassification Report:")
print(classification_report(y_test, y_pred, target_names=["Normal", "Failure"]))

print("\nConfusion Matrix:")
cm = confusion_matrix(y_test, y_pred)
print(f"  TN: {cm[0,0]:4d}  FP: {cm[0,1]:4d}")
print(f"  FN: {cm[1,0]:4d}  TP: {cm[1,1]:4d}")

auc = roc_auc_score(y_test, y_proba)
print(f"\nROC AUC Score: {auc:.4f}")

# Feature importance
if hasattr(failure_model, 'feature_importances_'):
    from src.ml.preprocessing.feature_engineering import FEATURE_ORDER
    importances = failure_model.feature_importances_
    print("\nFeature Importances:")
    for feat, imp in sorted(zip(FEATURE_ORDER, importances), key=lambda x: x[1], reverse=True):
        print(f"  {feat:25s}: {imp:.4f}")

# Evaluate Anomaly Detector
print("\n[2/3] Evaluating Anomaly Detector...")
anomaly_bundle = joblib.load("models/anomaly_model.joblib")
anomaly_model = anomaly_bundle["model"]
raw_min = anomaly_bundle["raw_min"]
raw_max = anomaly_bundle["raw_max"]

metrics_df = pd.read_csv("src/ml/data/datasets/synthetic_charger_metrics.csv")
X_all = build_X(metrics_df.sample(n=500, random_state=88))

predictions = anomaly_model.predict(X_all)
scores = anomaly_model.score_samples(X_all)
raw_scores = -scores
normalized = 100 * np.clip((raw_scores - raw_min) / (raw_max - raw_min), 0, 1)

anomalies = predictions == -1
print(f"\nDetected Anomalies: {anomalies.sum()} / {len(X_all)} ({100*anomalies.mean():.1f}%)")
print(f"Anomaly Score Range: {normalized.min():.1f} - {normalized.max():.1f}")
print(f"Mean Score: {normalized.mean():.1f}")
print(f"Median Score: {np.median(normalized):.1f}")

# Evaluate Maintenance Optimizer
print("\n[3/3] Evaluating Maintenance Optimizer...")
from src.ml.models.maintenance_optimizer import MaintenanceOptimizer
from src.ml.models.failure_predictor import FailurePredictor

maint_optimizer = MaintenanceOptimizer()
failure_predictor = FailurePredictor()

# Test with sample data
test_sample = test_df.sample(n=50, random_state=42)
urgency_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
downtime_hours = []
cost_savings = []

for _, row in test_sample.iterrows():
    metrics = {
        "connector_status": row["connector_status"],
        "energy_delivered": float(row["energy_delivered"]),
        "power": float(row["power"]),
        "temperature": float(row["temperature"]),
        "error_codes": eval(str(row["error_codes"])) if pd.notna(row["error_codes"]) else [],
        "uptime_hours": float(row["uptime_hours"]),
        "total_sessions": int(row["total_sessions"]),
        "last_maintenance": row["last_maintenance"]
    }
    
    failure_result = failure_predictor.predict(metrics)
    maint_result = maint_optimizer.recommend(metrics, failure_result)
    
    urgency_counts[maint_result["urgency"]] += 1
    downtime_hours.append(maint_result["estimated_downtime_hours"])
    if "cost_benefit" in maint_result and "net_savings" in maint_result["cost_benefit"]:
        cost_savings.append(maint_result["cost_benefit"]["net_savings"])

print(f"\nUrgency Distribution:")
for urgency, count in urgency_counts.items():
    print(f"  {urgency:8s}: {count:2d} ({100*count/50:.1f}%)")

print(f"\nDowntime Analysis:")
print(f"  Mean: {np.mean(downtime_hours):.1f} hours")
print(f"  Median: {np.median(downtime_hours):.1f} hours")
print(f"  Range: {min(downtime_hours):.1f} - {max(downtime_hours):.1f} hours")

if cost_savings:
    print(f"\nCost Savings Analysis:")
    print(f"  Mean: ${np.mean(cost_savings):.0f}")
    print(f"  Median: ${np.median(cost_savings):.0f}")
    print(f"  Total: ${sum(cost_savings):.0f}")

print("\n" + "=" * 60)
print("✓ All 3 models evaluated!")
print("=" * 60)

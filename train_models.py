#!/usr/bin/env python3
"""Complete model training pipeline."""
from pathlib import Path

print("=" * 60)
print("EVzone ML Service - Model Training Pipeline")
print("=" * 60)

# Step 1: Generate synthetic datasets
print("\n[1/3] Generating synthetic datasets...")
from src.ml.data.synthetic_generator import save_datasets

data_dir = Path("src/ml/data/datasets")
datasets = save_datasets(data_dir)
print(f"✓ Generated {len(datasets)} datasets:")
for name, path in datasets.items():
    print(f"  - {name}: {path}")

# Step 2: Train failure prediction model
print("\n[2/3] Training failure prediction model...")
from src.ml.training.train_failure_model import main as train_failure
train_failure()

# Step 3: Train anomaly detection model
print("\n[3/3] Training anomaly detection model...")
from src.ml.training.train_anomaly_model import main as train_anomaly
train_anomaly()

print("\n" + "=" * 60)
print("✓ Training complete! Models saved to ./models/")
print("=" * 60)
print("\nNext steps:")
print("  1. Restart the ML service to load new models")
print("  2. Test predictions: python3 test_endpoints.py")
print("  3. Check model versions: curl http://localhost:8000/api/v1/models")

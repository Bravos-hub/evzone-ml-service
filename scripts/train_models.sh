#!/bin/bash
# Training script for ML models

set -e

echo "Starting model training..."

# Train failure prediction model
echo "Training failure prediction model..."
python -m src.ml.training.train_failure_model

# Train maintenance scheduling model
echo "Training maintenance scheduling model..."
python -m src.ml.training.train_maintenance_model

echo "Model training completed!"


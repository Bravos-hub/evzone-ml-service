"""
Model evaluation utilities.
"""
import logging
from typing import Dict, Any
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

logger = logging.getLogger(__name__)


def evaluate_model(model, test_data, test_labels) -> Dict[str, Any]:
    """
    Evaluate model performance.
    
    Args:
        model: Trained model
        test_data: Test features
        test_labels: Test labels
        
    Returns:
        Evaluation metrics dictionary
    """
    logger.info("Evaluating model performance...")
    
    # Generate predictions
    y_pred = model.predict(test_data)

    # Calculate metrics
    # Using 'weighted' average to handle both binary and multi-class classification
    # as it accounts for label imbalance.
    metrics = {
        "accuracy": float(accuracy_score(test_labels, y_pred)),
        "precision": float(precision_score(test_labels, y_pred, average='weighted', zero_division=0)),
        "recall": float(recall_score(test_labels, y_pred, average='weighted', zero_division=0)),
        "f1_score": float(f1_score(test_labels, y_pred, average='weighted', zero_division=0)),
    }

    logger.info(f"Evaluation results: {metrics}")

    return metrics

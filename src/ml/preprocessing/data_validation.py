"""
Data validation utilities.
"""
from typing import Dict, Any, List


def validate_charger_metrics(metrics: Dict[str, Any]) -> tuple[bool, List[str]]:
    """
    Validate charger metrics.
    
    Args:
        metrics: Charger metrics dictionary
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    required_fields = ["charger_id", "connector_status", "energy_delivered"]
    
    for field in required_fields:
        if field not in metrics:
            errors.append(f"Missing required field: {field}")
    
    # Validate data types and ranges
    if "energy_delivered" in metrics:
        if not isinstance(metrics["energy_delivered"], (int, float)):
            errors.append("energy_delivered must be numeric")
        elif metrics["energy_delivered"] < 0:
            errors.append("energy_delivered must be non-negative")
    
    return len(errors) == 0, errors


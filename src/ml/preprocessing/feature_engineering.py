"""Feature engineering for charger metrics."""
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

STATUS_TO_INT = {
    "AVAILABLE": 0,
    "CHARGING": 1,
    "OCCUPIED": 2,
    "FULLY_CHARGED": 3,
    "UNAVAILABLE": 4,
    "OFFLINE": 5,
    "FAULTY": 6,
}


def safe_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


def days_since(dt: Optional[datetime]) -> float:
    """Calculate days since a given datetime."""
    if dt is None:
        return 9999.0
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except ValueError:
            return 9999.0
    now = safe_now()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return max((now - dt).total_seconds() / 86400.0, 0.0)


def extract_features(metrics: Dict[str, Any]) -> Dict[str, float]:
    """Convert charger metrics into numeric features."""
    status_int = float(STATUS_TO_INT.get(metrics.get("connector_status", ""), 0))
    error_count = float(len(metrics.get("error_codes", [])))
    last_maint_days = days_since(metrics.get("last_maintenance"))
    
    return {
        "status_int": status_int,
        "energy_delivered": float(metrics.get("energy_delivered", 0.0)),
        "power": float(metrics.get("power", 0.0)),
        "temperature": float(metrics.get("temperature", 0.0)),
        "error_count": error_count,
        "uptime_hours": float(metrics.get("uptime_hours", 0.0)),
        "total_sessions": float(metrics.get("total_sessions", 0.0)),
        "days_since_maintenance": float(last_maint_days),
    }


FEATURE_ORDER: List[str] = [
    "status_int",
    "energy_delivered",
    "power",
    "temperature",
    "error_count",
    "uptime_hours",
    "total_sessions",
    "days_since_maintenance",
]


def features_to_vector(features: Dict[str, float]) -> List[float]:
    """Convert feature dict to ordered vector."""
    return [float(features.get(k, 0.0)) for k in FEATURE_ORDER]

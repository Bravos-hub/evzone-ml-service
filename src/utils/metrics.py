"""
Prometheus metrics for monitoring.
"""
from prometheus_client import Counter, Histogram, Gauge

# Prediction metrics
prediction_requests = Counter(
    "ml_predictions_total",
    "Total number of prediction requests",
    ["model_type", "status"]
)

prediction_duration = Histogram(
    "ml_prediction_duration_seconds",
    "Time spent on predictions",
    ["model_type"]
)

model_load_time = Histogram(
    "ml_model_load_time_seconds",
    "Time spent loading models",
    ["model_type"]
)

active_models = Gauge(
    "ml_active_models",
    "Number of active loaded models",
    ["model_type"]
)

cache_hits = Counter(
    "ml_cache_hits_total",
    "Number of cache hits",
    ["model_type"]
)

cache_misses = Counter(
    "ml_cache_misses_total",
    "Number of cache misses",
    ["model_type"]
)


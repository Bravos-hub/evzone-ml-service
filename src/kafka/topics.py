"""
Kafka topic definitions.
"""
from src.config.settings import settings

# Input topics (consume from)
CHARGER_METRICS_TOPIC = settings.kafka_topic_charger_metrics

# Output topics (publish to)
PREDICTIONS_TOPIC = settings.kafka_topic_predictions
ANOMALIES_TOPIC = settings.kafka_topic_anomalies
FAILURE_ALERTS_TOPIC = settings.kafka_topic_failure_alerts

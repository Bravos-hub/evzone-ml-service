"""
Kafka consumer for charger metrics.
"""
import json
import logging
from confluent_kafka import Consumer, KafkaError
from src.config.settings import settings
from src.kafka.topics import CHARGER_METRICS_TOPIC, ANOMALIES_TOPIC, FAILURE_ALERTS_TOPIC
from src.kafka.producer import KafkaProducer
from src.services.data_collector import DataCollector
from src.services.prediction_service import PredictionService

logger = logging.getLogger(__name__)


class KafkaConsumer:
    """Kafka consumer for processing charger metrics."""
    
    def __init__(
        self,
        data_collector: DataCollector,
        prediction_service: PredictionService,
        producer: KafkaProducer = None,
    ):
        self.data_collector = data_collector
        self.prediction_service = prediction_service
        self.producer = producer or KafkaProducer()
        self.consumer: Consumer = None
        self.running = False
    
    async def start(self):
        """Start Kafka consumer."""
        try:
            await self.producer.start()
            self.consumer = Consumer({
                'bootstrap.servers': settings.kafka_brokers,
                'group.id': settings.kafka_group_id,
                'auto.offset.reset': 'latest',
                'enable.auto.commit': True,
            })
            
            self.consumer.subscribe([CHARGER_METRICS_TOPIC])
            self.running = True
            
            logger.info(f"Kafka consumer started, subscribed to {CHARGER_METRICS_TOPIC}")
            
            # Start consuming in background
            await self._consume_loop()
            
        except Exception as e:
            logger.error(f"Failed to start Kafka consumer: {e}")
            raise
    
    async def _consume_loop(self):
        """Main consumption loop."""
        while self.running:
            try:
                msg = self.consumer.poll(timeout=1.0)
                
                if msg is None:
                    continue
                
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        logger.error(f"Consumer error: {msg.error()}")
                        continue
                
                # Process message
                await self._process_message(msg.value().decode('utf-8'))
                
            except Exception as e:
                logger.error(f"Error in consume loop: {e}")
    
    async def _process_message(self, message_value: str):
        """Process a single Kafka message."""
        try:
            message = json.loads(message_value)
            metrics = message.get("metrics") if isinstance(message.get("metrics"), dict) else message
            charger_id = message.get("charger_id") or metrics.get("charger_id")
            tenant_id = message.get("tenant_id") or message.get("operator_id")
            
            if not charger_id:
                logger.warning("Message missing charger_id, skipping")
                return
            
            if isinstance(metrics, dict):
                metrics.setdefault("charger_id", charger_id)
            
            # Collect data for training
            await self.data_collector.collect_charger_metrics(message)
            
            # Trigger prediction if enabled
            if settings.enable_predictions:
                failure_pred = await self.prediction_service.predict_failure(
                    charger_id,
                    metrics,
                    tenant_id=tenant_id,
                )
                if failure_pred and failure_pred.get("failure_probability", 0.0) >= 0.85:
                    payload = dict(failure_pred)
                    payload["source_topic"] = CHARGER_METRICS_TOPIC
                    await self.producer.publish(FAILURE_ALERTS_TOPIC, payload)
            
            # Anomaly detection
            detector = await self.prediction_service.model_manager.get_model("anomaly_detector")
            if detector:
                anomaly_result = detector.detect(metrics, tenant_id=tenant_id)
                if anomaly_result.get("is_anomaly"):
                    payload = dict(anomaly_result)
                    payload["source_topic"] = CHARGER_METRICS_TOPIC
                    await self.producer.publish(ANOMALIES_TOPIC, payload)
            
        except Exception as e:
            logger.error(f"Failed to process message: {e}")
    
    async def stop(self):
        """Stop Kafka consumer."""
        self.running = False
        if self.consumer:
            self.consumer.close()
        logger.info("Kafka consumer stopped")

"""
Kafka producer for sending predictions.
"""
import json
import logging
from confluent_kafka import Producer
from typing import Dict, Any, Optional
from src.config.settings import settings
from src.kafka.topics import PREDICTIONS_TOPIC

logger = logging.getLogger(__name__)

class KafkaProducer:
    """Kafka producer for publishing predictions."""
    
    _instance: Optional['KafkaProducer'] = None

    def __init__(self):
        self.producer = None

    @classmethod
    def get_instance(cls) -> 'KafkaProducer':
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = KafkaProducer()
        return cls._instance
    
    async def start(self):
        """Initialize Kafka producer."""
        if self.producer:
            return

        try:
            self.producer = Producer({
                'bootstrap.servers': settings.kafka_brokers,
                'client.id': settings.kafka_client_id,
            })
            logger.info("Kafka producer initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {e}")
            self.producer = None
            raise
    
    async def publish_prediction(self, prediction: Dict[str, Any]):
        """
        Publish prediction to Kafka.
        
        Args:
            prediction: Prediction result dictionary
        """
        await self.publish(PREDICTIONS_TOPIC, prediction)

    async def publish(self, topic: str, payload: Dict[str, Any]):
        """
        Publish payload to a Kafka topic.
        
        Args:
            topic: Target Kafka topic
            payload: Message payload
        """
        if not self.producer:
            logger.debug("Producer not initialized, skipping publish")
            return
        
        try:
            message = json.dumps(payload, default=str)
            self.producer.produce(
                topic,
                value=message.encode('utf-8'),
                callback=self._delivery_callback,
            )
            self.producer.poll(0)
            
        except Exception as e:
            logger.error(f"Failed to publish to {topic}: {e}")
    
    def _delivery_callback(self, err, msg):
        """Callback for message delivery."""
        if err:
            logger.error(f"Message delivery failed: {err}")
        else:
            logger.debug(f"Message delivered to {msg.topic()}")
    
    async def flush(self):
        """Flush pending messages."""
        if self.producer:
            self.producer.flush()
    
    async def stop(self):
        """Stop Kafka producer."""
        if self.producer:
            await self.flush()
        logger.info("Kafka producer stopped")

"""
Data collector service for gathering training data from Kafka.
"""
import logging
import uuid
from typing import Dict, Any
from datetime import datetime, timezone

from src.database.connection import AsyncSessionLocal
from src.database.models import ChargerMetrics

logger = logging.getLogger(__name__)


class DataCollector:
    """Collects and processes data from Kafka for model training."""
    
    async def collect_charger_metrics(
        self,
        message: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Process charger metrics from Kafka.
        
        Args:
            message: Kafka message containing charger metrics
            
        Returns:
            Processed metrics dictionary
        """
        try:
            charger_id = message.get("charger_id")
            timestamp_str = message.get("timestamp")

            if timestamp_str:
                if isinstance(timestamp_str, str):
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00")).replace(tzinfo=None)
                    except ValueError:
                        timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
                elif isinstance(timestamp_str, (int, float)):
                    timestamp = datetime.fromtimestamp(timestamp_str, timezone.utc).replace(tzinfo=None)
                else:
                    timestamp = timestamp_str if isinstance(timestamp_str, datetime) else datetime.now(timezone.utc).replace(tzinfo=None)
            else:
                timestamp = datetime.now(timezone.utc).replace(tzinfo=None)

            metrics_record = ChargerMetrics(
                id=str(uuid.uuid4()),
                charger_id=charger_id,
                timestamp=timestamp,
                connector_status=message.get("connector_status"),
                energy_delivered=message.get("energy_delivered"),
                power=message.get("power"),
                temperature=message.get("temperature"),
                error_codes=message.get("error_codes"),
                uptime_hours=message.get("uptime_hours"),
                total_sessions=message.get("total_sessions"),
                raw_data=message
            )

            async with AsyncSessionLocal() as session:
                session.add(metrics_record)
                await session.commit()
            
            logger.debug(f"Collected metrics for charger: {charger_id}")
            
            return {
                "charger_id": charger_id,
                "timestamp": timestamp,
                "metrics": message,
            }
            
        except Exception as e:
            logger.error(f"Data collection failed: {e}")
            raise


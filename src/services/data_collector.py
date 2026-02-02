"""
Data collector service for gathering training data from Kafka.
"""
import logging
import uuid
import json
from typing import Dict, Any
from datetime import datetime

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
        Process charger metrics from Kafka and save to database.
        
        Args:
            message: Kafka message containing charger metrics
            
        Returns:
            Processed metrics dictionary
        """
        async with AsyncSessionLocal() as session:
            try:
                charger_id = message.get("charger_id")
                if not charger_id:
                    logger.warning("Message missing charger_id, skipping")
                    return {}

                # Parse error_codes
                error_codes = message.get("error_codes", [])
                if isinstance(error_codes, str):
                    try:
                        error_codes = json.loads(error_codes)
                    except json.JSONDecodeError:
                        error_codes = []

                # Parse timestamp
                ts_val = message.get("timestamp")
                if ts_val:
                    if isinstance(ts_val, str):
                        try:
                            timestamp = datetime.fromisoformat(ts_val.replace("Z", "+00:00"))
                        except ValueError:
                            timestamp = datetime.utcnow()
                    else:
                        timestamp = ts_val
                else:
                    timestamp = datetime.utcnow()

                # Create database record
                record = ChargerMetrics(
                    id=str(uuid.uuid4()),
                    charger_id=charger_id,
                    timestamp=timestamp,
                    connector_status=message.get("connector_status"),
                    energy_delivered=float(message.get("energy_delivered", 0.0) or 0.0),
                    power=float(message.get("power", 0.0) or 0.0),
                    temperature=float(message.get("temperature", 0.0) or 0.0),
                    error_codes=error_codes,
                    uptime_hours=float(message.get("uptime_hours", 0.0) or 0.0),
                    total_sessions=int(message.get("total_sessions", 0) or 0),
                    raw_data=message
                )

                session.add(record)
                await session.commit()

                logger.debug(f"Collected metrics for charger: {charger_id}")

                return {
                    "charger_id": charger_id,
                    "timestamp": timestamp,
                    "metrics": message,
                    "saved": True
                }

            except Exception as e:
                await session.rollback()
                logger.error(f"Data collection failed: {e}")
                # We log but re-raise so consumer knows it failed (and might not commit offset)
                raise e

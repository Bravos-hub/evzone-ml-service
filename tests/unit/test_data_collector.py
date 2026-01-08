"""
Unit tests for DataCollector.
"""
import pytest

from src.services.data_collector import DataCollector


@pytest.mark.asyncio
async def test_collect_charger_metrics_success():
    collector = DataCollector()
    message = {"charger_id": "c1", "value": 1}

    result = await collector.collect_charger_metrics(message)

    assert result["charger_id"] == "c1"
    assert result["metrics"] == message


@pytest.mark.asyncio
async def test_collect_charger_metrics_error():
    collector = DataCollector()

    class BadMessage:
        def get(self, key, default=None):
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        await collector.collect_charger_metrics(BadMessage())

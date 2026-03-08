"""
Unit tests for DataCollector.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock, call

from src.services.data_collector import DataCollector


@pytest.mark.asyncio
@patch("src.services.data_collector.AsyncSessionLocal")
async def test_collect_charger_metrics_success(mock_session_local):
    mock_session = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session_local.return_value.__aenter__.return_value = mock_session

    collector = DataCollector()
    message = {"charger_id": "c1", "value": 1, "connector_status": "Available"}

    result = await collector.collect_charger_metrics(message)

    assert result["charger_id"] == "c1"
    assert result["metrics"] == message

    mock_session.add.assert_called_once()
    mock_session.commit.assert_awaited_once()

    # Verify the added model properties
    added_model = mock_session.add.call_args[0][0]
    assert added_model.charger_id == "c1"
    assert added_model.connector_status == "Available"
    assert added_model.raw_data == message


@pytest.mark.asyncio
@patch("src.services.data_collector.AsyncSessionLocal")
async def test_collect_charger_metrics_error(mock_session_local):
    mock_session = AsyncMock()
    mock_session_local.return_value.__aenter__.return_value = mock_session

    collector = DataCollector()

    class BadMessage:
        def get(self, key, default=None):
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        await collector.collect_charger_metrics(BadMessage())

"""
Integration test for Data Persistence.
"""
import pytest
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.data_collector import DataCollector
from src.database.models import ChargerMetrics

@pytest.mark.asyncio
async def test_collect_charger_metrics_persistence():
    # Mock message
    message = {
        "charger_id": "test-charger-1",
        "connector_status": "CHARGING",
        "energy_delivered": 10.5,
        "power": 5.0,
        "temperature": 45.0,
        "error_codes": ["E1"],
        "uptime_hours": 100.0,
        "total_sessions": 20,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # Mock session
    mock_session = AsyncMock()

    # Mock AsyncSessionLocal to return our mock session
    # We need to mock the context manager aspect of AsyncSessionLocal()
    # AsyncSessionLocal() returns an object that has __aenter__ returning the session

    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__.return_value = mock_session
    mock_session_factory.return_value.__aexit__.return_value = None

    with patch("src.services.data_collector.AsyncSessionLocal", mock_session_factory):
        collector = DataCollector()
        result = await collector.collect_charger_metrics(message)

        # Verify result
        assert result["saved"] is True
        assert result["charger_id"] == "test-charger-1"

        # Verify DB interactions
        assert mock_session.add.called
        assert mock_session.commit.called

        # Verify what was added
        args = mock_session.add.call_args[0]
        record = args[0]
        assert isinstance(record, ChargerMetrics)
        assert record.charger_id == "test-charger-1"
        assert record.power == 5.0
        assert record.error_codes == ["E1"]

@pytest.mark.asyncio
async def test_collect_charger_metrics_persistence_failure():
    message = {"charger_id": "fail"}

    mock_session = AsyncMock()
    mock_session.commit.side_effect = Exception("DB Error")

    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__.return_value = mock_session
    mock_session_factory.return_value.__aexit__.return_value = None

    with patch("src.services.data_collector.AsyncSessionLocal", mock_session_factory):
        collector = DataCollector()

        with pytest.raises(Exception) as exc:
            await collector.collect_charger_metrics(message)

        assert "DB Error" in str(exc.value)
        assert mock_session.rollback.called

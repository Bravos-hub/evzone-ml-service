"""
Unit tests for prediction route helper functions.
"""
from datetime import datetime, timezone

import pytest

from src.api.routes import predictions as pr


def test_parse_datetime_invalid_string():
    assert pr._parse_datetime("bad-date") is None


def test_parse_window_instance_and_missing():
    window = pr.PredictedFailureWindow(
        start=datetime.now(timezone.utc),
        end=datetime.now(timezone.utc),
    )
    assert pr._parse_window(window) is window
    assert pr._parse_window({"start": "2026-01-01T00:00:00Z"}) is None


def test_parse_cost_benefit_instance_and_type_error():
    cb = pr.CostBenefitAnalysis(
        preventive_maintenance_cost=1.0,
        expected_failure_cost=2.0,
        net_savings=1.0,
    )
    assert pr._parse_cost_benefit(cb) is cb
    assert pr._parse_cost_benefit({1: "bad"}) is None
    assert pr._parse_cost_benefit("bad") is None


def test_build_failure_response_fallbacks():
    result = {
        "charger_id": "c1",
        "failure_probability": 0.2,
        "predicted_failure_date": "2026-01-01T00:00:00Z",
        "predicted_failure_window": None,
        "confidence": None,
        "confidence_score": None,
        "recommended_action": "BAD",
        "recommended_action_window": "WORSE",
        "timestamp": "bad-date",
    }
    response = pr._build_failure_response(result, tenant_id="t1")

    assert response.tenant_id == "t1"
    assert response.predicted_failure_window is not None
    assert response.recommended_action == "WITHIN_30_DAYS"
    assert response.recommended_action_window == "WITHIN_30_DAYS"
    assert response.confidence == 0.0
    assert response.confidence_score == 0.0


def test_build_maintenance_response_fallbacks():
    result = {
        "charger_id": "c1",
        "urgency": "BAD",
        "urgency_level": "WORSE",
        "estimated_downtime_hours": 1.0,
        "cost_benefit": {1: "bad"},
        "timestamp": "bad-date",
    }
    response = pr._build_maintenance_response(result, tenant_id=None)

    assert response.urgency == "LOW"
    assert response.urgency_level == "LOW"
    assert response.cost_benefit is None

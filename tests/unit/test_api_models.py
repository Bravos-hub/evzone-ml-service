"""
Unit tests for model management API routes.
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

def test_list_models_success(client, auth_headers):
    mock_models = {
        "failure_predictor": {
            "name": "failure_predictor",
            "version": "v1.0.0",
            "type": "FailurePredictor",
            "status": "LOADED"
        }
    }

    with patch("src.services.model_manager.ModelManager.list_models") as mock_list:
        mock_list.return_value = mock_models

        response = client.get("/api/v1/models", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["models"][0]["name"] == "failure_predictor"

def test_reload_all_models_success(client, auth_headers):
    mock_models = {"m1": {}, "m2": {}}

    with patch("src.services.model_manager.ModelManager.list_models") as mock_list, \
         patch("src.services.model_manager.ModelManager.reload_model") as mock_reload:
        mock_list.return_value = mock_models
        mock_reload.return_value = True

        response = client.post("/api/v1/models/reload", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["model_name"] == "all"
    assert mock_reload.call_count == 2

def test_reload_specific_model_success(client, auth_headers):
    with patch("src.services.model_manager.ModelManager.reload_model") as mock_reload:
        mock_reload.return_value = True

        response = client.post("/api/v1/models/reload?model_name=failure_predictor", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["model_name"] == "failure_predictor"
    mock_reload.assert_called_once_with("failure_predictor")

def test_list_models_failure_handles_exception(client, auth_headers):
    with patch("src.services.model_manager.ModelManager.list_models") as mock_list:
        mock_list.side_effect = Exception("Internal error")

        response = client.get("/api/v1/models", headers=auth_headers)

    assert response.status_code == 500
    assert "Failed to list models" in response.json()["detail"]

"""API tests using an injected lightweight model registry."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import numpy as np
from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.model_loader import ModelLoadError


class FixedRegressor:
    """Small deterministic stand-in for a saved regression pipeline."""

    def __init__(self, value: float) -> None:
        self.value = value

    def predict(self, features) -> np.ndarray:
        return np.full(len(features), self.value)


class FixedClassifier:
    """Small deterministic stand-in for a saved classification pipeline."""

    def __init__(self, probability: float) -> None:
        self.probability = probability

    def predict_proba(self, features) -> np.ndarray:
        positive = np.full(len(features), self.probability)
        return np.column_stack([1 - positive, positive])


class StubRegistry:
    """Registry-compatible fixture that avoids loading large production models."""

    is_loaded = True

    def load_all(self) -> None:
        return None

    def describe(self) -> list[dict[str, Any]]:
        return [
            {
                "task": task,
                "horizon_hours": horizon,
                "model_name": "stub",
                "artifact": "stub.joblib",
            }
            for horizon in (1, 6, 12, 24)
            for task in ("temperature", "rain_probability", "rainfall_amount")
        ]

    def get_artifact(self, task: str, horizon: int) -> dict[str, Any]:
        if task == "temperature":
            model = FixedRegressor(24.0 + horizon / 10)
        elif task == "rain_probability":
            return {
                "model": FixedClassifier(0.71),
                "feature_columns": ["temperature_2m"],
                "threshold": 0.5,
            }
        else:
            model = FixedRegressor(1.8)
        return {"model": model, "feature_columns": ["temperature_2m"]}


class MissingModelRegistry:
    """Registry fixture that represents an unavailable model volume."""

    is_loaded = False

    def load_all(self) -> None:
        raise ModelLoadError("Selected model file is missing: models/example.joblib")


client = TestClient(create_app(StubRegistry()))


def valid_payload(hours: int = 169) -> dict[str, list[dict[str, object]]]:
    """Create contiguous hourly observations accepted by the prediction endpoint."""
    start = datetime(2025, 1, 1)
    observations = []
    for index in range(hours):
        observations.append(
            {
                "timestamp": (start + timedelta(hours=index)).isoformat(),
                "temperature": 22.0 + (index % 24) / 10,
                "relative_humidity": 70.0,
                "precipitation": 0.0,
                "surface_pressure": 920.0,
                "cloud_cover": 40.0,
                "wind_speed": 8.0,
                "wind_direction": 180.0,
            }
        )
    return {"observations": observations}


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "location": "Bangalore",
        "models_loaded": True,
    }


def test_readiness_endpoint() -> None:
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "location": "Bangalore",
        "models_loaded": True,
    }


def test_liveness_survives_missing_models_and_readiness_is_unavailable() -> None:
    missing_client = TestClient(create_app(MissingModelRegistry()))
    assert missing_client.get("/health").status_code == 200
    response = missing_client.get("/health/ready")
    assert response.status_code == 503
    assert "Selected model file is missing" in response.json()["detail"]


def test_valid_prediction() -> None:
    response = client.post("/predict", json=valid_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["location"] == "Bangalore"
    assert [forecast["horizon_hours"] for forecast in body["forecasts"]] == [1, 6, 12, 24]
    assert body["forecasts"][0]["rain_probability"] == 0.71
    assert body["forecasts"][0]["rain_expected"] is True


def test_invalid_input() -> None:
    payload = valid_payload()
    payload["observations"][0]["relative_humidity"] = 150
    response = client.post("/predict", json=payload)
    assert response.status_code == 422


def test_missing_observations() -> None:
    response = client.post("/predict", json=valid_payload(hours=20))
    assert response.status_code == 422
    assert "At least 169 hourly observations" in response.json()["detail"]


def test_prediction_response_structure() -> None:
    body = client.post("/predict", json=valid_payload()).json()
    assert set(body) == {"location", "generated_at", "forecasts"}
    required = {
        "horizon_hours",
        "temperature_c",
        "rain_probability",
        "rain_expected",
        "rainfall_mm",
    }
    assert len(body["forecasts"]) == 4
    assert all(set(forecast) == required for forecast in body["forecasts"])


def test_missing_required_field() -> None:
    payload = valid_payload()
    del payload["observations"][0]["wind_direction"]
    response = client.post("/predict", json=payload)
    assert response.status_code == 422


def test_invalid_timestamp() -> None:
    payload = valid_payload()
    payload["observations"][0]["timestamp"] = "not-a-timestamp"
    response = client.post("/predict", json=payload)
    assert response.status_code == 422

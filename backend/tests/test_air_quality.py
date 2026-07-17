"""Tests for the cached Open-Meteo air-quality integration."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app.air_quality import OpenMeteoAirQualityService
from backend.app.main import create_app
from backend.app.open_meteo import OpenMeteoObservationError


def air_quality_payload(*, aqi: float = 42, pm2_5: float = 8, pm10: float = 19) -> dict[str, Any]:
    """Return a representative current-reading response from Open-Meteo."""
    return {
        "current": {
            "time": "2026-07-18T09:00",
            "us_aqi": aqi,
            "pm2_5": pm2_5,
            "pm10": pm10,
        }
    }


def uv_payload(*, uv_index: float = 2.4) -> dict[str, Any]:
    """Return a representative current UV response from the Forecast API."""
    return {"current": {"time": "2026-07-18T09:00", "uv_index": uv_index}}


class FakeResponse:
    """Minimal httpx response replacement for request tests."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self.payload


def test_air_quality_response_is_summarized(monkeypatch: pytest.MonkeyPatch) -> None:
    """A valid current reading maps to clear dashboard labels."""
    monkeypatch.setattr(
        httpx,
        "get",
        lambda url, **_kwargs: FakeResponse(uv_payload() if "forecast" in url else air_quality_payload()),
    )
    result = OpenMeteoAirQualityService(retries=1).fetch_environment()

    assert result.us_aqi == 42
    assert result.air_quality_label == "Good"
    assert result.dust_outlook == "Low"
    assert result.uv_index == 2.4
    assert result.uv_label == "Low"
    assert result.pm10 == 19.0


def test_air_quality_rejects_missing_values(monkeypatch: pytest.MonkeyPatch) -> None:
    """Incomplete external responses do not reach the browser."""
    payload = air_quality_payload()
    del payload["current"]["pm10"]
    monkeypatch.setattr(
        httpx,
        "get",
        lambda url, **_kwargs: FakeResponse(uv_payload() if "forecast" in url else payload),
    )

    with pytest.raises(OpenMeteoObservationError, match="missing: pm10"):
        OpenMeteoAirQualityService(retries=1).fetch_environment()


def test_air_quality_cache_reuses_a_fresh_reading(monkeypatch: pytest.MonkeyPatch) -> None:
    """The upstream API is not queried again within the cache window."""
    calls = 0

    def request(*_args: Any, **_kwargs: Any) -> FakeResponse:
        nonlocal calls
        calls += 1
        return FakeResponse(uv_payload() if "forecast" in _args[0] else air_quality_payload())

    monkeypatch.setattr(httpx, "get", request)
    service = OpenMeteoAirQualityService(retries=1, clock=lambda: 100.0)
    assert service.fetch_environment().us_aqi == 42
    assert service.fetch_environment().us_aqi == 42
    assert calls == 2


def test_environment_endpoint_returns_service_response() -> None:
    """The dashboard endpoint exposes a valid injected service response."""

    class FakeAirQualityService:
        def fetch_environment(self):  # type: ignore[no-untyped-def]
            return OpenMeteoAirQualityService._to_environmental_insights(air_quality_payload(), uv_payload())

    with TestClient(create_app(air_quality_service=FakeAirQualityService())) as client:
        response = client.get("/api/environment")

    assert response.status_code == 200
    assert response.json()["air_quality_label"] == "Good"

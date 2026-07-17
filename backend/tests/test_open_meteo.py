"""Tests for live Open-Meteo observation translation and caching."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app import config
from backend.app.main import create_app
from backend.app.open_meteo import OpenMeteoObservationError, OpenMeteoObservationService
from backend.app.schemas import DailyForecast, HourlyForecast, ObservationHistoryResponse, WeatherObservation


class FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self.payload


def hourly_payload(records: int = 169) -> dict[str, Any]:
    start = datetime(2026, 7, 1)
    hourly: dict[str, list[Any]] = {
        "time": [(start + timedelta(hours=index)).isoformat(timespec="minutes") for index in range(records)]
    }
    for field in config.OPEN_METEO_HOURLY_FIELDS:
        hourly[field] = [20.0 + index / 100 for index in range(records)]
    daily: dict[str, list[Any]] = {
        "time": [(date(2026, 7, 1) + timedelta(days=index)).isoformat() for index in range(6)]
    }
    for field in config.OPEN_METEO_DAILY_FIELDS:
        if field == "sunrise":
            daily[field] = [(datetime(2026, 7, 1, 6) + timedelta(days=index)).isoformat(timespec="minutes") for index in range(6)]
        elif field == "sunset":
            daily[field] = [(datetime(2026, 7, 1, 18) + timedelta(days=index)).isoformat(timespec="minutes") for index in range(6)]
        elif field == "daylight_duration":
            daily[field] = [43_200.0] * 6
        else:
            daily[field] = [20.0 + index for index in range(6)]
    return {"hourly": hourly, "daily": daily}


def test_successful_open_meteo_response_is_converted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("backend.app.open_meteo.httpx.get", lambda *args, **kwargs: FakeResponse(hourly_payload()))
    history = OpenMeteoObservationService().fetch_observations()
    assert len(history.observations) == 169
    assert history.source == "Open-Meteo"
    assert history.observations[0].timestamp.isoformat().startswith("2026-07-01T00:00")
    assert history.observations[-1].temperature == pytest.approx(21.68)
    assert len(history.daily_forecasts) == 6
    assert len(history.hourly_forecasts) == config.OPEN_METEO_HOURLY_FORECAST_COUNT
    assert history.hourly_forecasts[-1].temperature == pytest.approx(21.68)
    assert history.daily_forecasts[0].date.isoformat() == "2026-07-01"


def test_forecast_request_uses_required_bengaluru_parameters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fetch(url: str, **kwargs: Any) -> FakeResponse:
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse(hourly_payload())

    monkeypatch.setattr("backend.app.open_meteo.httpx.get", fetch)
    OpenMeteoObservationService().fetch_observations()

    assert captured["url"] == config.OPEN_METEO_FORECAST_URL
    assert captured["params"] == {
        "latitude": 12.9716,
        "longitude": 77.5946,
        "timezone": "Asia/Kolkata",
        "past_hours": 168,
        "forecast_hours": 24,
        "forecast_days": 6,
        "hourly": ",".join(config.OPEN_METEO_HOURLY_FIELDS),
        "daily": ",".join(config.OPEN_METEO_DAILY_FIELDS),
    }
    assert captured["timeout"] == config.OPEN_METEO_TIMEOUT_SECONDS


def test_insufficient_records_are_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("backend.app.open_meteo.httpx.get", lambda *args, **kwargs: FakeResponse(hourly_payload(168)))
    with pytest.raises(OpenMeteoObservationError, match="only 168 hourly records"):
        OpenMeteoObservationService().fetch_observations()


def test_missing_open_meteo_values_are_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = hourly_payload()
    payload["hourly"]["dew_point_2m"][42] = None
    monkeypatch.setattr("backend.app.open_meteo.httpx.get", lambda *args, **kwargs: FakeResponse(payload))
    with pytest.raises(OpenMeteoObservationError, match="missing values"):
        OpenMeteoObservationService().fetch_observations()


def test_non_contiguous_timestamps_are_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = hourly_payload()
    payload["hourly"]["time"][80] = "2026-07-04T09:00"
    monkeypatch.setattr("backend.app.open_meteo.httpx.get", lambda *args, **kwargs: FakeResponse(payload))
    with pytest.raises(OpenMeteoObservationError, match="not contiguous"):
        OpenMeteoObservationService().fetch_observations()


def test_non_contiguous_daily_dates_are_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = hourly_payload()
    payload["daily"]["time"][3] = "2026-07-06"
    monkeypatch.setattr("backend.app.open_meteo.httpx.get", lambda *args, **kwargs: FakeResponse(payload))
    with pytest.raises(OpenMeteoObservationError, match="daily forecasts are not consecutive"):
        OpenMeteoObservationService().fetch_observations()


def test_open_meteo_timeout_returns_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_timeout(*args: Any, **kwargs: Any) -> None:
        raise httpx.TimeoutException("timed out")

    monkeypatch.setattr("backend.app.open_meteo.httpx.get", raise_timeout)
    service = OpenMeteoObservationService(retries=2, sleeper=lambda _: None)
    with pytest.raises(OpenMeteoObservationError, match="Unable to fetch Bengaluru"):
        service.fetch_observations()


def test_cache_reuses_valid_open_meteo_response(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    def fetch(*args: Any, **kwargs: Any) -> FakeResponse:
        nonlocal calls
        calls += 1
        return FakeResponse(hourly_payload())

    monkeypatch.setattr("backend.app.open_meteo.httpx.get", fetch)
    service = OpenMeteoObservationService()
    service.fetch_observations()
    service.fetch_observations()
    assert calls == 1


class FakeObservationService:
    def fetch_observations(self, _location) -> ObservationHistoryResponse:  # type: ignore[no-untyped-def]
        observation = WeatherObservation(
            timestamp=datetime(2026, 7, 1), temperature=24, relative_humidity=70,
            precipitation=0, surface_pressure=920, cloud_cover=40, wind_speed=8, wind_direction=180,
        )
        return ObservationHistoryResponse(
            location="Bengaluru, India", latitude=12.9716, longitude=77.5946, timezone="Asia/Kolkata",
            model_supported=True, source="Open-Meteo", latest_timestamp=observation.timestamp,
            observations=[observation] * 169,
            hourly_forecasts=[
                HourlyForecast(
                    timestamp=datetime(2026, 7, 1), temperature=24,
                    precipitation_probability=20, weather_code=1,
                )
            ],
            daily_forecasts=[
                DailyForecast(
                    date=date(2026, 7, 1), weather_code=1, temperature_max=28,
                    temperature_min=20, precipitation_probability=20, precipitation_sum=0,
                    sunrise=datetime(2026, 7, 1, 6), sunset=datetime(2026, 7, 1, 18),
                    daylight_duration_seconds=43_200,
                )
            ],
        )


def test_observations_endpoint_returns_skycast_records() -> None:
    response = TestClient(create_app(observation_service=FakeObservationService())).get("/api/observations")
    assert response.status_code == 200
    assert response.json()["source"] == "Open-Meteo"
    assert len(response.json()["observations"]) == 169
    assert len(response.json()["hourly_forecasts"]) == 1
    assert len(response.json()["daily_forecasts"]) == 1

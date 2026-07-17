"""Fetch, validate, cache, and translate live Open-Meteo observations."""

from __future__ import annotations

import logging
import math
import time
from datetime import date, datetime, timedelta
from threading import RLock
from typing import Any, Callable

import httpx

from backend.app import config
from backend.app.schemas import DailyForecast, HourlyForecast, ObservationHistoryResponse, WeatherObservation
from pydantic import ValidationError

LOGGER = logging.getLogger(__name__)


class OpenMeteoObservationError(RuntimeError):
    """Raised when a usable recent weather history cannot be obtained."""


class OpenMeteoObservationService:
    """Provide a one-hour cached, prediction-ready Bengaluru weather history."""

    def __init__(
        self,
        *,
        cache_seconds: int = config.OPEN_METEO_CACHE_SECONDS,
        retries: int = config.OPEN_METEO_RETRIES,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self.cache_seconds = cache_seconds
        self.retries = retries
        self._clock = clock
        self._sleeper = sleeper
        self._cache: ObservationHistoryResponse | None = None
        self._cached_at = 0.0
        self._lock = RLock()

    def fetch_observations(self) -> ObservationHistoryResponse:
        """Return cached observations or obtain and validate a fresh Open-Meteo response."""
        with self._lock:
            if self._cache is not None and self._clock() - self._cached_at < self.cache_seconds:
                LOGGER.info("Using cached Open-Meteo observations")
                return self._cache.model_copy(deep=True)

            payload = self._request_hourly_data()
            history = self._to_observation_history(payload)
            self._cache = history
            self._cached_at = self._clock()
            LOGGER.info("Cached %d Open-Meteo Bengaluru observations", len(history.observations))
            return history.model_copy(deep=True)

    def _request_hourly_data(self) -> dict[str, Any]:
        params = {
            "latitude": config.OPEN_METEO_LATITUDE,
            "longitude": config.OPEN_METEO_LONGITUDE,
            "timezone": config.TIMEZONE,
            "past_hours": config.OPEN_METEO_PAST_HOURS,
            "forecast_hours": config.OPEN_METEO_FORECAST_HOURS,
            "forecast_days": config.OPEN_METEO_FORECAST_DAYS,
            "hourly": ",".join(config.OPEN_METEO_HOURLY_FIELDS),
            "daily": ",".join(config.OPEN_METEO_DAILY_FIELDS),
        }
        last_error: Exception | None = None
        for attempt in range(self.retries):
            try:
                response = httpx.get(
                    config.OPEN_METEO_FORECAST_URL,
                    params=params,
                    timeout=config.OPEN_METEO_TIMEOUT_SECONDS,
                )
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise OpenMeteoObservationError("Open-Meteo returned an invalid JSON payload.")
                return payload
            except (httpx.HTTPError, ValueError, OpenMeteoObservationError) as exc:
                last_error = exc
                LOGGER.warning(
                    "Open-Meteo request failed (attempt %d/%d): %s",
                    attempt + 1,
                    self.retries,
                    exc,
                )
                if attempt < self.retries - 1:
                    self._sleeper(0.5 * (2**attempt))
        raise OpenMeteoObservationError(
            "Unable to fetch Bengaluru weather history from Open-Meteo. Please try again shortly."
        ) from last_error

    @staticmethod
    def _to_observation_history(payload: dict[str, Any]) -> ObservationHistoryResponse:
        hourly = payload.get("hourly")
        if not isinstance(hourly, dict):
            raise OpenMeteoObservationError("Open-Meteo response did not contain hourly weather data.")

        columns = ("time", *config.OPEN_METEO_HOURLY_FIELDS)
        missing_columns = [column for column in columns if column not in hourly]
        if missing_columns:
            raise OpenMeteoObservationError(
                f"Open-Meteo response is missing hourly fields: {', '.join(missing_columns)}."
            )
        if any(not isinstance(hourly[column], list) for column in columns):
            raise OpenMeteoObservationError("Open-Meteo hourly fields must be arrays.")

        record_count = len(hourly["time"])
        if record_count < config.MINIMUM_OBSERVATIONS:
            raise OpenMeteoObservationError(
                f"Open-Meteo returned only {record_count} hourly records; at least "
                f"{config.MINIMUM_OBSERVATIONS} are required."
            )
        unequal = [column for column in columns if len(hourly[column]) != record_count]
        if unequal:
            raise OpenMeteoObservationError(
                f"Open-Meteo hourly field lengths do not match: {', '.join(unequal)}."
            )

        observations: list[WeatherObservation] = []
        previous_time: datetime | None = None
        for index in range(record_count):
            values = {column: hourly[column][index] for column in columns}
            missing_values = [column for column, value in values.items() if value is None]
            if missing_values:
                raise OpenMeteoObservationError(
                    "Open-Meteo returned missing values for "
                    f"record {index}: {', '.join(missing_values)}."
                )
            invalid_numeric = [
                column
                for column in config.OPEN_METEO_HOURLY_FIELDS
                if not isinstance(values[column], (int, float)) or not math.isfinite(values[column])
            ]
            if invalid_numeric:
                raise OpenMeteoObservationError(
                    "Open-Meteo returned invalid numeric values for "
                    f"record {index}: {', '.join(invalid_numeric)}."
                )
            try:
                timestamp = datetime.fromisoformat(str(values["time"]).replace("Z", "+00:00"))
            except ValueError as exc:
                raise OpenMeteoObservationError(
                    f"Open-Meteo returned an invalid timestamp at record {index}."
                ) from exc
            if previous_time is not None and timestamp - previous_time != timedelta(hours=1):
                raise OpenMeteoObservationError(
                    "Open-Meteo timestamps are not contiguous hourly records."
                )
            previous_time = timestamp
            try:
                observations.append(
                    WeatherObservation(
                        timestamp=timestamp,
                        temperature=float(values["temperature_2m"]),
                        relative_humidity=float(values["relative_humidity_2m"]),
                        precipitation=float(values["precipitation"]),
                        surface_pressure=float(values["surface_pressure"]),
                        cloud_cover=float(values["cloud_cover"]),
                        wind_speed=float(values["wind_speed_10m"]),
                        wind_direction=float(values["wind_direction_10m"]),
                    )
                )
            except (TypeError, ValueError, ValidationError) as exc:
                raise OpenMeteoObservationError(
                    f"Open-Meteo returned invalid numeric values at record {index}."
                ) from exc

        if observations != sorted(observations, key=lambda observation: observation.timestamp):
            raise OpenMeteoObservationError("Open-Meteo records are not sorted oldest to newest.")
        hourly_forecasts = OpenMeteoObservationService._to_hourly_forecasts(hourly)
        daily_forecasts = OpenMeteoObservationService._to_daily_forecasts(payload)
        return ObservationHistoryResponse(
            location=config.DISPLAY_LOCATION,
            source="Open-Meteo",
            latest_timestamp=observations[-1].timestamp,
            observations=observations,
            hourly_forecasts=hourly_forecasts,
            daily_forecasts=daily_forecasts,
        )

    @staticmethod
    def _to_hourly_forecasts(hourly: dict[str, Any]) -> list[HourlyForecast]:
        """Translate the requested upcoming hours into dashboard forecast records."""
        start_index = len(hourly["time"]) - config.OPEN_METEO_HOURLY_FORECAST_COUNT
        if start_index < 0:
            raise OpenMeteoObservationError("Open-Meteo returned too few hourly forecasts.")

        forecasts: list[HourlyForecast] = []
        for index in range(start_index, len(hourly["time"])):
            try:
                timestamp = datetime.fromisoformat(str(hourly["time"][index]).replace("Z", "+00:00"))
                forecasts.append(
                    HourlyForecast(
                        timestamp=timestamp,
                        temperature=float(hourly["temperature_2m"][index]),
                        precipitation_probability=float(hourly["precipitation_probability"][index]),
                        weather_code=int(hourly["weather_code"][index]),
                    )
                )
            except (TypeError, ValueError, ValidationError) as exc:
                raise OpenMeteoObservationError(
                    f"Open-Meteo returned invalid hourly forecast values at record {index}."
                ) from exc
        return forecasts

    @staticmethod
    def _to_daily_forecasts(payload: dict[str, Any]) -> list[DailyForecast]:
        """Convert Open-Meteo daily arrays into six validated forecast records."""
        daily = payload.get("daily")
        if not isinstance(daily, dict):
            raise OpenMeteoObservationError("Open-Meteo response did not contain daily forecast data.")

        columns = ("time", *config.OPEN_METEO_DAILY_FIELDS)
        missing_columns = [column for column in columns if column not in daily]
        if missing_columns:
            raise OpenMeteoObservationError(
                f"Open-Meteo response is missing daily fields: {', '.join(missing_columns)}."
            )
        if any(not isinstance(daily[column], list) for column in columns):
            raise OpenMeteoObservationError("Open-Meteo daily fields must be arrays.")

        record_count = len(daily["time"])
        if record_count < config.OPEN_METEO_FORECAST_DAYS:
            raise OpenMeteoObservationError(
                f"Open-Meteo returned only {record_count} daily forecasts; at least "
                f"{config.OPEN_METEO_FORECAST_DAYS} are required."
            )
        unequal = [column for column in columns if len(daily[column]) != record_count]
        if unequal:
            raise OpenMeteoObservationError(
                f"Open-Meteo daily field lengths do not match: {', '.join(unequal)}."
            )

        forecasts: list[DailyForecast] = []
        previous_date: date | None = None
        for index in range(config.OPEN_METEO_FORECAST_DAYS):
            values = {column: daily[column][index] for column in columns}
            missing_values = [column for column, value in values.items() if value is None]
            if missing_values:
                raise OpenMeteoObservationError(
                    "Open-Meteo returned missing daily values for "
                    f"record {index}: {', '.join(missing_values)}."
                )
            numeric_fields = (
                "weather_code",
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_probability_max",
                "precipitation_sum",
                "daylight_duration",
            )
            invalid_numeric = [
                column
                for column in numeric_fields
                if not isinstance(values[column], (int, float))
                or not math.isfinite(values[column])
            ]
            if invalid_numeric:
                raise OpenMeteoObservationError(
                    "Open-Meteo returned invalid daily values for "
                    f"record {index}: {', '.join(invalid_numeric)}."
                )
            try:
                forecast_date = date.fromisoformat(str(values["time"]))
                sunrise = datetime.fromisoformat(str(values["sunrise"]).replace("Z", "+00:00"))
                sunset = datetime.fromisoformat(str(values["sunset"]).replace("Z", "+00:00"))
            except ValueError as exc:
                raise OpenMeteoObservationError(
                    f"Open-Meteo returned an invalid daily date at record {index}."
                ) from exc
            if previous_date is not None and forecast_date - previous_date != timedelta(days=1):
                raise OpenMeteoObservationError("Open-Meteo daily forecasts are not consecutive dates.")
            previous_date = forecast_date
            try:
                forecasts.append(
                    DailyForecast(
                        date=forecast_date,
                        weather_code=int(values["weather_code"]),
                        temperature_max=float(values["temperature_2m_max"]),
                        temperature_min=float(values["temperature_2m_min"]),
                        precipitation_probability=float(values["precipitation_probability_max"]),
                        precipitation_sum=float(values["precipitation_sum"]),
                        sunrise=sunrise,
                        sunset=sunset,
                        daylight_duration_seconds=float(values["daylight_duration"]),
                    )
                )
            except (TypeError, ValueError, ValidationError) as exc:
                raise OpenMeteoObservationError(
                    f"Open-Meteo returned invalid daily values at record {index}."
                ) from exc
        return forecasts

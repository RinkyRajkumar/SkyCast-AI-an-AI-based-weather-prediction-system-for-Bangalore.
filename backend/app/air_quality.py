"""Fetch and summarize current Bengaluru environmental data from Open-Meteo."""

from __future__ import annotations

import logging
import math
import time
from datetime import datetime
from threading import RLock
from typing import Any, Callable
from zoneinfo import ZoneInfo

import httpx

from backend.app import config
from backend.app.locations import default_location
from backend.app.open_meteo import OpenMeteoObservationError
from backend.app.schemas import EnvironmentalInsightsResponse, PollenReading, WeatherLocation

LOGGER = logging.getLogger(__name__)


class OpenMeteoAirQualityService:
    """Provide cached air-quality, dust, and UV summaries for selected places."""

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
        self._cache: dict[tuple[float, float, str], tuple[float, EnvironmentalInsightsResponse]] = {}
        self._lock = RLock()

    def fetch_environment(self, location: WeatherLocation | None = None) -> EnvironmentalInsightsResponse:
        """Return a cached environmental summary or request fresh Open-Meteo data."""
        selected_location = location or default_location()
        cache_key = (
            round(selected_location.latitude, 4),
            round(selected_location.longitude, 4),
            selected_location.timezone,
        )
        with self._lock:
            cached = self._cache.get(cache_key)
            if cached is not None and self._clock() - cached[0] < self.cache_seconds:
                LOGGER.info("Using cached Open-Meteo environmental data for %s", selected_location.label)
                return cached[1].model_copy(deep=True)

            air_payload = self._request_json(
                config.OPEN_METEO_AIR_QUALITY_URL,
                {"current": ",".join(config.OPEN_METEO_AIR_QUALITY_FIELDS)},
                "air-quality",
                selected_location,
            )
            uv_payload = self._request_json(
                config.OPEN_METEO_FORECAST_URL,
                {"current": config.OPEN_METEO_UV_FIELD},
                "UV",
                selected_location,
            )
            try:
                pollen_payload: dict[str, Any] | None = self._request_json(
                    config.OPEN_METEO_AIR_QUALITY_URL,
                    {
                        "hourly": ",".join(config.OPEN_METEO_POLLEN_FIELDS),
                        "forecast_hours": "24",
                    },
                    "pollen",
                    selected_location,
                )
            except OpenMeteoObservationError as exc:
                LOGGER.info("Pollen data unavailable for %s: %s", selected_location.label, exc)
                pollen_payload = None
            response = self._to_environmental_insights(
                air_payload, uv_payload, selected_location, pollen_payload
            )
            self._cache[cache_key] = (self._clock(), response)
            return response.model_copy(deep=True)

    def _request_json(
        self, url: str, request_params: dict[str, str], label: str, location: WeatherLocation
    ) -> dict[str, Any]:
        params = {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "timezone": location.timezone,
            **request_params,
        }
        last_error: Exception | None = None
        for attempt in range(self.retries):
            try:
                response = httpx.get(url, params=params, timeout=config.OPEN_METEO_TIMEOUT_SECONDS)
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise OpenMeteoObservationError(f"Open-Meteo returned invalid {label} data.")
                return payload
            except (httpx.HTTPError, ValueError, OpenMeteoObservationError) as exc:
                last_error = exc
                LOGGER.warning("%s request failed (attempt %d/%d): %s", label.title(), attempt + 1, self.retries, exc)
                if attempt < self.retries - 1:
                    self._sleeper(0.5 * (2**attempt))
        raise OpenMeteoObservationError(f"Unable to fetch {location.label} {label} data from Open-Meteo.") from last_error

    @staticmethod
    def _current_values(
        payload: dict[str, Any], fields: tuple[str, ...], label: str, location: WeatherLocation
    ) -> tuple[datetime, dict[str, float]]:
        current = payload.get("current")
        if not isinstance(current, dict):
            raise OpenMeteoObservationError(f"Open-Meteo response did not contain current {label} data.")
        required = ("time", *fields)
        missing = [field for field in required if current.get(field) is None]
        if missing:
            raise OpenMeteoObservationError(f"Open-Meteo {label} response is missing: {', '.join(missing)}.")
        values = {field: current[field] for field in fields}
        invalid = [field for field, value in values.items() if not isinstance(value, (int, float)) or not math.isfinite(value)]
        if invalid:
            raise OpenMeteoObservationError(f"Open-Meteo {label} response has invalid values: {', '.join(invalid)}.")
        try:
            observed_at = datetime.fromisoformat(str(current["time"]).replace("Z", "+00:00"))
            if observed_at.tzinfo is None:
                observed_at = observed_at.replace(tzinfo=ZoneInfo(location.timezone))
        except ValueError as exc:
            raise OpenMeteoObservationError(f"Open-Meteo returned an invalid {label} timestamp.") from exc
        return observed_at, {field: float(value) for field, value in values.items()}

    @classmethod
    def _to_environmental_insights(
        cls,
        air_payload: dict[str, Any],
        uv_payload: dict[str, Any],
        location: WeatherLocation | None = None,
        pollen_payload: dict[str, Any] | None = None,
    ) -> EnvironmentalInsightsResponse:
        selected_location = location or default_location()
        observed_at, air_values = cls._current_values(
            air_payload, config.OPEN_METEO_AIR_QUALITY_FIELDS, "air-quality", selected_location
        )
        _, uv_values = cls._current_values(uv_payload, (config.OPEN_METEO_UV_FIELD,), "UV", selected_location)

        aqi = round(air_values["us_aqi"])
        if aqi <= 50:
            air_label, air_description = "Good", "Air quality is satisfactory for most people."
        elif aqi <= 100:
            air_label, air_description = "Fair", "Air quality is generally acceptable; sensitive people may notice minor effects."
        elif aqi <= 150:
            air_label, air_description = "Moderate", "Sensitive groups should consider reducing prolonged outdoor exertion."
        else:
            air_label, air_description = "Poor", "Consider limiting extended outdoor activity when possible."

        pm10 = air_values["pm10"]
        if pm10 <= 50:
            dust_outlook, dust_description = "Low", "Outdoor dust exposure is currently low."
        elif pm10 <= 100:
            dust_outlook, dust_description = "Moderate", "Sensitive people may prefer to limit long outdoor exposure."
        else:
            dust_outlook, dust_description = "High", "Elevated outdoor dust may affect sensitive people."

        uv_index = round(uv_values[config.OPEN_METEO_UV_FIELD], 1)
        if uv_index < 3:
            uv_label, uv_description = "Low", "Minimal protection is needed for typical outdoor activity."
        elif uv_index < 6:
            uv_label, uv_description = "Moderate", "Use sunscreen and seek shade around midday."
        elif uv_index < 8:
            uv_label, uv_description = "High", "Use sun protection and reduce prolonged midday exposure."
        elif uv_index < 11:
            uv_label, uv_description = "Very high", "Extra sun protection is recommended; seek shade when possible."
        else:
            uv_label, uv_description = "Extreme", "Avoid extended outdoor exposure around midday."

        pollen_available, pollen_outlook, pollen_description, pollen_readings = cls._pollen_summary(
            pollen_payload, selected_location
        )

        return EnvironmentalInsightsResponse(
            location=selected_location.label,
            source="Open-Meteo",
            observed_at=observed_at,
            us_aqi=aqi,
            pm2_5=air_values["pm2_5"],
            pm10=pm10,
            air_quality_label=air_label,
            air_quality_description=air_description,
            dust_outlook=dust_outlook,
            dust_description=dust_description,
            uv_index=uv_index,
            uv_label=uv_label,
            uv_description=uv_description,
            pollen_available=pollen_available,
            pollen_outlook=pollen_outlook,
            pollen_description=pollen_description,
            pollen_readings=pollen_readings,
        )

    @staticmethod
    def _pollen_summary(
        payload: dict[str, Any] | None, location: WeatherLocation
    ) -> tuple[bool, str, str, list[PollenReading]]:
        """Summarise the next 24 hours without treating missing coverage as a zero reading."""
        hourly = payload.get("hourly") if isinstance(payload, dict) else None
        if not isinstance(hourly, dict):
            return (
                False,
                "Pollen data unavailable",
                f"The live weather provider does not currently supply pollen coverage for {location.name}.",
                [],
            )

        reading_names = {
            "alder_pollen": "Alder",
            "birch_pollen": "Birch",
            "grass_pollen": "Grass",
            "mugwort_pollen": "Mugwort",
            "olive_pollen": "Olive",
            "ragweed_pollen": "Ragweed",
        }
        readings: list[PollenReading] = []
        has_coverage = False
        for field in config.OPEN_METEO_POLLEN_FIELDS:
            values = hourly.get(field)
            if not isinstance(values, list):
                continue
            valid_values = [
                float(value)
                for value in values
                if isinstance(value, (int, float)) and math.isfinite(value) and value >= 0
            ]
            if not valid_values:
                continue
            has_coverage = True
            peak = max(valid_values)
            if peak > 0:
                readings.append(PollenReading(pollen_type=reading_names[field], concentration=round(peak, 1)))

        if not has_coverage:
            return (
                False,
                "Pollen data unavailable",
                f"The live weather provider does not currently supply pollen coverage for {location.name}.",
                [],
            )
        readings.sort(key=lambda reading: reading.concentration, reverse=True)
        if not readings:
            return (
                True,
                "No listed pollen detected",
                "No listed pollen types are forecast over the next 24 hours by the live weather provider.",
                [],
            )
        names = ", ".join(reading.pollen_type.lower() for reading in readings)
        return (
            True,
            "Pollen present",
            f"{names.capitalize()} pollen is forecast over the next 24 hours. This may affect people sensitive to those pollen types.",
            readings,
        )

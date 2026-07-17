"""Fetch and summarize current Bengaluru environmental data from Open-Meteo."""

from __future__ import annotations

import logging
import math
import time
from datetime import datetime
from threading import RLock
from typing import Any, Callable

import httpx

from backend.app import config
from backend.app.open_meteo import OpenMeteoObservationError
from backend.app.schemas import EnvironmentalInsightsResponse

LOGGER = logging.getLogger(__name__)


class OpenMeteoAirQualityService:
    """Provide a one-hour cached air-quality, dust, and UV summary."""

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
        self._cache: EnvironmentalInsightsResponse | None = None
        self._cached_at = 0.0
        self._lock = RLock()

    def fetch_environment(self) -> EnvironmentalInsightsResponse:
        """Return a cached environmental summary or request fresh Open-Meteo data."""
        with self._lock:
            if self._cache is not None and self._clock() - self._cached_at < self.cache_seconds:
                LOGGER.info("Using cached Open-Meteo environmental data")
                return self._cache.model_copy(deep=True)

            air_payload = self._request_json(
                config.OPEN_METEO_AIR_QUALITY_URL,
                {"current": ",".join(config.OPEN_METEO_AIR_QUALITY_FIELDS)},
                "air-quality",
            )
            uv_payload = self._request_json(
                config.OPEN_METEO_FORECAST_URL,
                {"current": config.OPEN_METEO_UV_FIELD},
                "UV",
            )
            response = self._to_environmental_insights(air_payload, uv_payload)
            self._cache = response
            self._cached_at = self._clock()
            return response.model_copy(deep=True)

    def _request_json(self, url: str, request_params: dict[str, str], label: str) -> dict[str, Any]:
        params = {
            "latitude": config.OPEN_METEO_LATITUDE,
            "longitude": config.OPEN_METEO_LONGITUDE,
            "timezone": config.TIMEZONE,
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
        raise OpenMeteoObservationError(f"Unable to fetch Bengaluru {label} data from Open-Meteo.") from last_error

    @staticmethod
    def _current_values(payload: dict[str, Any], fields: tuple[str, ...], label: str) -> tuple[datetime, dict[str, float]]:
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
        except ValueError as exc:
            raise OpenMeteoObservationError(f"Open-Meteo returned an invalid {label} timestamp.") from exc
        return observed_at, {field: float(value) for field, value in values.items()}

    @classmethod
    def _to_environmental_insights(
        cls, air_payload: dict[str, Any], uv_payload: dict[str, Any]
    ) -> EnvironmentalInsightsResponse:
        observed_at, air_values = cls._current_values(air_payload, config.OPEN_METEO_AIR_QUALITY_FIELDS, "air-quality")
        _, uv_values = cls._current_values(uv_payload, (config.OPEN_METEO_UV_FIELD,), "UV")

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

        return EnvironmentalInsightsResponse(
            location=config.DISPLAY_LOCATION,
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
        )

"""Resolve searched places to safe Open-Meteo location parameters."""

from __future__ import annotations

import logging
import time
from threading import RLock
from typing import Any, Callable

import httpx

from backend.app import config
from backend.app.schemas import LocationSearchResponse, WeatherLocation

LOGGER = logging.getLogger(__name__)


class LocationSearchError(RuntimeError):
    """Raised when a location search cannot return usable results."""


def default_location() -> WeatherLocation:
    """Return SkyCast's model-supported default location."""
    return WeatherLocation(
        name=config.DEFAULT_LOCATION_NAME,
        country="India",
        latitude=config.OPEN_METEO_LATITUDE,
        longitude=config.OPEN_METEO_LONGITUDE,
        timezone=config.TIMEZONE,
    )


class OpenMeteoLocationSearchService:
    """Search Open-Meteo's geocoding service with bounded caching and retries."""

    def __init__(
        self,
        *,
        cache_seconds: int = config.LOCATION_SEARCH_CACHE_SECONDS,
        retries: int = config.OPEN_METEO_RETRIES,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self.cache_seconds = cache_seconds
        self.retries = retries
        self._clock = clock
        self._sleeper = sleeper
        self._cache: dict[str, tuple[float, LocationSearchResponse]] = {}
        self._lock = RLock()

    def search(self, query: str) -> LocationSearchResponse:
        """Return matching locations for a normalised city or place-name query."""
        normalised = " ".join(query.split())
        if len(normalised) < 2:
            raise LocationSearchError("Enter at least two characters to search for a location.")
        if len(normalised) > 120:
            raise LocationSearchError("The location search is too long.")
        cache_key = normalised.casefold()
        with self._lock:
            cached = self._cache.get(cache_key)
            if cached and self._clock() - cached[0] < self.cache_seconds:
                return cached[1].model_copy(deep=True)
            response = self._request(normalised)
            self._cache[cache_key] = (self._clock(), response)
            return response.model_copy(deep=True)

    def _request(self, query: str) -> LocationSearchResponse:
        last_error: Exception | None = None
        for attempt in range(self.retries):
            try:
                response = httpx.get(
                    config.OPEN_METEO_GEOCODING_URL,
                    params={"name": query, "count": config.LOCATION_SEARCH_MAX_RESULTS, "language": "en", "format": "json"},
                    timeout=config.OPEN_METEO_TIMEOUT_SECONDS,
                )
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise LocationSearchError("The location service returned invalid data.")
                results = self._parse_results(payload)
                return LocationSearchResponse(query=query, results=results)
            except (httpx.HTTPError, ValueError, LocationSearchError) as exc:
                last_error = exc
                LOGGER.warning("Location search failed (attempt %d/%d): %s", attempt + 1, self.retries, exc)
                if attempt < self.retries - 1:
                    self._sleeper(0.5 * (2**attempt))
        raise LocationSearchError("Unable to search for locations right now. Please try again shortly.") from last_error

    @staticmethod
    def _parse_results(payload: dict[str, Any]) -> list[WeatherLocation]:
        raw_results = payload.get("results")
        if raw_results is None:
            return []
        if not isinstance(raw_results, list):
            raise LocationSearchError("The location service returned invalid search results.")
        results: list[WeatherLocation] = []
        for raw in raw_results:
            if not isinstance(raw, dict):
                continue
            try:
                results.append(
                    WeatherLocation(
                        name=raw["name"],
                        country=raw.get("country"),
                        admin1=raw.get("admin1"),
                        latitude=raw["latitude"],
                        longitude=raw["longitude"],
                        timezone=raw["timezone"],
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue
        return results

"""Collect hourly historical weather observations for Bangalore."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from datetime import date
from typing import Any

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src import config

LOGGER = logging.getLogger(__name__)


class WeatherDataError(RuntimeError):
    """Raised when Open-Meteo returns unusable historical weather data."""


def create_session() -> requests.Session:
    """Create an HTTP session with exponential-backoff retries."""
    retry = Retry(
        total=config.MAX_RETRIES,
        connect=config.MAX_RETRIES,
        read=config.MAX_RETRIES,
        status=config.MAX_RETRIES,
        backoff_factor=config.BACKOFF_FACTOR,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def iter_year_ranges(start_date: str, end_date: str) -> Iterator[tuple[str, str]]:
    """Yield inclusive, year-sized date ranges between two ISO dates."""
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    if start > end:
        raise ValueError("start_date must not be after end_date")

    for year in range(start.year, end.year + 1):
        chunk_start = max(start, date(year, 1, 1))
        chunk_end = min(end, date(year, 12, 31))
        yield chunk_start.isoformat(), chunk_end.isoformat()


def response_to_dataframe(payload: dict[str, Any]) -> pd.DataFrame:
    """Validate an Open-Meteo JSON payload and convert its hourly data to a DataFrame."""
    if payload.get("error"):
        raise WeatherDataError(str(payload.get("reason", "Open-Meteo returned an error")))

    hourly = payload.get("hourly")
    if not isinstance(hourly, dict):
        raise WeatherDataError("API response does not contain an 'hourly' object")

    expected = ("time", *config.HOURLY_VARIABLES)
    missing = [column for column in expected if column not in hourly]
    if missing:
        raise WeatherDataError(f"API response is missing hourly fields: {missing}")

    lengths = {column: len(hourly[column]) for column in expected if isinstance(hourly[column], list)}
    if len(lengths) != len(expected) or len(set(lengths.values())) != 1:
        raise WeatherDataError("Hourly fields are not lists of equal length")
    if not lengths or next(iter(lengths.values())) == 0:
        raise WeatherDataError("API response contains no hourly records")

    return pd.DataFrame({column: hourly[column] for column in expected})


def fetch_date_range(session: requests.Session, start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch and validate one inclusive date range from Open-Meteo."""
    params = {
        "latitude": config.LATITUDE,
        "longitude": config.LONGITUDE,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(config.HOURLY_VARIABLES),
        "timezone": config.TIMEZONE,
    }
    LOGGER.info("Requesting weather data from %s to %s", start_date, end_date)
    try:
        response = session.get(config.API_URL, params=params, timeout=config.REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise WeatherDataError(f"Open-Meteo request failed for {start_date} to {end_date}: {exc}") from exc

    try:
        payload = response.json()
    except requests.exceptions.JSONDecodeError as exc:
        raise WeatherDataError("Open-Meteo returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise WeatherDataError("Open-Meteo returned an unexpected JSON structure")
    return response_to_dataframe(payload)


def collect_weather_data() -> pd.DataFrame:
    """Download all configured years, save the raw CSV, and return the dataset."""
    frames: list[pd.DataFrame] = []
    with create_session() as session:
        for start_date, end_date in iter_year_ranges(config.START_DATE, config.END_DATE):
            frames.append(fetch_date_range(session, start_date, end_date))

    data = pd.concat(frames, ignore_index=True)
    config.RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    data.to_csv(config.RAW_DATA_FILE, index=False)

    parsed_time = pd.to_datetime(data["time"], errors="coerce")
    LOGGER.info("Saved raw data to %s", config.RAW_DATA_FILE)
    LOGGER.info("Rows collected: %d", len(data))
    LOGGER.info("Date range: %s to %s", parsed_time.min(), parsed_time.max())
    LOGGER.info("Missing values by column:\n%s", data.isna().sum().to_string())
    return data


def main() -> int:
    """Run the collection command and return a process exit code."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    try:
        collect_weather_data()
    except (WeatherDataError, OSError, ValueError) as exc:
        LOGGER.error("Collection failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

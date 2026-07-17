"""Tests for the SkyCast AI data-cleaning pipeline."""

import pandas as pd

from src import config
from src.clean_data import clean_weather_data


def make_weather_data(times: list[str], precipitation: list[object] | None = None) -> pd.DataFrame:
    """Build a minimal, valid raw weather frame for cleaning tests."""
    row_count = len(times)
    values: dict[str, list[object]] = {
        "time": times,
        "temperature_2m": [20.0] * row_count,
        "relative_humidity_2m": [70.0] * row_count,
        "precipitation": precipitation if precipitation is not None else [0.0] * row_count,
        "rain": [0.0] * row_count,
        "surface_pressure": [920.0] * row_count,
        "cloud_cover": [50.0] * row_count,
        "wind_speed_10m": [10.0] * row_count,
        "wind_direction_10m": [180.0] * row_count,
    }
    return pd.DataFrame(values, columns=["time", *config.HOURLY_VARIABLES])


def test_datetime_parsing() -> None:
    raw = make_weather_data(["2025-01-01T00:00", "2025-01-01T01:00"])
    cleaned, _ = clean_weather_data(raw)
    assert pd.api.types.is_datetime64_any_dtype(cleaned["time"])


def test_duplicate_removal_keeps_one_timestamp() -> None:
    raw = make_weather_data(["2025-01-01T00:00", "2025-01-01T00:00"])
    cleaned, report = clean_weather_data(raw)
    assert len(cleaned) == 1
    assert report["duplicate_timestamps_removed"] == 1


def test_rain_occurrence_creation() -> None:
    raw = make_weather_data(
        ["2025-01-01T00:00", "2025-01-01T01:00", "2025-01-01T02:00"],
        precipitation=[0, 0.1, "2.5"],
    )
    cleaned, _ = clean_weather_data(raw)
    assert cleaned["rain_occurrence"].tolist() == [0, 1, 1]


def test_small_gap_is_time_interpolated() -> None:
    times = pd.date_range("2025-01-01", periods=5, freq="h").strftime("%Y-%m-%dT%H:%M").tolist()
    raw = make_weather_data(times)
    raw["temperature_2m"] = [10.0, None, None, None, 18.0]
    cleaned, _ = clean_weather_data(raw)
    assert cleaned["temperature_2m"].tolist() == [10.0, 12.0, 14.0, 16.0, 18.0]


def test_large_missing_gap_is_preserved() -> None:
    times = pd.date_range("2025-01-01", periods=6, freq="h").strftime("%Y-%m-%dT%H:%M").tolist()
    raw = make_weather_data(times)
    raw["temperature_2m"] = [10.0, None, None, None, None, 20.0]
    cleaned, _ = clean_weather_data(raw)
    assert cleaned["temperature_2m"].iloc[1:5].isna().all()

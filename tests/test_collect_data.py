"""Tests for API-response validation helpers."""

import pytest

from src import config
from src.collect_data import WeatherDataError, response_to_dataframe


def test_valid_response_is_converted() -> None:
    hourly = {"time": ["2025-01-01T00:00"]}
    hourly.update({variable: [1.0] for variable in config.HOURLY_VARIABLES})
    frame = response_to_dataframe({"hourly": hourly})
    assert frame.columns.tolist() == ["time", *config.HOURLY_VARIABLES]


def test_invalid_response_is_rejected() -> None:
    with pytest.raises(WeatherDataError):
        response_to_dataframe({"error": True, "reason": "bad request"})

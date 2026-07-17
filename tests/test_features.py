"""Tests for leakage-safe feature engineering."""

import numpy as np
import pandas as pd

from src.features import create_features


def sample_clean_data(periods: int = 200, start: str = "2015-01-01") -> pd.DataFrame:
    """Create deterministic hourly observations for feature tests."""
    values = np.arange(periods, dtype=float)
    return pd.DataFrame(
        {
            "time": pd.date_range(start, periods=periods, freq="h"),
            "temperature_2m": values,
            "relative_humidity_2m": 50.0 + values,
            "precipitation": np.ones(periods),
            "rain": np.ones(periods),
            "surface_pressure": 900.0 + values,
            "cloud_cover": np.zeros(periods),
            "wind_speed_10m": np.ones(periods),
            "wind_direction_10m": np.zeros(periods),
            "rain_occurrence": np.ones(periods),
        }
    )


def test_lags_and_targets_are_correct() -> None:
    features = create_features(sample_clean_data())
    row = features.iloc[168]
    assert row["temperature_lag_1h"] == 167.0
    assert row["temperature_lag_24h"] == 144.0
    assert row["temperature_lag_168h"] == 0.0
    assert row["temperature_target_1h"] == 169.0
    assert row["temperature_target_24h"] == 192.0
    assert row["previous_day_temperature_1h"] == 145.0
    assert row["previous_day_temperature_6h"] == 150.0
    assert row["previous_day_temperature_12h"] == 156.0
    assert row["previous_day_temperature_24h"] == 168.0


def test_rolling_features_use_past_values_only() -> None:
    features = create_features(sample_clean_data())
    row = features.iloc[24]
    assert row["temperature_mean_3h"] == np.mean([21.0, 22.0, 23.0])
    assert row["temperature_mean_24h"] == np.mean(np.arange(24, dtype=float))
    assert row["humidity_mean_24h"] == np.mean(50.0 + np.arange(24, dtype=float))
    assert row["pressure_mean_24h"] == np.mean(900.0 + np.arange(24, dtype=float))
    assert row["precipitation_sum_6h"] == 6.0
    assert row["precipitation_sum_24h"] == 24.0

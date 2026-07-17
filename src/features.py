"""Create leakage-safe time-series features and temperature targets."""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from src import config

LOGGER = logging.getLogger(__name__)


def create_features(clean_data: pd.DataFrame) -> pd.DataFrame:
    """Return chronologically ordered weather data with features and future targets."""
    required = {
        "time",
        config.TEMPERATURE_COLUMN,
        "relative_humidity_2m",
        "surface_pressure",
        "precipitation",
    }
    missing = required.difference(clean_data.columns)
    if missing:
        raise ValueError(f"Clean data is missing required columns: {sorted(missing)}")

    data = clean_data.copy()
    data["time"] = pd.to_datetime(data["time"], errors="coerce")
    if data["time"].isna().any():
        raise ValueError("Feature input contains invalid timestamps")
    data = data.sort_values("time").drop_duplicates(subset="time", keep="first").reset_index(drop=True)

    data["hour"] = data["time"].dt.hour
    data["day_of_week"] = data["time"].dt.dayofweek
    data["day_of_year"] = data["time"].dt.dayofyear
    data["month"] = data["time"].dt.month
    data["hour_sin"] = np.sin(2 * np.pi * data["hour"] / 24)
    data["hour_cos"] = np.cos(2 * np.pi * data["hour"] / 24)
    data["day_of_year_sin"] = np.sin(2 * np.pi * data["day_of_year"] / 365.25)
    data["day_of_year_cos"] = np.cos(2 * np.pi * data["day_of_year"] / 365.25)

    temperature = data[config.TEMPERATURE_COLUMN]
    for lag in config.TEMPERATURE_LAGS:
        data[f"temperature_lag_{lag}h"] = temperature.shift(lag)

    for horizon in config.FORECAST_HORIZONS:
        previous_day_offset = 24 - horizon
        data[f"previous_day_temperature_{horizon}h"] = temperature.shift(previous_day_offset)

    past_temperature = temperature.shift(1)
    for window in (3, 6, 24, 168):
        data[f"temperature_mean_{window}h"] = past_temperature.rolling(window, min_periods=window).mean()
    data["temperature_std_24h"] = past_temperature.rolling(24, min_periods=24).std()
    data["humidity_mean_24h"] = (
        data["relative_humidity_2m"].shift(1).rolling(24, min_periods=24).mean()
    )
    data["pressure_mean_24h"] = data["surface_pressure"].shift(1).rolling(24, min_periods=24).mean()
    for window in (6, 24):
        data[f"precipitation_sum_{window}h"] = (
            data["precipitation"].shift(1).rolling(window, min_periods=window).sum()
        )

    for horizon in config.FORECAST_HORIZONS:
        data[f"temperature_target_{horizon}h"] = temperature.shift(-horizon)
    return data


def run_feature_engineering() -> pd.DataFrame:
    """Load cleaned weather data, create features, and save the feature dataset."""
    if not config.PROCESSED_DATA_FILE.exists():
        raise FileNotFoundError(
            f"Clean data not found: {config.PROCESSED_DATA_FILE}. Run python -m src.clean_data first."
        )
    clean_data = pd.read_csv(config.PROCESSED_DATA_FILE)
    features = create_features(clean_data)
    config.PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    features.to_csv(config.FEATURE_DATA_FILE, index=False)
    LOGGER.info("Saved %d feature rows and %d columns to %s", len(features), len(features.columns), config.FEATURE_DATA_FILE)
    LOGGER.info("Feature date range: %s to %s", features["time"].min(), features["time"].max())
    return features


def main() -> int:
    """Run feature engineering and return a process exit code."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    try:
        run_feature_engineering()
    except (FileNotFoundError, OSError, ValueError) as exc:
        LOGGER.error("Feature engineering failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

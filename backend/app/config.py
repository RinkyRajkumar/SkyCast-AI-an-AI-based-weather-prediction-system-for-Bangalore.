"""Configuration for the SkyCast AI FastAPI backend."""

from __future__ import annotations

import os
from pathlib import Path

from src import config as pipeline_config

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOCATION = "Bangalore"
DISPLAY_LOCATION = "Bengaluru, India"
TIMEZONE = pipeline_config.TIMEZONE
FORECAST_HORIZONS = pipeline_config.FORECAST_HORIZONS
MINIMUM_OBSERVATIONS = max(pipeline_config.TEMPERATURE_LAGS) + 1

MODELS_ROOT = Path(
    os.getenv("SKYCAST_MODELS_ROOT", str(pipeline_config.MODELS_DIR.parent))
).resolve()
REPORTS_ROOT = Path(
    os.getenv("SKYCAST_REPORTS_ROOT", str(pipeline_config.REPORTS_DIR))
).resolve()
ADVANCED_METRICS_FILE = REPORTS_ROOT / "advanced_model_metrics.json"
RAIN_METRICS_FILE = REPORTS_ROOT / "rain_model_metrics.json"
ADVANCED_MODELS_DIR = MODELS_ROOT / "advanced"
BASELINE_MODELS_DIR = MODELS_ROOT / "baselines"
RAIN_MODELS_DIR = MODELS_ROOT / "rain"

DEFAULT_TEMPERATURE_MODELS = {
    1: "random_forest",
    6: "random_forest",
    12: "random_forest",
    24: "hist_gradient_boosting",
}
DEFAULT_RAIN_CLASSIFIERS = {
    1: "hist_gradient_boosting_classifier",
    6: "hist_gradient_boosting_classifier",
    12: "hist_gradient_boosting_classifier",
    24: "random_forest_classifier",
}
DEFAULT_RAINFALL_MODELS = {
    horizon: "hist_gradient_boosting_regressor" for horizon in FORECAST_HORIZONS
}

DEFAULT_CORS_ORIGINS = (
    "http://localhost:3000,http://localhost:5173,"
    "http://127.0.0.1:3000,http://127.0.0.1:5173"
)
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("SKYCAST_CORS_ORIGINS", DEFAULT_CORS_ORIGINS).split(",")
    if origin.strip()
]
CORS_ORIGIN_REGEX = os.getenv("SKYCAST_CORS_ORIGIN_REGEX") or None
CORS_ALLOW_CREDENTIALS = os.getenv(
    "SKYCAST_CORS_ALLOW_CREDENTIALS", "false"
).lower() in {"1", "true", "yes"}

OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
OPEN_METEO_LATITUDE = 12.9716
OPEN_METEO_LONGITUDE = 77.5946
OPEN_METEO_PAST_HOURS = 168
OPEN_METEO_FORECAST_HOURS = 24
OPEN_METEO_HOURLY_FORECAST_COUNT = 24
OPEN_METEO_FORECAST_DAYS = 6
OPEN_METEO_CACHE_SECONDS = 60 * 60
OPEN_METEO_TIMEOUT_SECONDS = float(os.getenv("SKYCAST_OPEN_METEO_TIMEOUT_SECONDS", "15"))
OPEN_METEO_RETRIES = 3
OPEN_METEO_HOURLY_FIELDS = (
    "temperature_2m",
    "relative_humidity_2m",
    "dew_point_2m",
    "apparent_temperature",
    "precipitation",
    "rain",
    "pressure_msl",
    "surface_pressure",
    "cloud_cover",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
    "weather_code",
    "precipitation_probability",
)
OPEN_METEO_DAILY_FIELDS = (
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_probability_max",
    "precipitation_sum",
    "sunrise",
    "sunset",
    "daylight_duration",
)
OPEN_METEO_AIR_QUALITY_FIELDS = ("us_aqi", "pm2_5", "pm10")
OPEN_METEO_UV_FIELD = "uv_index"

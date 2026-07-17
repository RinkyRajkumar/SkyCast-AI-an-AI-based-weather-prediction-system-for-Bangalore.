"""Central configuration for the SkyCast AI data pipeline."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

LATITUDE = 12.9716
LONGITUDE = 77.5946
START_DATE = "2015-01-01"
END_DATE = "2025-12-31"
TIMEZONE = "Asia/Kolkata"

API_URL = "https://archive-api.open-meteo.com/v1/archive"
HOURLY_VARIABLES = (
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "rain",
    "surface_pressure",
    "cloud_cover",
    "wind_speed_10m",
    "wind_direction_10m",
)

RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
RAW_DATA_FILE = RAW_DATA_DIR / "bangalore_hourly_weather_2015_2025.csv"
PROCESSED_DATA_FILE = PROCESSED_DATA_DIR / "bangalore_weather_clean.csv"
FEATURE_DATA_FILE = PROCESSED_DATA_DIR / "bangalore_weather_features.csv"

MODELS_DIR = PROJECT_ROOT / "models" / "baselines"
ADVANCED_MODELS_DIR = PROJECT_ROOT / "models" / "advanced"
RAIN_MODELS_DIR = PROJECT_ROOT / "models" / "rain"
REPORTS_DIR = PROJECT_ROOT / "reports"
BASELINE_METRICS_FILE = REPORTS_DIR / "baseline_metrics.json"
ADVANCED_METRICS_FILE = REPORTS_DIR / "advanced_model_metrics.json"
RAIN_METRICS_FILE = REPORTS_DIR / "rain_model_metrics.json"
FIGURES_DIR = REPORTS_DIR / "figures"

TEMPERATURE_COLUMN = "temperature_2m"
FORECAST_HORIZONS = (1, 6, 12, 24)
TEMPERATURE_LAGS = (1, 3, 6, 12, 24, 48, 168)
TRAIN_END = "2022-12-31 23:59:59"
VALIDATION_START = "2023-01-01"
VALIDATION_END = "2024-12-31 23:59:59"
TEST_START = "2025-01-01"
TEST_END = "2025-12-31 23:59:59"

REQUEST_TIMEOUT = (10, 120)
MAX_RETRIES = 5
BACKOFF_FACTOR = 1.0

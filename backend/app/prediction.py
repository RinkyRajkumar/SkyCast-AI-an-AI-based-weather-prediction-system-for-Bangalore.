"""Convert recent observations into training-compatible features and forecasts."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Protocol

import numpy as np
import pandas as pd

from backend.app import config
from backend.app.schemas import Forecast, PredictionRequest, PredictionResponse
from src.features import create_features

LOGGER = logging.getLogger(__name__)


class RegistryProtocol(Protocol):
    """Minimal model-registry interface required by prediction."""

    def get_artifact(self, task: str, horizon: int) -> dict[str, Any]: ...


class PredictionInputError(ValueError):
    """Raised when observations cannot form the required hourly history."""


class ModelPredictionError(RuntimeError):
    """Raised when a loaded model cannot produce a valid forecast."""


def _local_naive_timestamp(value: datetime) -> pd.Timestamp:
    """Normalize aware timestamps to Bangalore time and treat naive values as local time."""
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is not None:
        timestamp = timestamp.tz_convert(config.TIMEZONE).tz_localize(None)
    return timestamp


def observations_to_features(request: PredictionRequest) -> pd.DataFrame:
    """Build the same latest feature row used by model training."""
    if len(request.observations) < config.MINIMUM_OBSERVATIONS:
        raise PredictionInputError(
            f"At least {config.MINIMUM_OBSERVATIONS} hourly observations are required; "
            f"received {len(request.observations)}."
        )

    records = []
    for observation in request.observations:
        records.append(
            {
                "time": _local_naive_timestamp(observation.timestamp),
                "temperature_2m": observation.temperature,
                "relative_humidity_2m": observation.relative_humidity,
                "precipitation": observation.precipitation,
                "rain": observation.precipitation,
                "surface_pressure": observation.surface_pressure,
                "cloud_cover": observation.cloud_cover,
                "wind_speed_10m": observation.wind_speed,
                "wind_direction_10m": observation.wind_direction,
                "rain_occurrence": int(observation.precipitation > 0),
            }
        )
    weather = pd.DataFrame.from_records(records).sort_values("time").reset_index(drop=True)
    if weather["time"].duplicated().any():
        raise PredictionInputError("Observation timestamps must be unique.")
    gaps = weather["time"].diff().dropna()
    if not gaps.eq(pd.Timedelta(hours=1)).all():
        raise PredictionInputError("Observations must be contiguous and exactly one hour apart.")

    features = create_features(weather)
    latest = features.tail(1)
    if latest.empty:
        raise PredictionInputError("No usable feature row could be created from the observations.")
    return latest


def _predict_regression(artifact: dict[str, Any], features: pd.DataFrame) -> float:
    columns = artifact["feature_columns"]
    missing = sorted(set(columns).difference(features.columns))
    if missing:
        raise ModelPredictionError(f"Required model features are missing: {missing}")
    value = float(artifact["model"].predict(features[columns])[0])
    if not np.isfinite(value):
        raise ModelPredictionError("Model returned a non-finite regression prediction")
    return value


def _predict_probability(artifact: dict[str, Any], features: pd.DataFrame) -> float:
    columns = artifact["feature_columns"]
    missing = sorted(set(columns).difference(features.columns))
    if missing:
        raise ModelPredictionError(f"Required classifier features are missing: {missing}")
    probability = float(artifact["model"].predict_proba(features[columns])[0, 1])
    if not np.isfinite(probability):
        raise ModelPredictionError("Model returned a non-finite rain probability")
    return float(np.clip(probability, 0.0, 1.0))


def generate_prediction(
    request: PredictionRequest, registry: RegistryProtocol
) -> PredictionResponse:
    """Generate temperature, rain probability, and rainfall forecasts for all horizons."""
    latest_features = observations_to_features(request)
    forecasts: list[Forecast] = []
    try:
        for horizon in config.FORECAST_HORIZONS:
            temperature_artifact = registry.get_artifact("temperature", horizon)
            rain_artifact = registry.get_artifact("rain_probability", horizon)
            amount_artifact = registry.get_artifact("rainfall_amount", horizon)
            temperature = _predict_regression(temperature_artifact, latest_features)
            rain_probability = _predict_probability(rain_artifact, latest_features)
            rainfall = max(_predict_regression(amount_artifact, latest_features), 0.0)
            threshold = float(rain_artifact.get("threshold", 0.5))
            forecasts.append(
                Forecast(
                    horizon_hours=horizon,
                    temperature_c=round(temperature, 2),
                    rain_probability=round(rain_probability, 4),
                    rain_expected=rain_probability >= threshold,
                    rainfall_mm=round(rainfall, 3),
                )
            )
    except ModelPredictionError:
        raise
    except Exception as exc:
        raise ModelPredictionError(f"A model prediction failed: {exc}") from exc

    LOGGER.info("Generated %d Bangalore forecast horizons", len(forecasts))
    return PredictionResponse(
        location=config.LOCATION,
        generated_at=datetime.now(timezone.utc),
        forecasts=forecasts,
    )

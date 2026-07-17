"""Pydantic request and response schemas for SkyCast AI."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class WeatherObservation(BaseModel):
    """One hourly weather observation in Bangalore local time or an offset-aware time."""

    timestamp: datetime
    temperature: float = Field(ge=-80, le=60)
    relative_humidity: float = Field(ge=0, le=100)
    precipitation: float = Field(ge=0)
    surface_pressure: float = Field(gt=0)
    cloud_cover: float = Field(ge=0, le=100)
    wind_speed: float = Field(ge=0)
    wind_direction: float = Field(ge=0, le=360)


class PredictionRequest(BaseModel):
    """A chronological history used to construct the latest model feature row."""

    observations: list[WeatherObservation] = Field(min_length=1)


class Forecast(BaseModel):
    """Temperature and rain predictions for one forecast horizon."""

    horizon_hours: int
    temperature_c: float
    rain_probability: float
    rain_expected: bool
    rainfall_mm: float


class PredictionResponse(BaseModel):
    """Complete Bangalore forecast response."""

    location: str
    generated_at: datetime
    forecasts: list[Forecast]


class HealthResponse(BaseModel):
    """Service health and lazy model-loading state."""

    status: str
    location: str
    models_loaded: bool


class ModelInfo(BaseModel):
    """One selected model exposed by the model registry."""

    task: str
    horizon_hours: int
    model_name: str
    artifact: str


class ModelsResponse(BaseModel):
    """Description of all models selected for API inference."""

    location: str
    models: list[ModelInfo]


class ObservationHistoryResponse(BaseModel):
    """Recent Open-Meteo observations converted to SkyCast prediction inputs."""

    location: str
    source: str
    latest_timestamp: datetime
    observations: list[WeatherObservation] = Field(min_length=1)
    hourly_forecasts: list["HourlyForecast"] = Field(min_length=1)
    daily_forecasts: list["DailyForecast"] = Field(min_length=1)


class HourlyForecast(BaseModel):
    """One near-term Open-Meteo hourly outlook for the dashboard."""

    timestamp: datetime
    temperature: float = Field(ge=-80, le=60)
    precipitation_probability: float = Field(ge=0, le=100)
    weather_code: int = Field(ge=0)


class DailyForecast(BaseModel):
    """One Open-Meteo daily outlook used by the six-day dashboard list."""

    date: date
    weather_code: int = Field(ge=0)
    temperature_max: float = Field(ge=-80, le=60)
    temperature_min: float = Field(ge=-80, le=60)
    precipitation_probability: float = Field(ge=0, le=100)
    precipitation_sum: float = Field(ge=0)
    sunrise: datetime
    sunset: datetime
    daylight_duration_seconds: float = Field(ge=0)


class EnvironmentalInsightsResponse(BaseModel):
    """Current air-quality and outdoor dust guidance for the dashboard."""

    location: str
    source: str
    observed_at: datetime
    us_aqi: int = Field(ge=0)
    pm2_5: float = Field(ge=0)
    pm10: float = Field(ge=0)
    air_quality_label: str
    air_quality_description: str
    dust_outlook: str
    dust_description: str
    uv_index: float = Field(ge=0)
    uv_label: str
    uv_description: str

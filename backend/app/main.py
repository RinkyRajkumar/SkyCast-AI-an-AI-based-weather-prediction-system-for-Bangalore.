"""FastAPI application for SkyCast AI model inference."""

from __future__ import annotations

import logging

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from backend.app import config
from backend.app.air_quality import OpenMeteoAirQualityService
from backend.app.climate_news import ClimateNewsError, ClimateNewsService
from backend.app.locations import LocationSearchError, OpenMeteoLocationSearchService
from backend.app.model_loader import ModelLoadError, ModelRegistry
from backend.app.open_meteo import OpenMeteoObservationError, OpenMeteoObservationService
from backend.app.prediction import ModelPredictionError, PredictionInputError, generate_prediction
from backend.app.schemas import (
    HealthResponse,
    EnvironmentalInsightsResponse,
    ClimateNewsResponse,
    LocationSearchResponse,
    ModelsResponse,
    ObservationHistoryResponse,
    PredictionRequest,
    PredictionResponse,
    WeatherLocation,
)

LOGGER = logging.getLogger(__name__)


def get_registry(request: Request) -> ModelRegistry:
    """Resolve and load the app-scoped model registry."""
    registry: ModelRegistry = request.app.state.model_registry
    try:
        registry.load_all()
    except ModelLoadError as exc:
        LOGGER.error("Model loading failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Model loading failed: {exc}",
        ) from exc
    return registry


def get_observation_service(request: Request) -> OpenMeteoObservationService:
    """Resolve the app-scoped Open-Meteo observation service."""
    return request.app.state.observation_service


def get_air_quality_service(request: Request) -> OpenMeteoAirQualityService:
    """Resolve the app-scoped Open-Meteo air-quality service."""
    return request.app.state.air_quality_service


def get_climate_news_service(request: Request) -> ClimateNewsService:
    """Resolve the app-scoped climate and weather news service."""
    return request.app.state.climate_news_service


def get_location_search_service(request: Request) -> OpenMeteoLocationSearchService:
    """Resolve the app-scoped Open-Meteo location-search service."""
    return request.app.state.location_search_service


def get_requested_location(
    name: str = Query(default=config.DEFAULT_LOCATION_NAME, min_length=1, max_length=120),
    latitude: float = Query(default=config.OPEN_METEO_LATITUDE, ge=-90, le=90),
    longitude: float = Query(default=config.OPEN_METEO_LONGITUDE, ge=-180, le=180),
    timezone: str = Query(default=config.TIMEZONE, min_length=1, max_length=64),
    country: str | None = Query(default="India", max_length=120),
    admin1: str | None = Query(default=None, max_length=120),
) -> WeatherLocation:
    """Validate a searched location before requesting any external weather data."""
    try:
        return WeatherLocation(
            name=name,
            latitude=latitude,
            longitude=longitude,
            timezone=timezone,
            country=country,
            admin1=admin1,
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The selected location has an invalid timezone.",
        ) from exc


def create_app(
    model_registry: ModelRegistry | None = None,
    observation_service: OpenMeteoObservationService | None = None,
    air_quality_service: OpenMeteoAirQualityService | None = None,
    climate_news_service: ClimateNewsService | None = None,
    location_search_service: OpenMeteoLocationSearchService | None = None,
) -> FastAPI:
    """Create the API app, optionally with an injected registry for tests."""
    application = FastAPI(
        title="SkyCast AI API",
        version="1.0.0",
        description="Temperature and rain forecasts for Bangalore",
    )
    application.state.model_registry = model_registry or ModelRegistry()
    application.state.observation_service = observation_service or OpenMeteoObservationService()
    application.state.air_quality_service = air_quality_service or OpenMeteoAirQualityService()
    application.state.climate_news_service = climate_news_service or ClimateNewsService()
    application.state.location_search_service = location_search_service or OpenMeteoLocationSearchService()
    application.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS,
        allow_origin_regex=config.CORS_ORIGIN_REGEX,
        allow_credentials=config.CORS_ALLOW_CREDENTIALS,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    @application.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        registry = application.state.model_registry
        return HealthResponse(
            status="ok", location=config.LOCATION, models_loaded=registry.is_loaded
        )

    @application.get("/health/ready", response_model=HealthResponse)
    def readiness(registry: ModelRegistry = Depends(get_registry)) -> HealthResponse:
        """Confirm that every model required for predictions can be loaded."""
        return HealthResponse(
            status="ready", location=config.LOCATION, models_loaded=registry.is_loaded
        )

    @application.get("/models", response_model=ModelsResponse)
    def models(registry: ModelRegistry = Depends(get_registry)) -> ModelsResponse:
        return ModelsResponse(location=config.LOCATION, models=registry.describe())

    @application.get("/api/observations", response_model=ObservationHistoryResponse)
    def observations(
        service: OpenMeteoObservationService = Depends(get_observation_service),
        location: WeatherLocation = Depends(get_requested_location),
    ) -> ObservationHistoryResponse:
        """Return recent, validated, cached Open-Meteo weather history for a searched place."""
        try:
            return service.fetch_observations(location)
        except OpenMeteoObservationError as exc:
            LOGGER.error("Could not obtain Open-Meteo observations: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(exc),
            ) from exc

    @application.get("/api/environment", response_model=EnvironmentalInsightsResponse)
    def environment(
        service: OpenMeteoAirQualityService = Depends(get_air_quality_service),
        location: WeatherLocation = Depends(get_requested_location),
    ) -> EnvironmentalInsightsResponse:
        """Return a cached, current air-quality and outdoor-dust summary for a selected place."""
        try:
            return service.fetch_environment(location)
        except OpenMeteoObservationError as exc:
            LOGGER.error("Could not obtain Open-Meteo air-quality data: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(exc),
            ) from exc

    @application.get("/api/climate-news", response_model=ClimateNewsResponse)
    def climate_news(
        service: ClimateNewsService = Depends(get_climate_news_service),
        location: WeatherLocation = Depends(get_requested_location),
    ) -> ClimateNewsResponse:
        """Return cached current climate and weather headlines for the dashboard."""
        try:
            return service.fetch_headlines(location)
        except ClimateNewsError as exc:
            LOGGER.error("Could not obtain current climate and weather news: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(exc),
            ) from exc

    @application.get("/api/locations", response_model=LocationSearchResponse)
    def locations(
        query: str = Query(min_length=2, max_length=120),
        service: OpenMeteoLocationSearchService = Depends(get_location_search_service),
    ) -> LocationSearchResponse:
        """Search known places for the dashboard's location selector."""
        try:
            return service.search(query)
        except LocationSearchError as exc:
            LOGGER.error("Location search failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(exc),
            ) from exc

    @application.post("/predict", response_model=PredictionResponse)
    def predict(
        payload: PredictionRequest,
        registry: ModelRegistry = Depends(get_registry),
    ) -> PredictionResponse:
        try:
            return generate_prediction(payload, registry)
        except PredictionInputError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
            ) from exc
        except ModelPredictionError as exc:
            LOGGER.exception("Prediction failed")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Model prediction failed: {exc}",
            ) from exc

    return application


logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
app = create_app()

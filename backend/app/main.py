"""FastAPI application for SkyCast AI model inference."""

from __future__ import annotations

import logging

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware

from backend.app import config
from backend.app.air_quality import OpenMeteoAirQualityService
from backend.app.model_loader import ModelLoadError, ModelRegistry
from backend.app.open_meteo import OpenMeteoObservationError, OpenMeteoObservationService
from backend.app.prediction import ModelPredictionError, PredictionInputError, generate_prediction
from backend.app.schemas import (
    HealthResponse,
    EnvironmentalInsightsResponse,
    ModelsResponse,
    ObservationHistoryResponse,
    PredictionRequest,
    PredictionResponse,
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


def create_app(
    model_registry: ModelRegistry | None = None,
    observation_service: OpenMeteoObservationService | None = None,
    air_quality_service: OpenMeteoAirQualityService | None = None,
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
    ) -> ObservationHistoryResponse:
        """Return a recent, validated, cached Open-Meteo weather history for Bengaluru."""
        try:
            return service.fetch_observations()
        except OpenMeteoObservationError as exc:
            LOGGER.error("Could not obtain Open-Meteo observations: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(exc),
            ) from exc

    @application.get("/api/environment", response_model=EnvironmentalInsightsResponse)
    def environment(
        service: OpenMeteoAirQualityService = Depends(get_air_quality_service),
    ) -> EnvironmentalInsightsResponse:
        """Return a cached, current air-quality and outdoor-dust summary for Bengaluru."""
        try:
            return service.fetch_environment()
        except OpenMeteoObservationError as exc:
            LOGGER.error("Could not obtain Open-Meteo air-quality data: %s", exc)
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

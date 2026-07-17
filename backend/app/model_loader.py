"""Select and lazily load the best trained SkyCast AI model artifacts."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from threading import Lock
from typing import Any

import joblib

from backend.app import config

LOGGER = logging.getLogger(__name__)


class ModelLoadError(RuntimeError):
    """Raised when metrics or a selected model artifact cannot be loaded."""


class ModelRegistry:
    """Thread-safe lazy registry for temperature, rain, and rainfall models."""

    def __init__(self) -> None:
        self._artifacts: dict[tuple[str, int], dict[str, Any]] = {}
        self._model_info: list[dict[str, Any]] = []
        self._loaded = False
        self._lock = Lock()

    @property
    def is_loaded(self) -> bool:
        """Return whether all selected artifacts are available in memory."""
        return self._loaded

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            raise ModelLoadError(f"Required metrics file is missing: {path}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ModelLoadError(f"Could not read metrics file {path}: {exc}") from exc
        if not isinstance(payload, dict):
            raise ModelLoadError(f"Metrics file must contain a JSON object: {path}")
        return payload

    @classmethod
    def _load_json_if_present(cls, path: Path) -> dict[str, Any] | None:
        """Load a metrics report when present, otherwise use documented defaults."""
        if not path.exists():
            LOGGER.warning(
                "Metrics report %s is unavailable; using configured model selections.", path
            )
            return None
        return cls._load_json(path)

    @staticmethod
    def _load_artifact(path: Path) -> dict[str, Any]:
        if not path.exists():
            raise ModelLoadError(f"Selected model file is missing: {path}")
        try:
            artifact = joblib.load(path)
        except Exception as exc:  # joblib may surface several deserialization exceptions
            raise ModelLoadError(f"Could not load model file {path}: {exc}") from exc
        if not isinstance(artifact, dict) or "model" not in artifact or "feature_columns" not in artifact:
            raise ModelLoadError(f"Model artifact has an invalid structure: {path}")
        return artifact

    @staticmethod
    def _temperature_path(horizon: int, model_name: str) -> Path:
        if model_name in {"random_forest", "hist_gradient_boosting"}:
            directory = config.ADVANCED_MODELS_DIR
        else:
            directory = config.BASELINE_MODELS_DIR
        return directory / f"temperature_{horizon}h_{model_name}.joblib"

    def load_all(self) -> None:
        """Load all 12 selected artifacts atomically."""
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return
            temperature_metrics = self._load_json_if_present(config.ADVANCED_METRICS_FILE)
            rain_metrics = self._load_json_if_present(config.RAIN_METRICS_FILE)

            artifacts: dict[tuple[str, int], dict[str, Any]] = {}
            model_info: list[dict[str, Any]] = []
            for horizon in config.FORECAST_HORIZONS:
                key = f"{horizon}h"
                try:
                    temperature_name = (
                        str(temperature_metrics["comparison"][key]["best_model"])
                        if temperature_metrics
                        else config.DEFAULT_TEMPERATURE_MODELS[horizon]
                    )
                    classifier_name = (
                        str(rain_metrics["classification"][key]["best_test_model"])
                        if rain_metrics
                        else config.DEFAULT_RAIN_CLASSIFIERS[horizon]
                    )
                    rainfall_name = (
                        str(rain_metrics["rainfall_amount"][key]["best_test_model"])
                        if rain_metrics
                        else config.DEFAULT_RAINFALL_MODELS[horizon]
                    )
                except KeyError as exc:
                    raise ModelLoadError(
                        "Metrics reports are incomplete. Regenerate them or remove them "
                        "to use the configured model selections."
                    ) from exc
                selections = (
                    (
                        "temperature",
                        temperature_name,
                        self._temperature_path(horizon, temperature_name),
                    ),
                    (
                        "rain_probability",
                        classifier_name,
                        config.RAIN_MODELS_DIR
                        / f"rain_{horizon}h_{classifier_name}.joblib",
                    ),
                    (
                        "rainfall_amount",
                        rainfall_name,
                        config.RAIN_MODELS_DIR
                        / f"rain_{horizon}h_{rainfall_name}.joblib",
                    ),
                )
                for task, model_name, path in selections:
                    artifacts[(task, horizon)] = self._load_artifact(path)
                    model_info.append(
                        {
                            "task": task,
                            "horizon_hours": horizon,
                            "model_name": model_name,
                            "artifact": (
                                str(path.relative_to(config.PROJECT_ROOT))
                                if path.is_relative_to(config.PROJECT_ROOT)
                                else str(path)
                            ),
                        }
                    )
                    LOGGER.info("Loaded %s %dh model from %s", task, horizon, path)
            self._artifacts = artifacts
            self._model_info = model_info
            self._loaded = True

    def get_artifact(self, task: str, horizon: int) -> dict[str, Any]:
        """Return a selected artifact after ensuring the registry is loaded."""
        self.load_all()
        try:
            return self._artifacts[(task, horizon)]
        except KeyError as exc:
            raise ModelLoadError(f"No model is registered for {task} at {horizon}h") from exc

    def describe(self) -> list[dict[str, Any]]:
        """Return serializable metadata for every selected model."""
        self.load_all()
        return list(self._model_info)

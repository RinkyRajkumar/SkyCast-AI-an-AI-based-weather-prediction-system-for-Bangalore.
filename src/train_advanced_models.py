"""Train, tune, evaluate, and persist advanced temperature regressors."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

from src import config
from src.evaluate import regression_metrics
from src.splits import horizon_safe_split

LOGGER = logging.getLogger(__name__)
ADVANCED_MODEL_NAMES = ("random_forest", "hist_gradient_boosting")

PARAMETER_CANDIDATES: dict[str, list[dict[str, Any]]] = {
    "random_forest": [
        {"n_estimators": 120, "max_depth": 16, "min_samples_leaf": 2, "max_features": 0.8},
        {"n_estimators": 180, "max_depth": None, "min_samples_leaf": 4, "max_features": 0.8},
    ],
    "hist_gradient_boosting": [
        {"learning_rate": 0.05, "max_iter": 180, "max_leaf_nodes": 31, "l2_regularization": 0.1},
        {"learning_rate": 0.08, "max_iter": 140, "max_leaf_nodes": 63, "l2_regularization": 0.5},
    ],
}


def advanced_model_path(horizon: int, model_name: str, models_dir: Path | None = None) -> Path:
    """Return the artifact path for an advanced model and horizon."""
    root = models_dir or config.ADVANCED_MODELS_DIR
    return root / f"temperature_{horizon}h_{model_name}.joblib"


def get_advanced_feature_columns(data: pd.DataFrame) -> list[str]:
    """Return predictor columns, excluding timestamps and every future target."""
    target_columns = {f"temperature_target_{h}h" for h in config.FORECAST_HORIZONS}
    columns = [
        column
        for column in data.columns
        if column != "time"
        and column not in target_columns
        and not column.startswith("previous_day_temperature_")
    ]
    if not columns:
        raise ValueError("No feature columns are available for advanced models")
    return columns


def build_advanced_model(model_name: str, parameters: dict[str, Any]) -> Pipeline:
    """Build a missing-value-safe advanced regression pipeline."""
    if model_name == "random_forest":
        estimator = RandomForestRegressor(random_state=42, n_jobs=-1, **parameters)
    elif model_name == "hist_gradient_boosting":
        estimator = HistGradientBoostingRegressor(random_state=42, **parameters)
    else:
        raise ValueError(f"Unknown advanced model: {model_name}")
    return Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("regressor", estimator),
        ]
    )


def train_advanced_models(
    feature_data: pd.DataFrame,
    models_dir: Path | None = None,
    parameter_candidates: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, object]:
    """Select hyperparameters by validation MAE and evaluate selected models on test data."""
    output_dir = models_dir or config.ADVANCED_MODELS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    candidates = parameter_candidates or PARAMETER_CANDIDATES
    feature_columns = get_advanced_feature_columns(feature_data)
    results: dict[str, object] = {
        "metadata": {
            "selection_metric": "validation_mae",
            "train_period": "2015-2022",
            "validation_period": "2023-2024",
            "test_period": "2025",
            "feature_count": len(feature_columns),
        },
        "advanced_models": {},
    }

    for horizon in config.FORECAST_HORIZONS:
        target_column = f"temperature_target_{horizon}h"
        train = horizon_safe_split(feature_data, "train", horizon).dropna(subset=[target_column])
        validation = horizon_safe_split(feature_data, "validation", horizon).dropna(
            subset=[target_column]
        )
        test = horizon_safe_split(feature_data, "test", horizon).dropna(subset=[target_column])
        if train.empty or validation.empty or test.empty:
            raise ValueError(f"One or more splits are empty for the {horizon}h horizon")

        horizon_key = f"{horizon}h"
        horizon_results: dict[str, object] = {}
        for model_name in ADVANCED_MODEL_NAMES:
            tuning_results: list[dict[str, object]] = []
            best_model: Pipeline | None = None
            best_parameters: dict[str, Any] | None = None
            best_validation: dict[str, float | int] | None = None

            for parameters in candidates[model_name]:
                LOGGER.info("Training %s for %dh with %s", model_name, horizon, parameters)
                model = build_advanced_model(model_name, parameters)
                model.fit(train[feature_columns], train[target_column])
                validation_predictions = model.predict(validation[feature_columns])
                validation_metrics = regression_metrics(
                    validation[target_column], validation_predictions
                )
                tuning_results.append(
                    {"parameters": parameters, "validation": validation_metrics}
                )
                if best_validation is None or validation_metrics["mae"] < best_validation["mae"]:
                    best_model = model
                    best_parameters = parameters
                    best_validation = validation_metrics

            if best_model is None or best_parameters is None or best_validation is None:
                raise RuntimeError(f"No {model_name} candidate was trained")
            test_predictions = best_model.predict(test[feature_columns])
            test_metrics = regression_metrics(test[target_column], test_predictions)
            artifact = {
                "model": best_model,
                "feature_columns": feature_columns,
                "model_name": model_name,
                "horizon_hours": horizon,
                "parameters": best_parameters,
            }
            path = advanced_model_path(horizon, model_name, output_dir)
            joblib.dump(artifact, path, compress=3)
            horizon_results[model_name] = {
                "best_parameters": best_parameters,
                "validation": best_validation,
                "test": test_metrics,
                "tuning_candidates": tuning_results,
                "artifact": path.name,
            }
            LOGGER.info(
                "%dh %s selected | validation MAE %.3f | test MAE %.3f",
                horizon,
                model_name,
                best_validation["mae"],
                test_metrics["mae"],
            )
        results["advanced_models"][horizon_key] = horizon_results
    return results


def run_training() -> dict[str, object]:
    """Load feature data, train advanced models, and save their metrics."""
    if not config.FEATURE_DATA_FILE.exists():
        raise FileNotFoundError(
            f"Feature data not found: {config.FEATURE_DATA_FILE}. Run python -m src.features first."
        )
    feature_data = pd.read_csv(config.FEATURE_DATA_FILE, parse_dates=["time"])
    results = train_advanced_models(feature_data)
    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    config.ADVANCED_METRICS_FILE.write_text(json.dumps(results, indent=2), encoding="utf-8")
    LOGGER.info("Saved advanced model metrics to %s", config.ADVANCED_METRICS_FILE)
    return results


def main() -> int:
    """Run advanced model training and return a process exit code."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    try:
        run_training()
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        LOGGER.error("Advanced model training failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Create future-rain targets and train classification and amount models."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import (
    HistGradientBoostingClassifier,
    HistGradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src import config
from src.evaluate import classification_metrics, regression_metrics
from src.splits import horizon_safe_split

LOGGER = logging.getLogger(__name__)
CLASSIFIER_NAMES = ("logistic_regression", "random_forest_classifier", "hist_gradient_boosting_classifier")
REGRESSOR_NAMES = ("random_forest_regressor", "hist_gradient_boosting_regressor")
CLASSIFICATION_THRESHOLDS = (0.3, 0.5, 0.7)

CLASSIFIER_CANDIDATES: dict[str, list[dict[str, Any]]] = {
    "logistic_regression": [{"C": 0.1}, {"C": 1.0}],
    "random_forest_classifier": [
        {"n_estimators": 100, "max_depth": 14, "min_samples_leaf": 2, "max_features": 0.8},
        {"n_estimators": 140, "max_depth": None, "min_samples_leaf": 4, "max_features": 0.8},
    ],
    "hist_gradient_boosting_classifier": [
        {"learning_rate": 0.05, "max_iter": 160, "max_leaf_nodes": 31, "l2_regularization": 0.1},
        {"learning_rate": 0.08, "max_iter": 130, "max_leaf_nodes": 63, "l2_regularization": 0.5},
    ],
}

REGRESSOR_CANDIDATES: dict[str, list[dict[str, Any]]] = {
    "random_forest_regressor": [
        {"n_estimators": 100, "max_depth": 14, "min_samples_leaf": 2, "max_features": 0.8},
        {"n_estimators": 140, "max_depth": None, "min_samples_leaf": 4, "max_features": 0.8},
    ],
    "hist_gradient_boosting_regressor": [
        {"learning_rate": 0.05, "max_iter": 160, "max_leaf_nodes": 31, "l2_regularization": 0.1},
        {"learning_rate": 0.08, "max_iter": 130, "max_leaf_nodes": 63, "l2_regularization": 0.5},
    ],
}


def create_rain_targets(feature_data: pd.DataFrame) -> pd.DataFrame:
    """Add cumulative future precipitation and binary rain targets for every horizon."""
    if "precipitation" not in feature_data.columns:
        raise ValueError("Feature data must contain 'precipitation'")
    data = feature_data.copy()
    precipitation = pd.to_numeric(data["precipitation"], errors="coerce")
    for horizon in config.FORECAST_HORIZONS:
        future_hours = pd.concat(
            [precipitation.shift(-step) for step in range(1, horizon + 1)], axis=1
        )
        amount = future_hours.sum(axis=1, min_count=horizon)
        data[f"rain_amount_target_{horizon}h"] = amount
        occurrence = (amount > 0).astype(float).where(amount.notna())
        data[f"rain_occurrence_target_{horizon}h"] = occurrence
    return data


def get_rain_feature_columns(data: pd.DataFrame) -> list[str]:
    """Select general historical predictors and exclude all future targets and timestamps."""
    columns = [
        column
        for column in data.columns
        if column != "time"
        and "_target_" not in column
        and not column.startswith("temperature_target_")
        and not column.startswith("previous_day_temperature_")
    ]
    if not columns:
        raise ValueError("No feature columns are available for rain models")
    return columns


def rain_model_path(
    horizon: int, model_name: str, models_dir: Path | None = None
) -> Path:
    """Return the artifact path for a rain model and horizon."""
    root = models_dir or config.RAIN_MODELS_DIR
    return root / f"rain_{horizon}h_{model_name}.joblib"


def build_classifier(model_name: str, parameters: dict[str, Any]) -> Pipeline:
    """Build a class-balanced, missing-value-safe classification pipeline."""
    if model_name == "logistic_regression":
        return Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                (
                    "classifier",
                    LogisticRegression(
                        class_weight="balanced", max_iter=1000, random_state=42, **parameters
                    ),
                ),
            ]
        )
    if model_name == "random_forest_classifier":
        estimator = RandomForestClassifier(
            class_weight="balanced", random_state=42, n_jobs=-1, **parameters
        )
    elif model_name == "hist_gradient_boosting_classifier":
        estimator = HistGradientBoostingClassifier(
            class_weight="balanced", random_state=42, **parameters
        )
    else:
        raise ValueError(f"Unknown rain classifier: {model_name}")
    return Pipeline(
        steps=[("imputer", SimpleImputer(strategy="median")), ("classifier", estimator)]
    )


def build_regressor(model_name: str, parameters: dict[str, Any]) -> Pipeline:
    """Build a missing-value-safe rainfall amount regression pipeline."""
    if model_name == "random_forest_regressor":
        estimator = RandomForestRegressor(random_state=42, n_jobs=-1, **parameters)
    elif model_name == "hist_gradient_boosting_regressor":
        estimator = HistGradientBoostingRegressor(random_state=42, **parameters)
    else:
        raise ValueError(f"Unknown rainfall regressor: {model_name}")
    return Pipeline(
        steps=[("imputer", SimpleImputer(strategy="median")), ("regressor", estimator)]
    )


def train_rain_models(
    feature_data: pd.DataFrame,
    models_dir: Path | None = None,
) -> dict[str, object]:
    """Tune rain models on validation data, save selected artifacts, and return metrics."""
    data = create_rain_targets(feature_data)
    feature_columns = get_rain_feature_columns(data)
    output_dir = models_dir or config.RAIN_MODELS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    results: dict[str, object] = {
        "metadata": {
            "target_definition": "sum of precipitation from t+1 through t+h; occurrence is sum > 0",
            "classifier_selection_metric": "validation_f1",
            "regressor_selection_metric": "validation_mae",
            "train_period": "2015-2022",
            "validation_period": "2023-2024",
            "test_period": "2025",
            "feature_count": len(feature_columns),
        },
        "classification": {},
        "rainfall_amount": {},
    }

    for horizon in config.FORECAST_HORIZONS:
        train = horizon_safe_split(data, "train", horizon)
        validation = horizon_safe_split(data, "validation", horizon)
        occurrence_target = f"rain_occurrence_target_{horizon}h"
        amount_target = f"rain_amount_target_{horizon}h"
        train_class = train.dropna(subset=[occurrence_target])
        validation_class = validation.dropna(subset=[occurrence_target])
        train_amount = train.dropna(subset=[amount_target])
        validation_amount = validation.dropna(subset=[amount_target])
        horizon_key = f"{horizon}h"
        classification_results: dict[str, object] = {}
        amount_results: dict[str, object] = {}

        for model_name in CLASSIFIER_NAMES:
            best: tuple[Pipeline, dict[str, Any], float, dict[str, float | int | None]] | None = None
            tuning: list[dict[str, object]] = []
            for parameters in CLASSIFIER_CANDIDATES[model_name]:
                LOGGER.info("Training %s for %dh with %s", model_name, horizon, parameters)
                model = build_classifier(model_name, parameters)
                model.fit(train_class[feature_columns], train_class[occurrence_target].astype(int))
                probabilities = model.predict_proba(validation_class[feature_columns])[:, 1]
                for threshold in CLASSIFICATION_THRESHOLDS:
                    metrics = classification_metrics(
                        validation_class[occurrence_target].astype(int), probabilities, threshold
                    )
                    tuning.append(
                        {"parameters": parameters, "threshold": threshold, "validation": metrics}
                    )
                    if best is None or metrics["f1"] > best[3]["f1"]:
                        best = (model, parameters, threshold, metrics)
            if best is None:
                raise RuntimeError(f"No {model_name} candidate was trained")
            model, parameters, threshold, validation_metrics = best
            artifact = {
                "model": model,
                "feature_columns": feature_columns,
                "model_name": model_name,
                "task": "classification",
                "horizon_hours": horizon,
                "parameters": parameters,
                "threshold": threshold,
            }
            path = rain_model_path(horizon, model_name, output_dir)
            joblib.dump(artifact, path, compress=3)
            classification_results[model_name] = {
                "best_parameters": parameters,
                "threshold": threshold,
                "validation": validation_metrics,
                "tuning_candidates": tuning,
                "artifact": path.name,
            }
            LOGGER.info(
                "%dh %s selected | validation F1 %.3f | threshold %.1f",
                horizon,
                model_name,
                validation_metrics["f1"],
                threshold,
            )

        for model_name in REGRESSOR_NAMES:
            best_regressor: tuple[Pipeline, dict[str, Any], dict[str, float | int]] | None = None
            tuning_regression: list[dict[str, object]] = []
            for parameters in REGRESSOR_CANDIDATES[model_name]:
                LOGGER.info("Training %s for %dh with %s", model_name, horizon, parameters)
                model = build_regressor(model_name, parameters)
                model.fit(train_amount[feature_columns], train_amount[amount_target])
                predictions = np.maximum(model.predict(validation_amount[feature_columns]), 0.0)
                metrics = regression_metrics(validation_amount[amount_target], predictions)
                tuning_regression.append({"parameters": parameters, "validation": metrics})
                if best_regressor is None or metrics["mae"] < best_regressor[2]["mae"]:
                    best_regressor = (model, parameters, metrics)
            if best_regressor is None:
                raise RuntimeError(f"No {model_name} candidate was trained")
            model, parameters, validation_metrics = best_regressor
            artifact = {
                "model": model,
                "feature_columns": feature_columns,
                "model_name": model_name,
                "task": "rainfall_amount",
                "horizon_hours": horizon,
                "parameters": parameters,
            }
            path = rain_model_path(horizon, model_name, output_dir)
            joblib.dump(artifact, path, compress=3)
            amount_results[model_name] = {
                "best_parameters": parameters,
                "validation": validation_metrics,
                "tuning_candidates": tuning_regression,
                "artifact": path.name,
            }
            LOGGER.info(
                "%dh %s selected | validation MAE %.3f mm",
                horizon,
                model_name,
                validation_metrics["mae"],
            )
        results["classification"][horizon_key] = classification_results
        results["rainfall_amount"][horizon_key] = amount_results
    return results


def run_training() -> dict[str, object]:
    """Load feature data, train all rain models, and save validation results."""
    if not config.FEATURE_DATA_FILE.exists():
        raise FileNotFoundError(f"Feature data not found: {config.FEATURE_DATA_FILE}")
    feature_data = pd.read_csv(config.FEATURE_DATA_FILE, parse_dates=["time"])
    results = train_rain_models(feature_data)
    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    config.RAIN_METRICS_FILE.write_text(json.dumps(results, indent=2), encoding="utf-8")
    LOGGER.info("Saved rain validation metrics to %s", config.RAIN_METRICS_FILE)
    return results


def main() -> int:
    """Run rain model training and return a process exit code."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    try:
        run_training()
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        LOGGER.error("Rain model training failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Evaluate saved baseline temperature forecasting models."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    brier_score_loss,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)

from src import config
from src.splits import horizon_safe_split
from src.train_baselines import MODEL_NAMES, model_path

LOGGER = logging.getLogger(__name__)


def classification_metrics(
    actual: pd.Series, probabilities: np.ndarray, threshold: float = 0.5
) -> dict[str, float | int | None]:
    """Calculate binary rain metrics from positive-class probabilities."""
    actual_values = actual.to_numpy(dtype=int)
    probability_values = np.asarray(probabilities, dtype=float)
    valid = np.isfinite(probability_values)
    if not valid.any():
        raise ValueError("No valid classification probabilities are available")
    y_true = actual_values[valid]
    y_probability = np.clip(probability_values[valid], 0.0, 1.0)
    y_predicted = (y_probability >= threshold).astype(int)
    roc_auc = float(roc_auc_score(y_true, y_probability)) if np.unique(y_true).size == 2 else None
    return {
        "precision": float(precision_score(y_true, y_predicted, zero_division=0)),
        "recall": float(recall_score(y_true, y_predicted, zero_division=0)),
        "f1": float(f1_score(y_true, y_predicted, zero_division=0)),
        "roc_auc": roc_auc,
        "brier_score": float(brier_score_loss(y_true, y_probability)),
        "threshold": float(threshold),
        "samples": int(valid.sum()),
        "positive_rate": float(y_true.mean()),
    }


def regression_metrics(actual: pd.Series, predicted: np.ndarray) -> dict[str, float | int]:
    """Calculate MAE, RMSE, and R² after excluding non-finite pairs."""
    actual_values = actual.to_numpy(dtype=float)
    predicted_values = np.asarray(predicted, dtype=float)
    valid = np.isfinite(actual_values) & np.isfinite(predicted_values)
    if not valid.any():
        raise ValueError("No valid observation/prediction pairs are available")
    y_true = actual_values[valid]
    y_pred = predicted_values[valid]
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "r2": float(r2_score(y_true, y_pred)),
        "samples": int(valid.sum()),
    }


def predict_artifact(artifact: object, model_name: str, data: pd.DataFrame) -> np.ndarray:
    """Generate predictions from a saved baseline artifact."""
    if model_name == "linear_regression":
        return artifact["model"].predict(data[artifact["feature_columns"]])
    return artifact.predict(data)


def evaluate_models(
    feature_data: pd.DataFrame,
    models_dir: Path | None = None,
) -> dict[str, dict[str, dict[str, dict[str, float | int]]]]:
    """Evaluate every saved model on chronological validation and test splits."""
    results: dict[str, dict[str, dict[str, dict[str, float | int]]]] = {}
    for horizon in config.FORECAST_HORIZONS:
        horizon_key = f"{horizon}h"
        target_column = f"temperature_target_{horizon}h"
        results[horizon_key] = {}
        for model_name in MODEL_NAMES:
            path = model_path(horizon, model_name, models_dir)
            if not path.exists():
                raise FileNotFoundError(f"Model artifact not found: {path}")
            artifact = joblib.load(path)
            results[horizon_key][model_name] = {}
            for split_name in ("validation", "test"):
                split = horizon_safe_split(feature_data, split_name, horizon).dropna(
                    subset=[target_column]
                )
                predictions = predict_artifact(artifact, model_name, split)
                results[horizon_key][model_name][split_name] = regression_metrics(
                    split[target_column], predictions
                )
    return results


def run_evaluation() -> dict[str, object]:
    """Load features and models, evaluate them, and save JSON metrics."""
    if not config.FEATURE_DATA_FILE.exists():
        raise FileNotFoundError(f"Feature data not found: {config.FEATURE_DATA_FILE}")
    feature_data = pd.read_csv(config.FEATURE_DATA_FILE, parse_dates=["time"])
    results = evaluate_models(feature_data)
    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    config.BASELINE_METRICS_FILE.write_text(json.dumps(results, indent=2), encoding="utf-8")
    LOGGER.info("Saved baseline metrics to %s", config.BASELINE_METRICS_FILE)
    for horizon, models in results.items():
        best_name, best_metrics = min(
            ((name, values["test"]) for name, values in models.items()),
            key=lambda item: item[1]["mae"],
        )
        LOGGER.info("%s best test MAE: %s (%.3f °C)", horizon, best_name, best_metrics["mae"])
    return results


def main() -> int:
    """Run baseline evaluation and return a process exit code."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    try:
        run_evaluation()
    except (FileNotFoundError, OSError, ValueError) as exc:
        LOGGER.error("Evaluation failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

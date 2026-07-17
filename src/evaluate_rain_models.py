"""Evaluate saved rain models on 2025 data and generate diagnostic plots."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import joblib
import matplotlib
import numpy as np
import pandas as pd
from sklearn.metrics import ConfusionMatrixDisplay, confusion_matrix, precision_recall_curve

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src import config
from src.evaluate import classification_metrics, regression_metrics
from src.splits import horizon_safe_split
from src.train_rain_models import (
    CLASSIFIER_NAMES,
    REGRESSOR_NAMES,
    create_rain_targets,
    rain_model_path,
)

LOGGER = logging.getLogger(__name__)


def load_training_results(path: Path | None = None) -> dict[str, Any]:
    """Load the validation/tuning results written by rain training."""
    metrics_path = path or config.RAIN_METRICS_FILE
    if not metrics_path.exists():
        raise FileNotFoundError(
            f"Rain metrics not found: {metrics_path}. Run python -m src.train_rain_models first."
        )
    results = json.loads(metrics_path.read_text(encoding="utf-8"))
    if not isinstance(results, dict):
        raise ValueError("Rain metrics file must contain a JSON object")
    return results


def evaluate_saved_rain_models(
    feature_data: pd.DataFrame,
    training_results: dict[str, Any],
    models_dir: Path | None = None,
) -> dict[str, Any]:
    """Add untouched test metrics and best-model summaries to training results."""
    data = create_rain_targets(feature_data)
    for horizon in config.FORECAST_HORIZONS:
        key = f"{horizon}h"
        test = horizon_safe_split(data, "test", horizon)
        occurrence_target = f"rain_occurrence_target_{horizon}h"
        amount_target = f"rain_amount_target_{horizon}h"
        classification_test = test.dropna(subset=[occurrence_target])
        amount_test = test.dropna(subset=[amount_target])

        for model_name in CLASSIFIER_NAMES:
            artifact = joblib.load(rain_model_path(horizon, model_name, models_dir))
            probabilities = artifact["model"].predict_proba(
                classification_test[artifact["feature_columns"]]
            )[:, 1]
            training_results["classification"][key][model_name]["test"] = (
                classification_metrics(
                    classification_test[occurrence_target].astype(int),
                    probabilities,
                    artifact["threshold"],
                )
            )

        for model_name in REGRESSOR_NAMES:
            artifact = joblib.load(rain_model_path(horizon, model_name, models_dir))
            predictions = np.maximum(
                artifact["model"].predict(amount_test[artifact["feature_columns"]]), 0.0
            )
            training_results["rainfall_amount"][key][model_name]["test"] = regression_metrics(
                amount_test[amount_target], predictions
            )

        classifier_results = training_results["classification"][key]
        best_classifier = max(
            CLASSIFIER_NAMES, key=lambda name: classifier_results[name]["test"]["f1"]
        )
        amount_results = training_results["rainfall_amount"][key]
        best_regressor = min(
            REGRESSOR_NAMES, key=lambda name: amount_results[name]["test"]["mae"]
        )
        training_results["classification"][key]["best_test_model"] = best_classifier
        training_results["rainfall_amount"][key]["best_test_model"] = best_regressor
    return training_results


def best_overall_model(
    results: dict[str, Any], task_key: str, model_names: tuple[str, ...], metric: str, maximize: bool
) -> tuple[int, str, dict[str, float | int | None]]:
    """Return the strongest model/horizon pair by a test metric."""
    candidates: list[tuple[int, str, dict[str, float | int | None]]] = []
    for horizon in config.FORECAST_HORIZONS:
        key = f"{horizon}h"
        for model_name in model_names:
            candidates.append((horizon, model_name, results[task_key][key][model_name]["test"]))
    selector = max if maximize else min
    return selector(candidates, key=lambda item: item[2][metric])


def classification_predictions(
    feature_data: pd.DataFrame, horizon: int, model_name: str
) -> tuple[pd.DataFrame, np.ndarray, np.ndarray, dict[str, Any]]:
    """Load one classifier and return test rows, probabilities, and thresholded predictions."""
    data = create_rain_targets(feature_data)
    target = f"rain_occurrence_target_{horizon}h"
    test = horizon_safe_split(data, "test", horizon).dropna(subset=[target])
    artifact = joblib.load(rain_model_path(horizon, model_name))
    probabilities = artifact["model"].predict_proba(test[artifact["feature_columns"]])[:, 1]
    predictions = (probabilities >= artifact["threshold"]).astype(int)
    return test, probabilities, predictions, artifact


def rainfall_predictions(
    feature_data: pd.DataFrame, horizon: int, model_name: str
) -> tuple[pd.DataFrame, np.ndarray, dict[str, Any]]:
    """Load one rainfall regressor and return non-negative test predictions."""
    data = create_rain_targets(feature_data)
    target = f"rain_amount_target_{horizon}h"
    test = horizon_safe_split(data, "test", horizon).dropna(subset=[target])
    artifact = joblib.load(rain_model_path(horizon, model_name))
    predictions = np.maximum(
        artifact["model"].predict(test[artifact["feature_columns"]]), 0.0
    )
    return test, predictions, artifact


def plot_confusion_matrix(
    feature_data: pd.DataFrame, horizon: int, model_name: str, figures_dir: Path
) -> Path:
    """Save a confusion matrix for the strongest classifier/horizon pair."""
    test, _, predictions, _ = classification_predictions(feature_data, horizon, model_name)
    target = test[f"rain_occurrence_target_{horizon}h"].astype(int)
    matrix = confusion_matrix(target, predictions)
    display = ConfusionMatrixDisplay(matrix, display_labels=["No rain", "Rain"])
    display.plot(cmap="Blues", colorbar=False)
    display.ax_.set_title(f"Rain Confusion Matrix: {model_name}, {horizon}h")
    display.figure_.tight_layout()
    path = figures_dir / "rain_confusion_matrix.png"
    display.figure_.savefig(path, dpi=160)
    plt.close(display.figure_)
    return path


def plot_precision_recall(
    feature_data: pd.DataFrame, horizon: int, model_name: str, figures_dir: Path
) -> Path:
    """Save a precision-recall curve for the strongest classifier/horizon pair."""
    test, probabilities, _, _ = classification_predictions(feature_data, horizon, model_name)
    target = test[f"rain_occurrence_target_{horizon}h"].astype(int)
    precision, recall, _ = precision_recall_curve(target, probabilities)
    fig, axis = plt.subplots(figsize=(7, 6))
    axis.plot(recall, precision, color="#2e86ab")
    axis.axhline(target.mean(), color="gray", linestyle="--", label="Positive-rate baseline")
    axis.set(
        title=f"Rain Precision–Recall Curve: {model_name}, {horizon}h",
        xlabel="Recall",
        ylabel="Precision",
        xlim=(0, 1),
        ylim=(0, 1.02),
    )
    axis.grid(alpha=0.25)
    axis.legend()
    fig.tight_layout()
    path = figures_dir / "rain_precision_recall_curve.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def plot_predicted_vs_actual_rainfall(
    feature_data: pd.DataFrame, horizon: int, model_name: str, figures_dir: Path
) -> Path:
    """Save two weeks of predicted and actual rainfall amounts."""
    test, predictions, _ = rainfall_predictions(feature_data, horizon, model_name)
    target = f"rain_amount_target_{horizon}h"
    display_rows = min(24 * 14, len(test))
    fig, axis = plt.subplots(figsize=(13, 5))
    axis.plot(test["time"].iloc[:display_rows], test[target].iloc[:display_rows], label="Actual", linewidth=1.4)
    axis.plot(test["time"].iloc[:display_rows], predictions[:display_rows], label="Predicted", linewidth=1.2)
    axis.set(
        title=f"Future Rainfall Amount: {model_name}, {horizon}h",
        xlabel="Forecast issue time",
        ylabel="Accumulated precipitation (mm)",
    )
    axis.grid(alpha=0.25)
    axis.legend()
    fig.autofmt_xdate()
    fig.tight_layout()
    path = figures_dir / "rainfall_predicted_vs_actual.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def plot_model_comparison(results: dict[str, Any], figures_dir: Path) -> Path:
    """Plot classifier F1 and rainfall-regressor MAE for every horizon."""
    horizons = [f"{h}h" for h in config.FORECAST_HORIZONS]
    x = np.arange(len(horizons))
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))

    classification_width = 0.24
    for index, model_name in enumerate(CLASSIFIER_NAMES):
        values = [results["classification"][h][model_name]["test"]["f1"] for h in horizons]
        axes[0].bar(x + (index - 1) * classification_width, values, classification_width, label=model_name)
    axes[0].set(title="Rain Classification Test F1", xlabel="Horizon", ylabel="F1", xticks=x, xticklabels=horizons, ylim=(0, 1))
    axes[0].legend(fontsize=8)
    axes[0].grid(axis="y", alpha=0.25)

    regression_width = 0.34
    for index, model_name in enumerate(REGRESSOR_NAMES):
        values = [results["rainfall_amount"][h][model_name]["test"]["mae"] for h in horizons]
        axes[1].bar(x + (index - 0.5) * regression_width, values, regression_width, label=model_name)
    axes[1].set(title="Rainfall Amount Test MAE", xlabel="Horizon", ylabel="MAE (mm)", xticks=x, xticklabels=horizons)
    axes[1].legend(fontsize=8)
    axes[1].grid(axis="y", alpha=0.25)
    fig.tight_layout()
    path = figures_dir / "rain_model_comparison.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def run_evaluation() -> dict[str, Any]:
    """Evaluate rain artifacts, update metrics JSON, and generate all requested plots."""
    if not config.FEATURE_DATA_FILE.exists():
        raise FileNotFoundError(f"Feature data not found: {config.FEATURE_DATA_FILE}")
    feature_data = pd.read_csv(config.FEATURE_DATA_FILE, parse_dates=["time"])
    results = evaluate_saved_rain_models(feature_data, load_training_results())
    best_classifier = best_overall_model(
        results, "classification", CLASSIFIER_NAMES, "f1", maximize=True
    )
    best_regressor = best_overall_model(
        results, "rainfall_amount", REGRESSOR_NAMES, "mae", maximize=False
    )
    results["best_overall"] = {
        "classification": {
            "horizon": f"{best_classifier[0]}h",
            "model": best_classifier[1],
            "test": best_classifier[2],
        },
        "rainfall_amount": {
            "horizon": f"{best_regressor[0]}h",
            "model": best_regressor[1],
            "test": best_regressor[2],
        },
    }
    config.RAIN_METRICS_FILE.write_text(json.dumps(results, indent=2), encoding="utf-8")

    config.FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    paths = [
        plot_confusion_matrix(feature_data, best_classifier[0], best_classifier[1], config.FIGURES_DIR),
        plot_precision_recall(feature_data, best_classifier[0], best_classifier[1], config.FIGURES_DIR),
        plot_predicted_vs_actual_rainfall(feature_data, best_regressor[0], best_regressor[1], config.FIGURES_DIR),
        plot_model_comparison(results, config.FIGURES_DIR),
    ]
    for path in paths:
        LOGGER.info("Saved figure to %s", path)
    LOGGER.info(
        "Best rain classifier: %s %dh (test F1 %.3f)",
        best_classifier[1],
        best_classifier[0],
        best_classifier[2]["f1"],
    )
    LOGGER.info(
        "Best rainfall model: %s %dh (test MAE %.3f mm)",
        best_regressor[1],
        best_regressor[0],
        best_regressor[2]["mae"],
    )
    return results


def main() -> int:
    """Run rain evaluation and return a process exit code."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    try:
        run_evaluation()
    except (FileNotFoundError, KeyError, OSError, ValueError) as exc:
        LOGGER.error("Rain evaluation failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

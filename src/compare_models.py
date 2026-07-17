"""Compare advanced and baseline forecasts and generate diagnostic figures."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import joblib
import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src import config
from src.evaluate import predict_artifact
from src.splits import horizon_safe_split
from src.train_advanced_models import ADVANCED_MODEL_NAMES, advanced_model_path
from src.train_baselines import MODEL_NAMES, model_path

LOGGER = logging.getLogger(__name__)


def load_json(path: Path) -> dict[str, Any]:
    """Load a JSON object from disk."""
    if not path.exists():
        raise FileNotFoundError(f"Metrics file not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return payload


def build_comparison(
    advanced_results: dict[str, Any], baseline_results: dict[str, Any]
) -> dict[str, dict[str, object]]:
    """Combine test metrics and identify the lowest-MAE model for each horizon."""
    comparison: dict[str, dict[str, object]] = {}
    advanced_models = advanced_results["advanced_models"]
    for horizon in config.FORECAST_HORIZONS:
        key = f"{horizon}h"
        models: dict[str, dict[str, float | int]] = {
            name: baseline_results[key][name]["test"] for name in MODEL_NAMES
        }
        models.update(
            {name: advanced_models[key][name]["test"] for name in ADVANCED_MODEL_NAMES}
        )
        best_name = min(models, key=lambda name: models[name]["mae"])
        comparison[key] = {
            "test_metrics": models,
            "best_model": best_name,
            "best_test_metrics": models[best_name],
        }
    return comparison


def load_predictions(
    model_name: str, horizon: int, test: pd.DataFrame
) -> tuple[np.ndarray, object]:
    """Load a baseline or advanced artifact and return its test predictions."""
    if model_name in ADVANCED_MODEL_NAMES:
        artifact = joblib.load(advanced_model_path(horizon, model_name))
        return artifact["model"].predict(test[artifact["feature_columns"]]), artifact
    artifact = joblib.load(model_path(horizon, model_name))
    return predict_artifact(artifact, model_name, test), artifact


def plot_actual_vs_predicted(
    feature_data: pd.DataFrame, comparison: dict[str, dict[str, object]], figures_dir: Path
) -> Path:
    """Plot two weeks of actual and predicted temperature for the best 24h model."""
    horizon = 24
    target_column = "temperature_target_24h"
    test = horizon_safe_split(feature_data, "test", horizon).dropna(subset=[target_column])
    model_name = str(comparison["24h"]["best_model"])
    predictions, _ = load_predictions(model_name, horizon, test)
    display_rows = min(24 * 14, len(test))

    fig, axis = plt.subplots(figsize=(13, 5))
    axis.plot(test["time"].iloc[:display_rows], test[target_column].iloc[:display_rows], label="Actual", linewidth=1.5)
    axis.plot(test["time"].iloc[:display_rows], predictions[:display_rows], label="Predicted", linewidth=1.2)
    axis.set(title=f"24h Temperature Forecast: {model_name}", xlabel="Forecast issue time", ylabel="Temperature (°C)")
    axis.legend()
    axis.grid(alpha=0.25)
    fig.autofmt_xdate()
    fig.tight_layout()
    path = figures_dir / "actual_vs_predicted_24h.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def plot_random_forest_importance(figures_dir: Path) -> Path:
    """Plot the top 20 impurity-based feature importances for the 24h Random Forest."""
    artifact = joblib.load(advanced_model_path(24, "random_forest"))
    importances = artifact["model"].named_steps["regressor"].feature_importances_
    importance = pd.Series(importances, index=artifact["feature_columns"]).nlargest(20).sort_values()
    fig, axis = plt.subplots(figsize=(9, 7))
    importance.plot.barh(ax=axis, color="#2e86ab")
    axis.set(title="Random Forest 24h Forecast: Top Feature Importances", xlabel="Impurity-based importance", ylabel="Feature")
    axis.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    path = figures_dir / "random_forest_feature_importance.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def plot_mae_comparison(comparison: dict[str, dict[str, object]], figures_dir: Path) -> Path:
    """Plot test MAE for every baseline and advanced model across horizons."""
    model_names = [*MODEL_NAMES, *ADVANCED_MODEL_NAMES]
    horizons = [f"{h}h" for h in config.FORECAST_HORIZONS]
    x = np.arange(len(horizons))
    width = 0.13
    fig, axis = plt.subplots(figsize=(13, 6))
    for index, model_name in enumerate(model_names):
        values = [comparison[h]["test_metrics"][model_name]["mae"] for h in horizons]
        axis.bar(x + (index - 2.5) * width, values, width, label=model_name)
    axis.set(title="Test MAE by Model and Forecast Horizon", xlabel="Forecast horizon", ylabel="MAE (°C)")
    axis.set_xticks(x, horizons)
    axis.legend(ncols=2)
    axis.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    path = figures_dir / "mae_comparison_all_models.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def run_comparison() -> dict[str, Any]:
    """Combine metrics, update the report, and create all requested plots."""
    advanced_results = load_json(config.ADVANCED_METRICS_FILE)
    baseline_results = load_json(config.BASELINE_METRICS_FILE)
    if not config.FEATURE_DATA_FILE.exists():
        raise FileNotFoundError(f"Feature data not found: {config.FEATURE_DATA_FILE}")
    feature_data = pd.read_csv(config.FEATURE_DATA_FILE, parse_dates=["time"])
    comparison = build_comparison(advanced_results, baseline_results)
    advanced_results["baseline_models"] = baseline_results
    advanced_results["comparison"] = comparison
    config.ADVANCED_METRICS_FILE.write_text(
        json.dumps(advanced_results, indent=2), encoding="utf-8"
    )

    config.FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    paths = [
        plot_actual_vs_predicted(feature_data, comparison, config.FIGURES_DIR),
        plot_random_forest_importance(config.FIGURES_DIR),
        plot_mae_comparison(comparison, config.FIGURES_DIR),
    ]
    for path in paths:
        LOGGER.info("Saved figure to %s", path)
    for horizon, values in comparison.items():
        LOGGER.info(
            "%s best overall: %s (test MAE %.3f °C)",
            horizon,
            values["best_model"],
            values["best_test_metrics"]["mae"],
        )
    return advanced_results


def main() -> int:
    """Run model comparison and return a process exit code."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    try:
        run_comparison()
    except (FileNotFoundError, KeyError, OSError, ValueError) as exc:
        LOGGER.error("Model comparison failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

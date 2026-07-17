"""Train and persist baseline models for all configured forecast horizons."""

from __future__ import annotations

import logging
from pathlib import Path

import joblib
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src import config
from src.baselines import MonthHourAverageBaseline, PersistenceBaseline, PreviousDayBaseline
from src.splits import horizon_safe_split

LOGGER = logging.getLogger(__name__)
MODEL_NAMES = ("persistence", "previous_day", "month_hour_average", "linear_regression")


def model_path(horizon: int, model_name: str, models_dir: Path | None = None) -> Path:
    """Return the artifact path for a model and forecast horizon."""
    root = models_dir or config.MODELS_DIR
    return root / f"temperature_{horizon}h_{model_name}.joblib"


def get_linear_feature_columns(data: pd.DataFrame) -> list[str]:
    """Select numeric predictors while excluding timestamps and all future targets."""
    excluded = {"time", *(f"temperature_target_{h}h" for h in config.FORECAST_HORIZONS)}
    return [
        column
        for column in data.columns
        if column not in excluded and not column.startswith("previous_day_temperature_")
    ]


def build_models(linear_features: list[str], horizon: int) -> dict[str, object]:
    """Construct all requested baseline estimators."""
    linear_model = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("regressor", LinearRegression()),
        ]
    )
    return {
        "persistence": PersistenceBaseline(),
        "previous_day": PreviousDayBaseline(horizon_hours=horizon),
        "month_hour_average": MonthHourAverageBaseline(horizon_hours=horizon),
        "linear_regression": {"model": linear_model, "feature_columns": linear_features},
    }


def train_models(feature_data: pd.DataFrame, models_dir: Path | None = None) -> list[Path]:
    """Fit every baseline on 2015–2022 only and save its artifact."""
    output_dir = models_dir or config.MODELS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    linear_features = get_linear_feature_columns(feature_data)
    saved: list[Path] = []

    for horizon in config.FORECAST_HORIZONS:
        train = horizon_safe_split(feature_data, "train", horizon)
        if train.empty:
            raise ValueError(f"Training split is empty for the {horizon}h horizon")
        target_column = f"temperature_target_{horizon}h"
        fit_data = train.dropna(subset=[target_column])
        target = fit_data[target_column]
        models = build_models(linear_features, horizon)
        for name, artifact in models.items():
            if name == "linear_regression":
                artifact["model"].fit(fit_data[linear_features], target)
            else:
                artifact.fit(fit_data, target)
            path = model_path(horizon, name, output_dir)
            joblib.dump(artifact, path)
            saved.append(path)
            LOGGER.info("Saved %dh %s model to %s", horizon, name, path)
    return saved


def run_training() -> list[Path]:
    """Load feature data and train all baseline artifacts."""
    if not config.FEATURE_DATA_FILE.exists():
        raise FileNotFoundError(
            f"Feature data not found: {config.FEATURE_DATA_FILE}. Run python -m src.features first."
        )
    feature_data = pd.read_csv(config.FEATURE_DATA_FILE, parse_dates=["time"])
    return train_models(feature_data)


def main() -> int:
    """Run baseline training and return a process exit code."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    try:
        run_training()
    except (FileNotFoundError, OSError, ValueError) as exc:
        LOGGER.error("Baseline training failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

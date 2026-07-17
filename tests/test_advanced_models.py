"""Tests for advanced temperature model utilities."""

import joblib
import numpy as np
import pandas as pd
import pytest

from src.evaluate import regression_metrics
from src.train_advanced_models import build_advanced_model, get_advanced_feature_columns


@pytest.fixture
def regression_data() -> tuple[pd.DataFrame, pd.Series]:
    rng = np.random.default_rng(42)
    features = pd.DataFrame(
        {
            "temperature_2m": np.linspace(18.0, 30.0, 80),
            "humidity_mean_24h": rng.normal(65.0, 5.0, 80),
        }
    )
    features.loc[4, "humidity_mean_24h"] = np.nan
    target = 0.8 * features["temperature_2m"] + 3.0
    return features, target


@pytest.mark.parametrize(
    ("model_name", "parameters"),
    [
        (
            "random_forest",
            {"n_estimators": 8, "max_depth": 4, "min_samples_leaf": 1, "max_features": 1.0},
        ),
        (
            "hist_gradient_boosting",
            {"learning_rate": 0.1, "max_iter": 10, "max_leaf_nodes": 7, "l2_regularization": 0.0},
        ),
    ],
)
def test_model_training_and_prediction_shape(
    regression_data: tuple[pd.DataFrame, pd.Series],
    model_name: str,
    parameters: dict[str, object],
) -> None:
    features, target = regression_data
    model = build_advanced_model(model_name, parameters)
    model.fit(features, target)
    predictions = model.predict(features)
    assert predictions.shape == target.shape
    assert np.isfinite(predictions).all()


def test_advanced_model_saving_and_loading(
    regression_data: tuple[pd.DataFrame, pd.Series], tmp_path
) -> None:
    features, target = regression_data
    model = build_advanced_model(
        "random_forest",
        {"n_estimators": 5, "max_depth": 3, "min_samples_leaf": 1, "max_features": 1.0},
    )
    model.fit(features, target)
    path = tmp_path / "advanced.joblib"
    joblib.dump({"model": model, "feature_columns": features.columns.tolist()}, path)
    loaded = joblib.load(path)
    assert np.allclose(
        model.predict(features),
        loaded["model"].predict(features[loaded["feature_columns"]]),
    )


def test_metric_calculation() -> None:
    actual = pd.Series([1.0, 2.0, 3.0])
    metrics = regression_metrics(actual, np.array([1.0, 2.0, 4.0]))
    assert metrics["mae"] == pytest.approx(1 / 3)
    assert metrics["rmse"] == pytest.approx(np.sqrt(1 / 3))
    assert metrics["r2"] == pytest.approx(0.5)
    assert metrics["samples"] == 3


def test_feature_selection_excludes_time_and_all_targets() -> None:
    data = pd.DataFrame(
        {
            "time": pd.date_range("2025-01-01", periods=2, freq="h"),
            "temperature_2m": [20.0, 21.0],
            "previous_day_temperature_1h": [19.0, 20.0],
            "temperature_target_1h": [21.0, 22.0],
            "temperature_target_6h": [22.0, 23.0],
            "temperature_target_12h": [23.0, 24.0],
            "temperature_target_24h": [24.0, 25.0],
        }
    )
    assert get_advanced_feature_columns(data) == ["temperature_2m"]

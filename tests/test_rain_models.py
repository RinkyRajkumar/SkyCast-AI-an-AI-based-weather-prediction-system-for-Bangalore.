"""Tests for rain target creation, estimators, metrics, and persistence."""

import joblib
import numpy as np
import pandas as pd
import pytest

from src.evaluate import classification_metrics, regression_metrics
from src.train_rain_models import build_classifier, build_regressor, create_rain_targets


@pytest.fixture
def classification_data() -> tuple[pd.DataFrame, pd.Series]:
    rng = np.random.default_rng(7)
    features = pd.DataFrame(
        {
            "precipitation": rng.uniform(0, 2, 60),
            "relative_humidity_2m": rng.uniform(40, 95, 60),
        }
    )
    features.loc[3, "relative_humidity_2m"] = np.nan
    target = pd.Series(([0, 0, 1, 0, 1] * 12), dtype=int)
    return features, target


def test_rain_target_creation_uses_future_window() -> None:
    data = pd.DataFrame({"precipitation": [0.0, 1.0, 0.0, 2.0, 0.0, 3.0, 0.0, 4.0]})
    targeted = create_rain_targets(data)
    assert targeted["rain_amount_target_1h"].iloc[0] == 1.0
    assert targeted["rain_occurrence_target_1h"].iloc[:4].tolist() == [1.0, 0.0, 1.0, 0.0]
    assert targeted["rain_amount_target_6h"].iloc[0] == 6.0
    assert np.isnan(targeted["rain_amount_target_6h"].iloc[-1])


@pytest.mark.parametrize(
    ("model_name", "parameters"),
    [
        ("logistic_regression", {"C": 0.5}),
        (
            "random_forest_classifier",
            {"n_estimators": 6, "max_depth": 3, "min_samples_leaf": 1, "max_features": 1.0},
        ),
        (
            "hist_gradient_boosting_classifier",
            {"learning_rate": 0.1, "max_iter": 8, "max_leaf_nodes": 7, "l2_regularization": 0.0},
        ),
    ],
)
def test_classifier_prediction_shape_and_probability_range(
    classification_data: tuple[pd.DataFrame, pd.Series],
    model_name: str,
    parameters: dict[str, object],
) -> None:
    features, target = classification_data
    model = build_classifier(model_name, parameters)
    model.fit(features, target)
    probabilities = model.predict_proba(features)[:, 1]
    assert probabilities.shape == target.shape
    assert ((probabilities >= 0) & (probabilities <= 1)).all()


@pytest.mark.parametrize(
    ("model_name", "parameters"),
    [
        (
            "random_forest_regressor",
            {"n_estimators": 6, "max_depth": 3, "min_samples_leaf": 1, "max_features": 1.0},
        ),
        (
            "hist_gradient_boosting_regressor",
            {"learning_rate": 0.1, "max_iter": 8, "max_leaf_nodes": 7, "l2_regularization": 0.0},
        ),
    ],
)
def test_rainfall_prediction_shape(
    classification_data: tuple[pd.DataFrame, pd.Series],
    model_name: str,
    parameters: dict[str, object],
) -> None:
    features, _ = classification_data
    target = features["precipitation"].fillna(0)
    model = build_regressor(model_name, parameters)
    model.fit(features, target)
    assert model.predict(features).shape == target.shape


def test_rain_metric_calculation() -> None:
    actual = pd.Series([0, 1, 1, 0])
    metrics = classification_metrics(actual, np.array([0.1, 0.8, 0.4, 0.7]), threshold=0.5)
    assert metrics["precision"] == pytest.approx(0.5)
    assert metrics["recall"] == pytest.approx(0.5)
    assert metrics["f1"] == pytest.approx(0.5)
    assert metrics["roc_auc"] == pytest.approx(0.75)
    assert 0 <= metrics["brier_score"] <= 1

    regression = regression_metrics(pd.Series([0.0, 1.0]), np.array([0.0, 2.0]))
    assert regression["mae"] == pytest.approx(0.5)
    assert regression["rmse"] == pytest.approx(np.sqrt(0.5))


def test_rain_model_saving_and_loading(
    classification_data: tuple[pd.DataFrame, pd.Series], tmp_path
) -> None:
    features, target = classification_data
    model = build_classifier("logistic_regression", {"C": 1.0})
    model.fit(features, target)
    artifact = {"model": model, "feature_columns": features.columns.tolist(), "threshold": 0.5}
    path = tmp_path / "rain_classifier.joblib"
    joblib.dump(artifact, path)
    loaded = joblib.load(path)
    assert np.allclose(
        artifact["model"].predict_proba(features),
        loaded["model"].predict_proba(features[loaded["feature_columns"]]),
    )

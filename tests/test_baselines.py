"""Tests for baseline prediction and artifact persistence."""

import joblib
import pandas as pd

from src.baselines import MonthHourAverageBaseline, PersistenceBaseline, PreviousDayBaseline


def test_baseline_predictions() -> None:
    train = pd.DataFrame(
        {
            "temperature_2m": [20.0, 21.0, 22.0],
            "previous_day_temperature_1h": [18.0, 19.0, 20.0],
            "month": [1, 1, 2],
            "hour": [0, 0, 1],
            "time": pd.to_datetime(["2015-01-01 00:00", "2015-01-02 00:00", "2015-02-01 01:00"]),
        }
    )
    target = pd.Series([24.0, 26.0, 30.0])

    assert PersistenceBaseline().predict(train).tolist() == [20.0, 21.0, 22.0]
    assert PreviousDayBaseline(horizon_hours=1).predict(train).tolist() == [18.0, 19.0, 20.0]
    climatology = MonthHourAverageBaseline().fit(train, target)
    predict_data = pd.DataFrame(
        {
            "month": [1, 2, 12],
            "hour": [0, 1, 23],
            "time": pd.to_datetime(["2015-01-03 00:00", "2015-02-02 01:00", "2015-12-01 23:00"]),
        }
    )
    assert climatology.predict(predict_data).tolist() == [25.0, 30.0, target.mean()]


def test_model_saving_and_loading(tmp_path) -> None:
    model = PersistenceBaseline()
    path = tmp_path / "persistence.joblib"
    joblib.dump(model, path)
    loaded = joblib.load(path)
    features = pd.DataFrame({"temperature_2m": [23.5]})
    assert loaded.predict(features).tolist() == [23.5]

"""Reusable baseline temperature predictors."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class PersistenceBaseline:
    """Predict that future temperature equals the current temperature."""

    column: str = "temperature_2m"

    def fit(self, features: pd.DataFrame, target: pd.Series) -> "PersistenceBaseline":
        """Provide an estimator-compatible no-op fit method."""
        return self

    def predict(self, features: pd.DataFrame) -> np.ndarray:
        """Return the current temperature for every row."""
        return features[self.column].to_numpy(dtype=float)


@dataclass
class PreviousDayBaseline:
    """Predict using the temperature one day before the forecast target time."""

    horizon_hours: int = 1

    def fit(self, features: pd.DataFrame, target: pd.Series) -> "PreviousDayBaseline":
        """Provide an estimator-compatible no-op fit method."""
        return self

    def predict(self, features: pd.DataFrame) -> np.ndarray:
        """Return the previous-day temperature for every row."""
        column = f"previous_day_temperature_{self.horizon_hours}h"
        return features[column].to_numpy(dtype=float)


@dataclass
class MonthHourAverageBaseline:
    """Predict the training-set mean target for each month/hour combination."""

    horizon_hours: int = 0
    averages: dict[tuple[int, int], float] = field(default_factory=dict)
    fallback: float = float("nan")

    def fit(self, features: pd.DataFrame, target: pd.Series) -> "MonthHourAverageBaseline":
        """Learn month/hour target averages and a global fallback from training data."""
        target_time = pd.to_datetime(features["time"]) + pd.Timedelta(hours=self.horizon_hours)
        fit_frame = pd.DataFrame(
            {"month": target_time.dt.month, "hour": target_time.dt.hour, "target": target}
        ).dropna(subset=["target"])
        grouped = fit_frame.groupby(["month", "hour"], observed=True)["target"].mean()
        self.averages = {(int(month), int(hour)): float(value) for (month, hour), value in grouped.items()}
        self.fallback = float(fit_frame["target"].mean())
        return self

    def predict(self, features: pd.DataFrame) -> np.ndarray:
        """Return month/hour climatology predictions with the training mean as fallback."""
        target_time = pd.to_datetime(features["time"]) + pd.Timedelta(hours=self.horizon_hours)
        return np.asarray(
            [
                self.averages.get((int(month), int(hour)), self.fallback)
                for month, hour in zip(target_time.dt.month, target_time.dt.hour)
            ],
            dtype=float,
        )

"""Tests for fixed chronological data splits."""

import pandas as pd

from src.splits import chronological_split, horizon_safe_split


def split_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "time": [
                pd.Timestamp("2015-01-01 00:00"),
                pd.Timestamp("2022-12-31 23:00"),
                pd.Timestamp("2023-01-01 00:00"),
                pd.Timestamp("2024-12-31 23:00"),
                pd.Timestamp("2025-01-01 00:00"),
                pd.Timestamp("2025-12-31 23:00"),
            ],
            "value": range(6),
        }
    )


def test_chronological_split_boundaries() -> None:
    splits = chronological_split(split_fixture())
    assert splits["train"]["time"].dt.year.unique().tolist() == [2015, 2022]
    assert splits["validation"]["time"].dt.year.unique().tolist() == [2023, 2024]
    assert splits["test"]["time"].dt.year.unique().tolist() == [2025]
    assert all(frame["time"].is_monotonic_increasing for frame in splits.values())


def test_splits_do_not_overlap() -> None:
    splits = chronological_split(split_fixture())
    timestamps = [set(frame["time"]) for frame in splits.values()]
    assert timestamps[0].isdisjoint(timestamps[1])
    assert timestamps[0].isdisjoint(timestamps[2])
    assert timestamps[1].isdisjoint(timestamps[2])


def test_forecast_targets_do_not_cross_split_boundaries() -> None:
    frame = split_fixture()
    train = horizon_safe_split(frame, "train", 24)
    validation = horizon_safe_split(frame, "validation", 24)
    assert (train["time"] + pd.Timedelta(hours=24) <= pd.Timestamp("2022-12-31 23:59:59")).all()
    assert (
        validation["time"] + pd.Timedelta(hours=24)
        <= pd.Timestamp("2024-12-31 23:59:59")
    ).all()

"""Chronological split utilities for SkyCast AI."""

from __future__ import annotations

import pandas as pd

from src import config


def chronological_split(data: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Split feature data into fixed train, validation, and test calendar periods."""
    if "time" not in data.columns:
        raise ValueError("Data must contain a 'time' column")
    frame = data.copy()
    frame["time"] = pd.to_datetime(frame["time"], errors="coerce")
    if frame["time"].isna().any():
        raise ValueError("Split input contains invalid timestamps")
    frame = frame.sort_values("time").reset_index(drop=True)

    train = frame.loc[frame["time"] <= pd.Timestamp(config.TRAIN_END)].copy()
    validation = frame.loc[
        frame["time"].between(config.VALIDATION_START, config.VALIDATION_END)
    ].copy()
    test = frame.loc[frame["time"].between(config.TEST_START, config.TEST_END)].copy()
    return {"train": train, "validation": validation, "test": test}


def horizon_safe_split(data: pd.DataFrame, split_name: str, horizon: int) -> pd.DataFrame:
    """Return one split after removing rows whose forecast target crosses its end boundary."""
    splits = chronological_split(data)
    if split_name not in splits:
        raise ValueError(f"Unknown split name: {split_name}")
    end_by_split = {
        "train": pd.Timestamp(config.TRAIN_END),
        "validation": pd.Timestamp(config.VALIDATION_END),
        "test": pd.Timestamp(config.TEST_END),
    }
    split = splits[split_name]
    target_time = split["time"] + pd.Timedelta(hours=horizon)
    return split.loc[target_time <= end_by_split[split_name]].copy()

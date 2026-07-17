"""Regression checks for the committed end-to-end demo request."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def test_demo_request_is_valid_contiguous_utf8_json() -> None:
    """Keep the browser-upload fixture parseable and inference-ready."""
    path = Path(__file__).resolve().parents[1] / "demo" / "bangalore_recent_observations.json"
    raw = path.read_text(encoding="utf-8")
    assert not raw.startswith("\ufeff")

    observations = json.loads(raw)["observations"]
    assert len(observations) == 169
    required = {
        "timestamp",
        "temperature",
        "relative_humidity",
        "precipitation",
        "surface_pressure",
        "cloud_cover",
        "wind_speed",
        "wind_direction",
    }
    assert all(set(observation) == required for observation in observations)

    timestamps = pd.to_datetime([observation["timestamp"] for observation in observations])
    assert timestamps.is_monotonic_increasing
    assert pd.Series(timestamps).diff().dropna().eq(pd.Timedelta(hours=1)).all()

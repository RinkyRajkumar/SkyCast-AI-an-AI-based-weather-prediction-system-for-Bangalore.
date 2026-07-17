"""Clean and quality-check the collected Bangalore weather dataset."""

from __future__ import annotations

import logging

import pandas as pd

from src import config

LOGGER = logging.getLogger(__name__)
TIME_COLUMN = "time"


def interpolate_small_gaps(series: pd.Series, max_gap: int = 3) -> pd.Series:
    """Time-interpolate only bounded missing runs no longer than ``max_gap`` hours."""
    if not isinstance(series.index, pd.DatetimeIndex):
        raise TypeError("A DatetimeIndex is required for time interpolation")

    missing = series.isna()
    run_id = missing.ne(missing.shift(fill_value=False)).cumsum()
    run_sizes = missing.groupby(run_id).transform("sum")
    eligible = missing & run_sizes.le(max_gap)
    interpolated = series.interpolate(method="time", limit_area="inside")

    result = series.copy()
    result.loc[eligible] = interpolated.loc[eligible]
    return result


def clean_weather_data(raw_data: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    """Clean raw hourly weather data and return it with quality metrics."""
    expected = {TIME_COLUMN, *config.HOURLY_VARIABLES}
    missing_columns = expected.difference(raw_data.columns)
    if missing_columns:
        raise ValueError(f"Raw data is missing required columns: {sorted(missing_columns)}")

    data = raw_data.copy()
    original_rows = len(data)
    data[TIME_COLUMN] = pd.to_datetime(data[TIME_COLUMN], errors="coerce")
    invalid_timestamps = int(data[TIME_COLUMN].isna().sum())
    data = data.dropna(subset=[TIME_COLUMN]).sort_values(TIME_COLUMN)
    duplicates_removed = int(data.duplicated(subset=[TIME_COLUMN]).sum())
    data = data.drop_duplicates(subset=[TIME_COLUMN], keep="first")

    numeric_columns = list(config.HOURLY_VARIABLES)
    for column in numeric_columns:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    missing_before = data[numeric_columns].isna().sum()
    data = data.set_index(TIME_COLUMN)
    for column in numeric_columns:
        data[column] = interpolate_small_gaps(data[column])
    missing_after = data[numeric_columns].isna().sum()

    data["rain_occurrence"] = (data["precipitation"] > 0).astype("int8")
    data = data.reset_index()

    report: dict[str, object] = {
        "input_rows": original_rows,
        "output_rows": len(data),
        "invalid_timestamps_removed": invalid_timestamps,
        "duplicate_timestamps_removed": duplicates_removed,
        "missing_before": missing_before.to_dict(),
        "missing_after": missing_after.to_dict(),
        "values_interpolated": int(missing_before.sum() - missing_after.sum()),
    }
    return data, report


def log_quality_report(report: dict[str, object]) -> None:
    """Log a concise cleaning and missing-value report."""
    LOGGER.info(
        "Quality report | input=%s output=%s invalid_times=%s duplicates=%s interpolated=%s",
        report["input_rows"],
        report["output_rows"],
        report["invalid_timestamps_removed"],
        report["duplicate_timestamps_removed"],
        report["values_interpolated"],
    )
    LOGGER.info("Remaining missing values: %s", report["missing_after"])


def run_cleaning() -> pd.DataFrame:
    """Load the configured raw CSV, clean it, and save the processed CSV."""
    if not config.RAW_DATA_FILE.exists():
        raise FileNotFoundError(
            f"Raw data file not found: {config.RAW_DATA_FILE}. Run python -m src.collect_data first."
        )
    raw_data = pd.read_csv(config.RAW_DATA_FILE)
    cleaned_data, report = clean_weather_data(raw_data)
    config.PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    cleaned_data.to_csv(config.PROCESSED_DATA_FILE, index=False)
    LOGGER.info("Saved cleaned data to %s", config.PROCESSED_DATA_FILE)
    log_quality_report(report)
    return cleaned_data


def main() -> int:
    """Run the cleaning command and return a process exit code."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    try:
        run_cleaning()
    except (FileNotFoundError, OSError, ValueError, TypeError) as exc:
        LOGGER.error("Cleaning failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

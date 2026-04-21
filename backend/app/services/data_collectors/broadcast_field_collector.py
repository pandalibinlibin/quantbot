"""
Broadcast Field Collector - Reusable infrastructure for downloading
and broadcasting non-per-instrument and non-daily fields.

Design Principle (approved 2026-04-21):
- If a field is not daily -> resample to daily (ffill)
- If a field is not per-instrument -> broadcast to all instruments
- After broadcast, the field is indistinguishable from regular OHLCV data
  and flows through the existing normalize -> dump_bin pipeline unchanged

Usage:
- User tells Cascade to "download shibor 7-day"
- Cascade writes code calling tushare API + broadcast_field()
- broadcast_field() auto-detects frequency/scope and injects into CSVs
- Existing pipeline (normalize -> dump_bin) handles the rest
"""

import logging
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger(__name__)

# Registry of broadcast field names.
# Updated when user adds new fields via inject_broadcast_fields().
# Used by factor_storage.py to distinguish raw fields from computed factors.
BROADCAST_FIELD_NAMES: set = {
    "shibor_1y",
}


def get_broadcast_field_names() -> set:
    """Return the set of all registered broadcast field names."""
    return BROADCAST_FIELD_NAMES.copy()


def detect_frequency(df: pd.DataFrame, date_col: str = "date") -> str:
    """
    Auto-detect data frequency from date column gaps.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with a date column
    date_col : str
        Name of the date column

    Returns
    -------
    str
        'daily', 'monthly', or 'quarterly'
    """
    if len(df) < 2:
        return "daily"

    dates = pd.to_datetime(df[date_col]).sort_values()
    gaps = dates.diff().dropna()
    median_gap_days = gaps.median().days

    if median_gap_days <= 7:
        return "daily"
    elif median_gap_days <= 45:
        return "monthly"
    else:
        return "quarterly"


def resample_to_daily(
    series: pd.Series,
    trading_calendar: Optional[List[pd.Timestamp]] = None,
) -> pd.Series:
    """
    Resample a non-daily series to daily frequency using forward-fill.

    Parameters
    ----------
    series : pd.Series
        Series with DatetimeIndex containing the values
    trading_calendar : list, optional
        Trading calendar dates to align to. If None, uses business days.

    Returns
    -------
    pd.Series
        Daily-frequency series, forward-filled
    """
    if trading_calendar is not None and len(trading_calendar) > 0:
        daily_index = pd.DatetimeIndex(trading_calendar)
        # Filter to the range of our data
        daily_index = daily_index[
            (daily_index >= series.index.min()) & (daily_index <= series.index.max())
        ]
    else:
        # Fall back to business days
        daily_index = pd.bdate_range(
            start=series.index.min(),
            end=series.index.max(),
        )

    # Reindex and forward-fill
    daily_series = series.reindex(daily_index).ffill()
    return daily_series


def broadcast_field(
    raw_df: pd.DataFrame,
    date_col: str,
    value_col: str,
    field_name: str,
    csv_dir: Path,
    trading_calendar: Optional[List[pd.Timestamp]] = None,
) -> int:
    """
    Core broadcast function: auto-detect -> resample -> inject into instrument CSVs.

    Auto-detection rules:
    - Frequency: median date gap > 7 days -> not daily -> resample with ffill
    - Scope: no 'ts_code' column -> global -> broadcast to all instruments

    After injection, the field appears as a regular column in each instrument CSV
    and flows through the existing normalize -> dump_bin pipeline unchanged.

    Parameters
    ----------
    raw_df : pd.DataFrame
        Raw data from tushare API call
    date_col : str
        Name of the date column in raw_df (e.g., 'date', 'month', 'quarter')
    value_col : str
        Name of the value column to extract (e.g., '1w', 'nt_yoy')
    field_name : str
        Storage name for the field (becomes {field_name}.day.bin)
    csv_dir : Path
        Directory containing per-instrument CSV files
    trading_calendar : list, optional
        Trading calendar for resampling alignment

    Returns
    -------
    int
        Number of instrument CSVs updated
    """
    csv_dir = Path(csv_dir)

    if raw_df is None or raw_df.empty:
        logger.warning(f"broadcast_field: empty data for '{field_name}'")
        return 0

    if value_col not in raw_df.columns:
        logger.error(
            f"broadcast_field: column '{value_col}' not found in data. "
            f"Available: {raw_df.columns.tolist()}"
        )
        return 0

    # Step 1: Extract value series with date index
    df = raw_df[[date_col, value_col]].copy()
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.dropna(subset=[value_col])
    df = df.set_index(date_col).sort_index()
    df = df[~df.index.duplicated(keep="last")]
    series = df[value_col].astype(np.float64)

    logger.info(
        f"broadcast_field '{field_name}': {len(series)} raw records, "
        f"range {series.index.min().date()} to {series.index.max().date()}"
    )

    # Step 2: Auto-detect frequency
    freq = detect_frequency(raw_df, date_col)
    logger.info(f"broadcast_field '{field_name}': detected frequency = {freq}")

    # Step 3: Resample to daily if needed
    if freq != "daily":
        series = resample_to_daily(series, trading_calendar)
        logger.info(
            f"broadcast_field '{field_name}': resampled to {len(series)} daily records"
        )

    # Step 4: Auto-detect scope
    is_global = "ts_code" not in raw_df.columns
    logger.info(
        f"broadcast_field '{field_name}': "
        f"scope = {'global (broadcast to all)' if is_global else 'per-instrument'}"
    )

    # Step 5: Inject into instrument CSVs
    csv_files = list(csv_dir.glob("*.csv"))
    if not csv_files:
        logger.warning(f"broadcast_field: no CSV files found in {csv_dir}")
        return 0

    updated_count = 0
    for csv_file in csv_files:
        try:
            inst_df = pd.read_csv(csv_file, index_col=0, parse_dates=True)
            if inst_df.empty:
                continue

            if not isinstance(inst_df.index, pd.DatetimeIndex):
                inst_df.index = pd.to_datetime(inst_df.index)

            # Align broadcast data to instrument dates via reindex + ffill
            aligned = series.reindex(inst_df.index, method="ffill")
            inst_df[field_name] = aligned

            inst_df.to_csv(csv_file, index=True)
            updated_count += 1

        except Exception as e:
            logger.warning(
                f"broadcast_field: failed to inject into {csv_file.name}: {e}"
            )

    logger.info(
        f"broadcast_field '{field_name}': "
        f"injected into {updated_count}/{len(csv_files)} instrument CSVs"
    )
    return updated_count


def get_trading_calendar_for_broadcast() -> Optional[List[pd.Timestamp]]:
    """
    Get trading calendar for resampling alignment.
    Reads from existing Qlib calendar file, falls back to Tushare API.

    Returns
    -------
    list or None
        List of trading day timestamps, or None if unavailable
    """
    # Try Qlib calendar file first (fastest)
    try:
        from app.core.config import settings

        calendar_file = Path(settings.QLIB_DATA_PATH) / "calendars" / "day.txt"
        if calendar_file.exists():
            with open(calendar_file, "r") as f:
                lines = [line.strip() for line in f if line.strip()]
            if lines:
                dates = [pd.Timestamp(line.split()[0]) for line in lines]
                logger.debug(f"Loaded {len(dates)} dates from Qlib calendar")
                return sorted(dates)
    except Exception as e:
        logger.warning(f"Failed to read Qlib calendar: {e}")

    # Fallback to Tushare trading calendar API
    try:
        from app.services.data_collectors.tushare_collector import (
            TushareDataCollector,
        )

        date_strings = TushareDataCollector.get_trading_calendar()
        if date_strings:
            dates = [pd.Timestamp(d) for d in date_strings]
            logger.debug(f"Loaded {len(dates)} dates from Tushare calendar")
            return dates
    except Exception as e:
        logger.warning(f"Failed to get Tushare calendar: {e}")

    return None


def inject_broadcast_fields(csv_dir: Path, start_date: str, end_date: str) -> bool:
    """
    Download and inject all broadcast fields into instrument CSVs.

    Called between data collection and normalization/conversion stages
    in the data pipeline. Add new broadcast field downloads here
    when the user requests them.

    Parameters
    ----------
    csv_dir : Path
        Directory containing per-instrument CSV files
    start_date : str
        Start date in YYYY-MM-DD format
    end_date : str
        End date in YYYY-MM-DD format

    Returns
    -------
    bool
        True if any broadcast fields were injected into CSVs
    """
    csv_dir = Path(csv_dir)
    csv_files = list(csv_dir.glob("*.csv"))
    if not csv_files:
        logger.debug("inject_broadcast_fields: no CSV files, skipping")
        return False

    trading_calendar = get_trading_calendar_for_broadcast()

    # ================================================================
    # BROADCAST FIELD DOWNLOADS
    # Each function: call tushare API -> broadcast_field() -> inject into CSVs
    # ================================================================

    # Use full CSV date range (not just incremental range) to ensure
    # broadcast fields cover the same period as OHLCV data
    full_start, full_end = _get_csv_date_range(csv_dir, start_date, end_date)

    changed = False

    count = _download_and_broadcast_shibor_1y(
        csv_dir, full_start, full_end, trading_calendar
    )
    if count and count > 0:
        changed = True

    return changed


def _get_csv_date_range(csv_dir: Path, fallback_start: str, fallback_end: str) -> tuple:
    """
    Read the actual date range from existing CSV files.

    For incremental updates, the pipeline passes only the recent date range,
    but broadcast fields need to cover the full OHLCV date range.
    Falls back to the provided start/end if CSV reading fails.

    Returns
    -------
    tuple
        (start_date, end_date) in YYYY-MM-DD format
    """
    try:
        csv_files = list(Path(csv_dir).glob("*.csv"))
        if csv_files:
            sample_df = pd.read_csv(csv_files[0], index_col=0, parse_dates=True)
            if not sample_df.empty:
                actual_start = sample_df.index.min().strftime("%Y-%m-%d")
                actual_end = sample_df.index.max().strftime("%Y-%m-%d")
                logger.debug(f"CSV date range: {actual_start} to {actual_end}")
                return actual_start, actual_end
    except Exception as e:
        logger.warning(f"Failed to read CSV date range: {e}")

    return fallback_start, fallback_end


def _download_and_broadcast_shibor_1y(
    csv_dir: Path,
    start_date: str,
    end_date: str,
    trading_calendar: Optional[List[pd.Timestamp]],
) -> int:
    """
    Download Shibor 1-year rate from Tushare and broadcast to all instruments.

    API: pro.shibor()
    Source column: '1y' (1-year Shibor rate, %)
    Target field: 'shibor_1y'
    Frequency: daily (no resample needed)
    Scope: global (no ts_code -> broadcast to all)

    Returns
    -------
    int
        Number of instrument CSVs updated, 0 on failure
    """
    try:
        import tushare as ts
        from app.core.config import settings

        token = settings.TUSHARE_TOKEN
        if not token:
            logger.warning("TUSHARE_TOKEN not configured, skipping shibor_1y")
            return 0

        ts.set_token(token)
        pro = ts.pro_api()

        # Convert YYYY-MM-DD to YYYYMMDD for tushare
        ts_start = start_date.replace("-", "")
        ts_end = end_date.replace("-", "")

        logger.info(f"Downloading Shibor 1Y: {ts_start} to {ts_end}")
        df = pro.shibor(start_date=ts_start, end_date=ts_end)

        if df is None or df.empty:
            logger.warning("Shibor API returned no data")
            return 0

        logger.info(f"Shibor 1Y: received {len(df)} rows")

        count = broadcast_field(
            raw_df=df,
            date_col="date",
            value_col="1y",
            field_name="shibor_1y",
            csv_dir=csv_dir,
            trading_calendar=trading_calendar,
        )

        logger.info(f"Shibor 1Y broadcast complete: {count} instruments updated")
        return count

    except Exception as e:
        logger.error(f"Failed to download/broadcast shibor_1y: {e}")
        return 0

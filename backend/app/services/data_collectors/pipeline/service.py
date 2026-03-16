"""
Data Pipeline Service - Complete incremental update logic.

Supported data sources:
- Tushare: A-share (China) market data
- EOD Historical Data: US stock market data

Educational Notes:
- Detects all missing data segments (beginning, middle, end)
- Downloads only missing time periods
- Handles multiple discontinuous gaps
- Uses collector and normalize components with Qlib optimizations
"""

import uuid
import logging
from pathlib import Path
from typing import Tuple, Optional, List
from datetime import datetime, timedelta
import pandas as pd
import time

from app.core.config import settings


def _filter_anomalous_timestamps(
    df: pd.DataFrame, expected_start: str, expected_end: str
) -> pd.DataFrame:
    """
    Filter out anomalous timestamps that are outside the expected date range.

    This function filters data to ensure only records within the expected
    date range are included, preventing incorrect Qlib calendar generation.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with DatetimeIndex containing the data
    expected_start : str
        Expected start date in YYYY-MM-DD format
    expected_end : str
        Expected end date in YYYY-MM-DD format

    Returns
    -------
    pd.DataFrame
        Filtered DataFrame with only data within expected date range
    """
    if df.empty:
        return df

    original_count = len(df)

    # Convert expected dates to datetime
    start_date = pd.to_datetime(expected_start).date()
    end_date = pd.to_datetime(expected_end).date()

    # Ensure index is datetime
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    # Filter by date range - keep only data within expected range
    df_filtered = df[(df.index.date >= start_date) & (df.index.date <= end_date)]

    filtered_count = original_count - len(df_filtered)
    if filtered_count > 0:
        logger.warning(
            f"Filtered out {filtered_count} anomalous timestamps outside range "
            f"{expected_start} to {expected_end}. Kept {len(df_filtered)} records."
        )

    return df_filtered


from app.services.data_source_manager import data_source_manager
from app.models import DownloadDataRequest, DownloadTaskResponse

logger = logging.getLogger(__name__)


def execute_data_pipeline(request: DownloadDataRequest) -> DownloadTaskResponse:
    """
    Execute data pipeline with complete incremental update logic.
    """
    task_id = str(uuid.uuid4())

    try:
        current_source = data_source_manager.get_current_source()
        logger.info(
            f"Starting pipeline execution: task_id={task_id}, source={current_source}, stock_pool={request.stock_pool}, incremental={request.incremental}"
        )

        # Step 0: Check data source configuration and handle changes
        config_changed = data_source_manager.check_and_handle_config_change()
        if config_changed:
            logger.info("Data configuration changed, existing data was cleaned up")
            # Force full refresh if source changed
            request.incremental = False

        # Step 1: Handle incremental vs full refresh
        if not request.incremental:
            # Full refresh: clear existing data
            from app.services.data_utils import clear_qlib_data

            clear_success, clear_message, cleared_mb = clear_qlib_data()
            if not clear_success:
                return DownloadTaskResponse(
                    task_id=task_id,
                    status="failed",
                    message=f"Failed to clear existing data: {clear_message}",
                )
            logger.info(f"Full refresh: cleared existing data ({cleared_mb} MB)")
            download_ranges = [(request.start_date, request.end_date)]
        else:
            # Incremental update: detect all missing time periods
            download_ranges = _get_missing_date_ranges(
                request.start_date, request.end_date, request.interval
            )
            if not download_ranges:
                return DownloadTaskResponse(
                    task_id=task_id,
                    status="completed",
                    message="No missing data found - existing data covers the requested period",
                )

            ranges_str = ", ".join(
                [f"{start} to {end}" for start, end in download_ranges]
            )
            logger.info(f"Incremental update: downloading missing ranges: {ranges_str}")

        # Step 2: Execute data collection for all missing ranges
        success = False
        message = ""
        current_source = data_source_manager.get_current_source()
        if current_source.lower() == "tushare":
            success, message = _execute_tushare_pipeline(
                stock_pool=request.stock_pool,
                download_ranges=download_ranges,
                incremental=request.incremental,
                interval=request.interval or "1d",
            )
        elif current_source.lower() == "eod":
            success, message = _execute_eod_pipeline(
                stock_pool=request.stock_pool,
                download_ranges=download_ranges,
                incremental=request.incremental,
                interval=request.interval or "1d",
            )
        else:
            success = False
            message = (
                f"Unsupported data source: {current_source}. Supported: tushare, eod"
            )

        # Check if data collection failed
        if not success:
            return DownloadTaskResponse(
                task_id=task_id,
                status="failed",
                message=f"Pipeline execution failed: {message}",
            )

        # Note: metadata.json is saved inside pipeline execution after successful conversion

        # Step 3: Trigger factor computation after successful data collection
        try:
            logger.info("=== FACTOR COMPUTATION START ===")
            logger.info(f"Request interval: {request.interval}")
            logger.info(f"Request incremental: {request.incremental}")
            logger.info(f"Request start_date: {request.start_date}")
            logger.info(f"Request end_date: {request.end_date}")

            from app.services.factor_pipeline import FactorPipeline, UpdateMode
            from app.models import Factor, FactorStatus
            from app.core.db import engine
            from sqlmodel import Session, select

            # Get active factors from database
            with Session(engine) as session:
                statement = select(Factor).where(Factor.status == FactorStatus.ACTIVE)
                active_factors = session.exec(statement).all()
                factor_names = [factor.name for factor in active_factors]

            logger.info(f"Active factors found: {factor_names}")

            if factor_names:
                # Use day frequency (only day-level data supported in stock selection system)
                factor_freq = "day"
                logger.info(f"Factor frequency: {factor_freq}")

                # Initialize factor pipeline with correct frequency
                factor_pipeline = FactorPipeline(freq=factor_freq, max_workers=4)
                logger.info(f"FactorPipeline initialized with freq={factor_freq}")

                # Determine update mode based on incremental flag
                data_collector_mode = "incremental" if request.incremental else "full"

                # For incremental mode, we need to:
                # 1. Re-initialize Qlib to refresh cached calendar data
                # 2. Read the full data date range from calendar
                # 3. Recompute all factors with full date range and overwrite existing data
                if request.incremental:
                    # Re-initialize Qlib to load updated calendar and feature data
                    from app.services.qlib_init_service import get_qlib_init_service

                    qlib_service = get_qlib_init_service()
                    qlib_service.reinitialize()
                    logger.info("Qlib re-initialized after incremental data update")

                    # Read calendar to get full data date range (day-level data only)
                    calendar_file = (
                        Path(settings.QLIB_DATA_PATH) / "calendars" / "day.txt"
                    )

                    if calendar_file.exists():
                        with open(calendar_file, "r") as f:
                            calendar_dates = [
                                line.strip() for line in f if line.strip()
                            ]
                        if calendar_dates:
                            # Extract date part (for minute data, dates include time)
                            factor_start = calendar_dates[0].split()[0]
                            factor_end = calendar_dates[-1].split()[0]
                            logger.info(
                                f"Incremental factor computation: using full calendar range {factor_start} to {factor_end}"
                            )
                        else:
                            factor_start = request.start_date
                            factor_end = request.end_date
                    else:
                        logger.warning(f"Calendar file not found: {calendar_file}")
                        factor_start = request.start_date
                        factor_end = request.end_date
                else:
                    factor_start = request.start_date
                    factor_end = request.end_date

                # Trigger factor computation
                factor_result = factor_pipeline.sync_with_data_collector(
                    factor_names=factor_names,
                    data_collector_mode=data_collector_mode,
                    start_time=factor_start,
                    end_time=factor_end,
                    parallel=True,
                )

                if factor_result.get("successful", 0) > 0:
                    logger.info(
                        f"Factor computation completed: {factor_result['successful']} successful, {factor_result.get('failed', 0)} failed"
                    )
                    # Update success message to include factor computation
                    message = f"{message} + Factor computation: {factor_result['successful']} factors computed"
                else:
                    logger.warning(
                        f"Factor computation failed: {factor_result.get('error', 'Unknown error')}"
                    )
                    message = f"{message} (Factor computation failed)"
            else:
                logger.info("No active factors found, skipping factor computation")

        except Exception as factor_e:
            logger.error(f"Factor computation failed: {factor_e}")
            # Don't fail the entire pipeline if factor computation fails
            message = f"{message} (Factor computation error: {str(factor_e)})"

        # Step 4: Return final result
        mode_text = "incremental update" if request.incremental else "full refresh"
        return DownloadTaskResponse(
            task_id=task_id,
            status="completed",
            message=f"Successfully completed {mode_text}: {message}",
        )

    except Exception as e:
        error_msg = f"Pipeline execution failed: {str(e)}"
        logger.error(error_msg, exc_info=True)

        return DownloadTaskResponse(
            task_id=task_id,
            status="error",
            message="Pipeline execution encountered an error",
        )


def _get_missing_date_ranges(
    requested_start: str, requested_end: str, interval: str = "1d"
) -> List[Tuple[str, str]]:
    """
    Detect all missing date ranges in existing Qlib data.

    Args:
        requested_start: Start date string (YYYY-MM-DD)
        requested_end: End date string (YYYY-MM-DD)
        interval: Data interval ("1d" for day, "1m" for minute)

    Returns:
        List of (start_date, end_date) tuples for missing periods
    """
    try:
        from app.services.qlib_init_service import get_qlib_init_service

        # Use day-level data directory (minute data handled by separate timing system)
        qlib_data_path = Path(settings.QLIB_DATA_PATH)
        calendar_file = qlib_data_path / "calendars" / "day.txt"

        if not qlib_data_path.exists():
            logger.info(
                f"No existing Qlib data found at {qlib_data_path}, will download full range"
            )
            return [(requested_start, requested_end)]

        try:
            # Read calendar directly from file instead of using D.calendar()
            # This avoids issues with Qlib caching and ensures we get the correct frequency
            if not calendar_file.exists():
                logger.info(
                    f"No calendar file found at {calendar_file}, will download full range"
                )
                return [(requested_start, requested_end)]

            with open(calendar_file, "r") as f:
                calendar_lines = [line.strip() for line in f if line.strip()]

            if not calendar_lines:
                logger.info("Calendar file is empty, will download full range")
                return [(requested_start, requested_end)]

            # Extract dates from calendar (for minute data, extract just the date part)
            existing_dates = set()
            for line in calendar_lines:
                # For minute data: "2026-02-11 09:30:00" -> "2026-02-11"
                # For day data: "2026-02-11" -> "2026-02-11"
                date_part = line.split()[0]
                existing_dates.add(date_part)

            logger.info(
                f"Found {len(existing_dates)} unique dates in calendar (interval={interval})"
            )
            # Generate requested date range (business days only)
            requested_start_dt = datetime.strptime(requested_start, "%Y-%m-%d")
            requested_end_dt = datetime.strptime(requested_end, "%Y-%m-%d")

            # Create full requested date range (we'll filter to business days later)
            requested_dates = []
            current_date = requested_start_dt
            while current_date <= requested_end_dt:
                # Simple business day check (Monday=0, Sunday=6)
                if current_date.weekday() < 5:  # Monday to Friday
                    requested_dates.append(current_date.strftime("%Y-%m-%d"))
                current_date += timedelta(days=1)

            # Find missing dates
            missing_dates = []
            for date_str in requested_dates:
                if date_str not in existing_dates:
                    missing_dates.append(date_str)

            if not missing_dates:
                logger.info("No missing dates found in requested range")
                return []

            # Group consecutive missing dates into ranges
            missing_ranges = []
            if missing_dates:
                range_start = missing_dates[0]
                range_end = missing_dates[0]

                for i in range(1, len(missing_dates)):
                    current_date = datetime.strptime(missing_dates[i], "%Y-%m-%d")
                    prev_date = datetime.strptime(missing_dates[i - 1], "%Y-%m-%d")

                    # Check if dates are consecutive (allowing for weekends)
                    days_diff = (current_date - prev_date).days
                    if days_diff <= 3:  # Allow for weekends
                        range_end = missing_dates[i]
                    else:
                        # Gap found, close current range and start new one
                        missing_ranges.append((range_start, range_end))
                        range_start = missing_dates[i]
                        range_end = missing_dates[i]

                # Add the last range
                missing_ranges.append((range_start, range_end))

            logger.info(
                f"Found {len(missing_ranges)} missing date ranges: {missing_ranges}"
            )
            return missing_ranges

        except Exception as e:
            logger.warning(
                f"Failed to analyze existing Qlib data: {str(e)}, will download full range"
            )
            return [(requested_start, requested_end)]

    except Exception as e:
        logger.warning(
            f"Error in missing date range detection: {str(e)}, will download full range"
        )
        return [(requested_start, requested_end)]


def _execute_tushare_pipeline(
    stock_pool: str,
    download_ranges: List[Tuple[str, str]],
    incremental: bool = False,
    interval: str = "1d",
) -> Tuple[bool, str]:
    """
    Execute Tushare data pipeline for A-share market.

    Parameters
    ----------
    stock_pool : str
        Stock pool name (csi300, csi500, csi800, csi1000, dividend)
    download_ranges : List[Tuple[str, str]]
        List of (start_date, end_date) tuples
    incremental : bool
        Whether to perform incremental update
    interval : str
        Data interval (only "1d" supported for Tushare)

    Returns
    -------
    Tuple[bool, str]
        (success, message)
    """
    try:
        from app.services.data_collectors.tushare_collector import TushareDataCollector

        # Map stock_pool to index name
        index_map = {
            "csi300": "CSI300",
            "csi500": "CSI500",
            "csi800": "CSI800",
            "csi1000": "CSI1000",
            "dividend": "DIVIDEND",
        }

        index_name = index_map.get(stock_pool.lower())
        if not index_name:
            return False, f"Unsupported stock pool for Tushare: {stock_pool}"

        # Setup directories
        csv_dir = Path(settings.CSV_DATA_PATH) / "cn_data"
        csv_dir.mkdir(parents=True, exist_ok=True)

        # Initialize collector
        collector = TushareDataCollector(
            save_dir=str(csv_dir),
            index_name=index_name,
            start=download_ranges[0][0],
            end=download_ranges[-1][1],
        )

        # Get instrument list
        instruments = collector.get_instrument_list()
        logger.info(f"Retrieved {len(instruments)} instruments for {stock_pool}")

        total_collected = 0

        # Download data for each missing range
        for range_start, range_end in download_ranges:
            logger.info(f"Downloading data for range: {range_start} to {range_end}")

            range_collected = 0
            failed_instruments = []

            for i, instrument in enumerate(instruments):
                try:
                    df = collector.get_data(
                        symbol=instrument,
                        interval=interval,
                        start_datetime=range_start,
                        end_datetime=range_end,
                    )

                    if df is not None and not df.empty:
                        # Filter anomalous timestamps
                        df = _filter_anomalous_timestamps(df, range_start, range_end)

                        if df.empty:
                            continue

                        # Use normalized instrument format
                        normalized_instrument = collector.normalize_symbol(instrument)
                        csv_file = csv_dir / f"{normalized_instrument}.csv"

                        if incremental and csv_file.exists():
                            # Merge with existing data
                            existing_df = pd.read_csv(
                                csv_file, index_col=0, parse_dates=True
                            )
                            if not isinstance(existing_df.index, pd.DatetimeIndex):
                                existing_df.index = pd.to_datetime(existing_df.index)
                            if not isinstance(df.index, pd.DatetimeIndex):
                                df.index = pd.to_datetime(df.index)

                            combined_df = pd.concat([existing_df, df])
                            combined_df = combined_df[
                                ~combined_df.index.duplicated(keep="last")
                            ]
                            combined_df = combined_df.sort_index()
                            combined_df.to_csv(csv_file, index=True)
                        else:
                            df.to_csv(csv_file, index=True)

                        range_collected += 1

                    # Log progress
                    if (i + 1) % 50 == 0 or (i + 1) == len(instruments):
                        logger.info(
                            f"Progress: {i + 1}/{len(instruments)} instruments processed"
                        )

                except Exception as e:
                    failed_instruments.append(instrument)
                    logger.warning(f"Failed to collect data for {instrument}: {e}")

            total_collected += range_collected
            logger.info(
                f"Range {range_start} to {range_end}: collected {range_collected}/{len(instruments)} instruments"
            )

        if total_collected == 0:
            # For incremental updates, no new data is normal (weekends, holidays, or already up-to-date)
            if incremental:
                return (
                    True,
                    "No new data available (data is already up-to-date or market is closed)",
                )
            else:
                return False, "No data was collected for any range"

        # Data Normalization
        from app.services.data_collectors.normalize import UniversalNormalize

        normalized_dir = csv_dir.parent / "normalized"
        normalized_dir.mkdir(parents=True, exist_ok=True)

        normalizer = UniversalNormalize(source_type="tushare", market="CN")

        normalize_success_count = 0
        for csv_file in csv_dir.glob("*.csv"):
            try:
                df = pd.read_csv(csv_file, index_col=0, parse_dates=True)
                if df.empty:
                    continue

                df = df.reset_index()
                if "index" in df.columns:
                    df = df.rename(columns={"index": "date"})

                if "symbol" not in df.columns:
                    df["symbol"] = csv_file.stem

                normalized_df = normalizer.normalize(df)
                output_file = normalized_dir / csv_file.name
                normalized_df.to_csv(output_file, index=True)
                normalize_success_count += 1

            except Exception as e:
                logger.warning(f"Failed to normalize {csv_file.name}: {e}")

        if normalize_success_count == 0:
            return False, "Data normalization failed"

        logger.info("Data normalization completed successfully")

        # Convert to Qlib format
        from app.services.data_utils import convert_csv_to_qlib_format_impl

        qlib_freq = "day"
        convert_success, convert_message = convert_csv_to_qlib_format_impl(
            csv_dir=str(csv_dir), freq=qlib_freq, incremental=incremental
        )
        if not convert_success:
            return False, f"Qlib format conversion failed: {convert_message}"

        logger.info("Qlib format conversion completed successfully")

        # Save metadata
        try:
            import json
            from datetime import datetime
            from app.services.data_utils import get_qlib_dir_for_freq

            metadata = {
                "source": "tushare",
                "stock_pool": stock_pool,
                "market": "CN",
                "region": "cn",
                "interval": interval,
                "download_date": datetime.now().isoformat(),
                "instruments_count": total_collected,
                "date_ranges": [(start, end) for start, end in download_ranges],
            }

            qlib_data_dir = get_qlib_dir_for_freq(qlib_freq)
            metadata_file = Path(qlib_data_dir) / "metadata.json"
            with open(metadata_file, "w") as f:
                json.dump(metadata, f, indent=2)

            logger.info(f"Saved metadata: stock_pool={stock_pool}, dir={qlib_data_dir}")

        except Exception as e:
            logger.warning(f"Failed to save metadata: {e}")

        return (
            True,
            f"Tushare pipeline completed: {total_collected} instruments collected",
        )

    except Exception as e:
        error_msg = f"Tushare pipeline execution failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg


def _execute_eod_pipeline(
    stock_pool: str,
    download_ranges: List[Tuple[str, str]],
    incremental: bool = False,
    interval: str = "1d",
) -> Tuple[bool, str]:
    """
    Execute EOD Historical Data pipeline for US market.

    Parameters
    ----------
    stock_pool : str
        Stock pool name (sp500, nasdaq100, djia)
    download_ranges : List[Tuple[str, str]]
        List of (start_date, end_date) tuples
    incremental : bool
        Whether to perform incremental update
    interval : str
        Data interval (only "1d" supported)

    Returns
    -------
    Tuple[bool, str]
        (success, message)
    """
    try:
        from app.services.data_collectors.eod_collector import EODDataCollector

        # Map stock_pool to index name
        index_map = {
            "sp500": "SP500",
            "nasdaq100": "NASDAQ100",
            "djia": "DJIA",
        }

        index_name = index_map.get(stock_pool.lower())
        if not index_name:
            return False, f"Unsupported stock pool for EOD: {stock_pool}"

        # Setup directories
        csv_dir = Path(settings.CSV_DATA_PATH) / "us_data"
        csv_dir.mkdir(parents=True, exist_ok=True)

        # Initialize collector
        collector = EODDataCollector(
            save_dir=str(csv_dir),
            index_name=index_name,
            start=download_ranges[0][0],
            end=download_ranges[-1][1],
        )

        # Get instrument list
        instruments = collector.get_instrument_list()
        logger.info(f"Retrieved {len(instruments)} instruments for {stock_pool}")

        total_collected = 0

        # Download data for each missing range
        for range_start, range_end in download_ranges:
            logger.info(f"Downloading data for range: {range_start} to {range_end}")

            range_collected = 0
            failed_instruments = []

            for i, instrument in enumerate(instruments):
                try:
                    df = collector.get_data(
                        symbol=instrument,
                        interval=interval,
                        start_datetime=range_start,
                        end_datetime=range_end,
                    )

                    if df is not None and not df.empty:
                        # Filter anomalous timestamps
                        df = _filter_anomalous_timestamps(df, range_start, range_end)

                        if df.empty:
                            continue

                        # Use normalized instrument format
                        normalized_instrument = collector.normalize_symbol(instrument)
                        csv_file = csv_dir / f"{normalized_instrument}.csv"

                        if incremental and csv_file.exists():
                            # Merge with existing data
                            existing_df = pd.read_csv(
                                csv_file, index_col=0, parse_dates=True
                            )
                            if not isinstance(existing_df.index, pd.DatetimeIndex):
                                existing_df.index = pd.to_datetime(existing_df.index)
                            if not isinstance(df.index, pd.DatetimeIndex):
                                df.index = pd.to_datetime(df.index)

                            combined_df = pd.concat([existing_df, df])
                            combined_df = combined_df[
                                ~combined_df.index.duplicated(keep="last")
                            ]
                            combined_df = combined_df.sort_index()
                            combined_df.to_csv(csv_file, index=True)
                        else:
                            df.to_csv(csv_file, index=True)

                        range_collected += 1

                    # Log progress
                    if (i + 1) % 50 == 0 or (i + 1) == len(instruments):
                        logger.info(
                            f"Progress: {i + 1}/{len(instruments)} instruments processed"
                        )

                except Exception as e:
                    failed_instruments.append(instrument)
                    logger.warning(f"Failed to collect data for {instrument}: {e}")

            total_collected += range_collected
            logger.info(
                f"Range {range_start} to {range_end}: collected {range_collected}/{len(instruments)} instruments"
            )

        if total_collected == 0:
            # For incremental updates, no new data is normal (weekends, holidays, or already up-to-date)
            if incremental:
                return (
                    True,
                    "No new data available (data is already up-to-date or market is closed)",
                )
            else:
                return False, "No data was collected for any range"

        # Data Normalization
        from app.services.data_collectors.normalize import UniversalNormalize

        normalized_dir = csv_dir.parent / "normalized"
        normalized_dir.mkdir(parents=True, exist_ok=True)

        normalizer = UniversalNormalize(source_type="eod", market="US")

        normalize_success_count = 0
        for csv_file in csv_dir.glob("*.csv"):
            try:
                df = pd.read_csv(csv_file, index_col=0, parse_dates=True)
                if df.empty:
                    continue

                df = df.reset_index()
                if "index" in df.columns:
                    df = df.rename(columns={"index": "date"})

                if "symbol" not in df.columns:
                    df["symbol"] = csv_file.stem

                normalized_df = normalizer.normalize(df)
                output_file = normalized_dir / csv_file.name
                normalized_df.to_csv(output_file, index=True)
                normalize_success_count += 1

            except Exception as e:
                logger.warning(f"Failed to normalize {csv_file.name}: {e}")

        if normalize_success_count == 0:
            return False, "Data normalization failed"

        logger.info("Data normalization completed successfully")

        # Convert to Qlib format
        from app.services.data_utils import convert_csv_to_qlib_format_impl

        qlib_freq = "day"
        convert_success, convert_message = convert_csv_to_qlib_format_impl(
            csv_dir=str(csv_dir), freq=qlib_freq, incremental=incremental
        )
        if not convert_success:
            return False, f"Qlib format conversion failed: {convert_message}"

        logger.info("Qlib format conversion completed successfully")

        # Save metadata
        try:
            import json
            from datetime import datetime
            from app.services.data_utils import get_qlib_dir_for_freq

            metadata = {
                "source": "eod",
                "stock_pool": stock_pool,
                "market": "US",
                "region": "us",
                "interval": interval,
                "download_date": datetime.now().isoformat(),
                "instruments_count": total_collected,
                "date_ranges": [(start, end) for start, end in download_ranges],
            }

            qlib_data_dir = get_qlib_dir_for_freq(qlib_freq)
            metadata_file = Path(qlib_data_dir) / "metadata.json"
            with open(metadata_file, "w") as f:
                json.dump(metadata, f, indent=2)

            logger.info(f"Saved metadata: stock_pool={stock_pool}, dir={qlib_data_dir}")

        except Exception as e:
            logger.warning(f"Failed to save metadata: {e}")

        return (
            True,
            f"EOD pipeline completed: {total_collected} instruments collected",
        )

    except Exception as e:
        error_msg = f"EOD pipeline execution failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg

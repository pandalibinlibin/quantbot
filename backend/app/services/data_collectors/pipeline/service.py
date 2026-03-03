"""
Data Pipeline Service - Complete incremental update logic.

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
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from app.core.config import settings


def _filter_anomalous_timestamps(
    df: pd.DataFrame, expected_start: str, expected_end: str
) -> pd.DataFrame:
    """
    Filter out anomalous timestamps that are outside the expected date range.

    This function addresses Yahoo Finance API issues where it sometimes returns
    data outside the requested date range, causing incorrect Qlib calendar generation.

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
        if current_source.lower() == "yahoo":
            success, message = _execute_yahoo_pipeline(
                stock_pool=request.stock_pool,
                download_ranges=download_ranges,
                incremental=request.incremental,
                interval=request.interval or "1d",  # 添加这行
            )

            # Yahoo pipeline completed, continue to factor computation

        else:
            success = False
            message = f"Unsupported data source: {current_source}"

        # Check if data collection failed
        if not success:
            return DownloadTaskResponse(
                task_id=task_id,
                status="failed",
                message=f"Pipeline execution failed: {message}",
            )

        # Note: metadata.json is saved inside _execute_yahoo_pipeline after successful conversion

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
                # Convert interval to factor engine frequency format
                factor_freq = "1min" if request.interval == "1m" else "day"
                logger.info(
                    f"Factor frequency: {factor_freq} (from interval: {request.interval})"
                )

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

                    # Read calendar to get full data date range
                    if factor_freq == "1min":
                        calendar_file = (
                            Path(settings.QLIB_DATA_PATH_1MIN)
                            / "calendars"
                            / "1min.txt"
                        )
                    else:
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

        # Determine which data directory and calendar to use based on interval
        is_minute_data = interval == "1m"
        if is_minute_data:
            qlib_data_path = Path(settings.QLIB_DATA_PATH_1MIN)
            calendar_file = qlib_data_path / "calendars" / "1min.txt"
        else:
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


def _download_benchmark_index(
    stock_pool: str,
    collector,
    csv_dir: Path,
    download_ranges: List[Tuple[str, str]],
    interval: str = "1d",
) -> bool:
    """
    Download benchmark index data for backtest comparison.

    This function downloads the benchmark index corresponding to the stock_pool:
    - CSI300 -> SH000300 (000300.SS)
    - CSI500 -> SH000905 (000905.SS)
    - SP500 -> SPY
    - NASDAQ100 -> QQQ

    Parameters
    ----------
    stock_pool : str
        Stock pool name (csi300, csi500, sp500, nasdaq100)
    collector : YahooDataCollector
        Initialized collector instance for downloading data
    csv_dir : Path
        Directory to save CSV files
    download_ranges : List[Tuple[str, str]]
        List of (start_date, end_date) tuples
    interval : str
        Data interval ("1d" or "1min")

    Returns
    -------
    bool
        True if benchmark download succeeded, False otherwise
    """
    from app.services.data_collectors.yahoo_collector import BENCHMARK_CONFIG

    index_upper = stock_pool.upper()
    if index_upper not in BENCHMARK_CONFIG:
        logger.warning(f"No benchmark config for stock_pool: {stock_pool}")
        return False

    benchmark_info = BENCHMARK_CONFIG[index_upper]
    yahoo_symbol = benchmark_info["yahoo_symbol"]
    qlib_symbol = benchmark_info["qlib_symbol"]

    logger.info(f"Downloading benchmark index: {yahoo_symbol} -> {qlib_symbol}")

    try:
        for range_start, range_end in download_ranges:
            df = collector.get_data(
                symbol=yahoo_symbol,
                interval=interval,
                start_datetime=range_start,
                end_datetime=range_end,
            )

            if df is not None and not df.empty:
                # Filter anomalous timestamps
                df = _filter_anomalous_timestamps(df, range_start, range_end)

                if df.empty:
                    logger.warning(
                        f"All benchmark data filtered out for {yahoo_symbol}"
                    )
                    continue

                csv_file = csv_dir / f"{qlib_symbol}.csv"

                if csv_file.exists():
                    # Merge with existing data
                    existing_df = pd.read_csv(csv_file, index_col=0, parse_dates=True)
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

                logger.info(
                    f"Benchmark {qlib_symbol} downloaded: {len(df)} records "
                    f"({range_start} to {range_end})"
                )
            else:
                logger.warning(
                    f"No data returned for benchmark {yahoo_symbol} "
                    f"({range_start} to {range_end})"
                )

        return True

    except Exception as e:
        logger.error(f"Failed to download benchmark {yahoo_symbol}: {e}")
        return False


def _execute_yahoo_pipeline(
    stock_pool: str,
    download_ranges: List[Tuple[str, str]],
    incremental: bool = False,
    interval: str = "1d",  # 添加这个参数
) -> Tuple[bool, str]:
    """
    Execute Yahoo data pipeline for multiple date ranges.
    """
    try:
        # Parse stock_pool to market and index parameters
        if stock_pool.lower() == "csi300":
            market, index = "CN", "CSI300"
        elif stock_pool.lower() == "csi500":
            market, index = "CN", "CSI500"
        elif stock_pool.lower() == "sp500":
            market, index = "US", "SP500"
        elif stock_pool.lower() == "nasdaq100":
            market, index = "US", "NASDAQ100"
        else:
            return False, f"Unsupported stock pool: {stock_pool}"

        # Setup directories
        from app.services.data_collectors.yahoo_collector import YahooDataCollector

        csv_dir = (
            Path(settings.CSV_DATA_PATH) / "cn_data"
            if market == "CN"
            else Path(settings.CSV_DATA_PATH) / "us_data"
        )
        csv_dir.mkdir(parents=True, exist_ok=True)

        # Get instrument list (same for all ranges)
        collector = YahooDataCollector(
            save_dir=str(csv_dir),
            market=market,
            index_name=index,
            start=download_ranges[0][0],  # Use first range for initialization
            end=download_ranges[0][1],
        )

        instruments = collector.get_instrument_list()
        logger.info(f"Retrieved {len(instruments)} instruments for {stock_pool}")

        total_collected = 0

        # Download data for each missing range
        for range_start, range_end in download_ranges:
            logger.info(f"Downloading data for range: {range_start} to {range_end}")

            # Update collector for this range
            collector.start = range_start
            collector.end = range_end

            # Use concurrent processing for better performance
            range_collected = 0
            failed_instruments = []

            def download_instrument_data(instrument):
                """Download data for a single instrument"""
                try:
                    df = collector.get_data(
                        symbol=instrument,
                        interval=interval,
                        start_datetime=range_start,
                        end_datetime=range_end,
                    )

                    if df is not None and not df.empty:
                        # Filter out anomalous timestamps before saving to CSV
                        df = _filter_anomalous_timestamps(df, range_start, range_end)

                        if df.empty:
                            logger.warning(
                                f"All data filtered out for {instrument} due to anomalous timestamps"
                            )
                            return instrument, False, 0

                        # Use normalized instrument format for consistency with Qlib
                        normalized_instrument = collector.normalize_symbol(instrument)
                        csv_file = csv_dir / f"{normalized_instrument}.csv"

                        if incremental and csv_file.exists():
                            # Merge with existing data
                            existing_df = pd.read_csv(
                                csv_file, index_col=0, parse_dates=True
                            )

                            # Debug logging for incremental update
                            logger.info(f"Incremental update for {instrument}:")
                            logger.info(
                                f"  New data shape: {df.shape}, dates: {df.index.min()} to {df.index.max()}"
                            )
                            logger.info(
                                f"  Existing data shape: {existing_df.shape}, dates: {existing_df.index.min()} to {existing_df.index.max()}"
                            )

                            # Ensure both DataFrames have the same index type
                            if not isinstance(existing_df.index, pd.DatetimeIndex):
                                existing_df.index = pd.to_datetime(existing_df.index)
                            if not isinstance(df.index, pd.DatetimeIndex):
                                df.index = pd.to_datetime(df.index)

                            # Merge and remove duplicates
                            combined_df = pd.concat([existing_df, df])
                            combined_df = combined_df[
                                ~combined_df.index.duplicated(keep="last")
                            ]
                            combined_df = combined_df.sort_index()

                            logger.info(
                                f"  Combined data shape: {combined_df.shape}, dates: {combined_df.index.min()} to {combined_df.index.max()}"
                            )
                            combined_df.to_csv(csv_file, index=True)
                        else:
                            # Save new data or overwrite
                            if csv_file.exists() and not incremental:
                                # Full refresh mode - overwrite
                                df.to_csv(csv_file, index=True)
                            else:
                                # First time or incremental - save/append
                                df.to_csv(csv_file, index=True)

                        return instrument, True, len(df)
                    else:
                        return instrument, False, 0

                except Exception as e:
                    logger.warning(
                        f"Failed to collect data for {instrument} in range {range_start}-{range_end}: {str(e)}"
                    )
                    return instrument, False, 0

            # Process instruments concurrently with limited workers
            max_workers = min(8, len(instruments))  # Limit concurrent requests
            start_time = time.time()

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_instrument = {
                    executor.submit(download_instrument_data, instrument): instrument
                    for instrument in instruments
                }

                # Process completed tasks
                for i, future in enumerate(as_completed(future_to_instrument), 1):
                    instrument = future_to_instrument[future]
                    try:
                        instrument_name, success, records = future.result()
                        if success:
                            range_collected += 1
                        else:
                            failed_instruments.append(instrument_name)

                        # Log progress every 50 instruments
                        if i % 50 == 0 or i == len(instruments):
                            elapsed = time.time() - start_time
                            rate = i / elapsed if elapsed > 0 else 0
                            logger.info(
                                f"Progress: {i}/{len(instruments)} instruments processed "
                                f"({range_collected} successful, {len(failed_instruments)} failed) "
                                f"- Rate: {rate:.1f} instruments/sec"
                            )

                    except Exception as e:
                        failed_instruments.append(instrument)
                        logger.error(f"Unexpected error processing {instrument}: {e}")

            # Log final results for this range
            elapsed = time.time() - start_time
            logger.info(
                f"Range {range_start} to {range_end} completed: "
                f"{range_collected}/{len(instruments)} successful in {elapsed:.1f}s"
            )
            if failed_instruments:
                logger.warning(
                    f"Failed instruments: {failed_instruments[:10]}{'...' if len(failed_instruments) > 10 else ''}"
                )

            total_collected += range_collected
            logger.info(
                f"Range {range_start} to {range_end}: collected {range_collected}/{len(instruments)} instruments"
            )

        if total_collected == 0:
            return False, "No data was collected for any range"

        success_rate = (
            (total_collected / (len(instruments) * len(download_ranges))) * 100
            if instruments
            else 0
        )
        logger.info(
            f"Yahoo pipeline completed: {total_collected}/{len(instruments) * len(download_ranges)} "
            f"total downloads successful ({success_rate:.1f}% success rate)"
        )

        # Step 1.5: Download benchmark index data for backtest comparison
        _download_benchmark_index(
            stock_pool=stock_pool,
            collector=collector,
            csv_dir=csv_dir,
            download_ranges=download_ranges,
            interval=interval,
        )

        # Step 2: Data Normalization using UniversalNormalize
        from app.services.data_collectors.normalize import UniversalNormalize
        import os

        normalized_dir = csv_dir.parent / "normalized"
        normalized_dir.mkdir(parents=True, exist_ok=True)

        # Initialize Qlib using the centralized service (ensures single initialization)
        try:
            from app.services.qlib_init_service import get_qlib_init_service

            qlib_service = get_qlib_init_service()
            qlib_service.initialize()
            logger.info("Qlib initialized via centralized service for calendar access")

        except Exception as qlib_error:
            logger.warning(
                f"Failed to initialize Qlib: {qlib_error}. Normalization will use empty calendar."
            )

        # Determine market type from the first part of the pipeline
        # This should match the market detection logic used earlier
        if stock_pool.lower() in ["csi300", "csi500"]:
            market_type = "CN"
        elif stock_pool.lower() in ["sp500", "nasdaq100"]:
            market_type = "US"
        else:
            market_type = "US"  # Default to US

        normalizer = UniversalNormalize(market=market_type)

        # Process each CSV file individually
        normalize_success_count = 0
        for csv_file in csv_dir.glob("*.csv"):
            try:
                # Read CSV file
                df = pd.read_csv(csv_file, index_col=0, parse_dates=True)
                if df.empty:
                    continue

                # Reset index to make 'date' a column (required by normalize)
                df = df.reset_index()
                if "index" in df.columns:
                    df = df.rename(columns={"index": "date"})

                # Add symbol column if not present
                if "symbol" not in df.columns:
                    symbol = csv_file.stem  # filename without extension
                    df["symbol"] = symbol

                # Normalize the data
                normalized_df = normalizer.normalize(df)

                # Save normalized data
                output_file = normalized_dir / csv_file.name
                normalized_df.to_csv(output_file, index=True)
                normalize_success_count += 1

            except Exception as e:
                logger.warning(f"Failed to normalize {csv_file.name}: {e}")
                continue

        if normalize_success_count == 0:
            return False, "Data normalization failed - no files processed successfully"

        logger.info("Data normalization completed successfully")

        # Step 3: Convert to Qlib format using dump_bin
        from app.services.data_utils import convert_csv_to_qlib_format_impl

        # Use the correct CSV directory based on market type
        csv_dir = (
            Path(settings.CSV_DATA_PATH) / "cn_data"
            if market_type == "CN"
            else Path(settings.CSV_DATA_PATH) / "us_data"
        )

        # Determine Qlib frequency based on interval parameter
        qlib_freq = "1min" if interval == "1m" else "day"
        logger.info(
            f"Converting to Qlib format with frequency: {qlib_freq} (interval: {interval})"
        )

        # Let convert_csv_to_qlib_format_impl auto-select the correct directory based on frequency
        # Pass incremental flag to preserve existing data during incremental updates
        convert_success, convert_message = convert_csv_to_qlib_format_impl(
            csv_dir=str(csv_dir), freq=qlib_freq, incremental=incremental
        )
        if not convert_success:
            return False, f"Qlib format conversion failed: {convert_message}"

        logger.info("Qlib format conversion completed successfully")

        # Step 4: Save metadata for accurate status reporting
        try:
            import json
            from datetime import datetime
            from app.services.data_utils import get_qlib_dir_for_freq

            metadata = {
                "source": "yahoo",
                "stock_pool": stock_pool,
                "market": market_type,
                "region": region,
                "interval": interval,
                "download_date": datetime.now().isoformat(),
                "instruments_count": total_collected,
                "date_ranges": [(start, end) for start, end in download_ranges],
            }

            # Save metadata to the correct directory based on frequency
            qlib_data_dir = get_qlib_dir_for_freq(qlib_freq)
            metadata_file = Path(qlib_data_dir) / "metadata.json"
            with open(metadata_file, "w") as f:
                json.dump(metadata, f, indent=2)

            logger.info(
                f"Saved metadata: stock_pool={stock_pool}, market={market_type}, dir={qlib_data_dir}"
            )

        except Exception as e:
            logger.warning(f"Failed to save metadata: {e}")

        ranges_summary = f"{len(download_ranges)} ranges, {total_collected} instrument-range combinations"
        return (
            True,
            f"Pipeline completed: downloaded {ranges_summary}, normalized and converted to Qlib format",
        )

    except Exception as e:
        error_msg = f"Yahoo pipeline execution failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg

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
        source_changed = data_source_manager.check_and_handle_source_change()
        if source_changed:
            logger.info("Data source changed, existing data was cleaned up")
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
                request.start_date, request.end_date
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
        current_source = data_source_manager.get_current_source()
        if current_source.lower() == "yahoo":
            success, message = _execute_yahoo_pipeline(
                stock_pool=request.stock_pool,
                download_ranges=download_ranges,
                incremental=request.incremental,
                interval=request.interval or "1d",  # 添加这行
            )

            if not success:
                return DownloadTaskResponse(
                    task_id=task_id,
                    status="failed",
                    message=f"Pipeline execution failed: {message}",
                )

            mode_text = "incremental update" if request.incremental else "full refresh"
            return DownloadTaskResponse(
                task_id=task_id,
                status="completed",
                message=f"Successfully completed {mode_text}: {message}",
            )

        else:
            return DownloadTaskResponse(
                task_id=task_id,
                status="failed",
                message=f"Unsupported data source: {current_source}",
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
    requested_start: str, requested_end: str
) -> List[Tuple[str, str]]:
    """
    Detect all missing date ranges in existing Qlib data.

    Returns:
        List of (start_date, end_date) tuples for missing periods
    """
    try:
        import qlib
        from qlib import init
        from qlib.data import D

        # Initialize Qlib to check existing data
        qlib_data_path = Path(settings.QLIB_DATA_PATH)
        if not qlib_data_path.exists():
            logger.info("No existing Qlib data found, will download full range")
            return [(requested_start, requested_end)]

        try:
            # Determine region based on stock_pool
            region = "cn" if stock_pool.lower() in ["csi300", "csi500"] else "us"
            init(provider_uri=str(qlib_data_path), region=region)

            # Get trading calendar
            calendar = D.calendar(freq="day")
            if calendar is None or len(calendar) == 0:
                logger.info("No calendar data found, will download full range")
                return [(requested_start, requested_end)]

            # Convert to date strings for comparison
            existing_dates = set(date.strftime("%Y-%m-%d") for date in calendar)

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

                        csv_file = csv_dir / f"{instrument}.csv"

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

        # Step 2: Data Normalization using UniversalNormalize
        from app.services.data_collectors.normalize import UniversalNormalize
        import os

        normalized_dir = csv_dir.parent / "normalized"
        normalized_dir.mkdir(parents=True, exist_ok=True)

        # Initialize Qlib before normalization to get trading calendar
        try:
            import qlib
            from qlib import init

            # Initialize Qlib with the target data directory
            qlib_data_path = Path(settings.QLIB_DATA_PATH)
            qlib_data_path.mkdir(parents=True, exist_ok=True)

            # Determine region based on stock_pool
            region = "cn" if stock_pool.lower() in ["csi300", "csi500"] else "us"
            init(provider_uri=str(qlib_data_path), region=region)
            logger.info(
                f"Qlib initialized successfully for calendar access (region: {region})"
            )

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

        convert_success, convert_message = convert_csv_to_qlib_format_impl(
            csv_dir=str(csv_dir), qlib_dir=settings.QLIB_DATA_PATH, freq=qlib_freq
        )
        if not convert_success:
            return False, f"Qlib format conversion failed: {convert_message}"

        logger.info("Qlib format conversion completed successfully")

        # Step 4: Save metadata for accurate status reporting
        try:
            import json
            from datetime import datetime

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

            metadata_file = Path(settings.QLIB_DATA_PATH) / "metadata.json"
            with open(metadata_file, "w") as f:
                json.dump(metadata, f, indent=2)

            logger.info(
                f"Saved metadata: stock_pool={stock_pool}, market={market_type}"
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

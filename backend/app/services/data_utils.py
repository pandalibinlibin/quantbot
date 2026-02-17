"""
Data utilities for Qlib data management.

Educational Notes:
- Simple utility functions for data operations
- Focuses on safety and error handling
- Based on Qlib's data directory structure
"""

import os
import shutil
from pathlib import Path
from typing import Tuple
from app.core.config import settings
from app.services.data_source_manager import data_source_manager


def clear_qlib_data_impl(
    qlib_data_path: str = "/app/qlib_data", csv_data_path: str = "/app/csv_data"
) -> Tuple[bool, str, float]:
    """
    Clear both qlib_data and csv_data directories for complete data source switching.

    Educational Notes:
    - Clears both final data (.bin) and intermediate data (CSV)
    - Ensures complete clean state when switching data sources
    - Calculates total freed space from both directories
    - Implements safety checks for both paths

    Args:
        qlib_data_path: Path to qlib data directory
        csv_data_path: Path to CSV data directory

    Returns:
        Tuple of (success, message, total_size_mb)
    """
    import os
    import shutil
    from pathlib import Path

    try:
        qlib_dir = Path(qlib_data_path)
        csv_dir = Path(csv_data_path)

        # Calculate total size before clearing
        total_size_mb = 0.0

        # Calculate qlib_data size
        if qlib_dir.exists():
            for dirpath, dirnames, filenames in os.walk(qlib_dir):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total_size_mb += os.path.getsize(filepath)

        # Calculate csv_data size
        if csv_dir.exists():
            for dirpath, dirnames, filenames in os.walk(csv_dir):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total_size_mb += os.path.getsize(filepath)

        # Convert to MB
        total_size_mb = round(total_size_mb / (1024 * 1024), 2)

        # Safety checks
        if not qlib_data_path.endswith("qlib_data"):
            return False, "Invalid qlib_data path for safety", 0.0

        if not csv_data_path.endswith("csv_data"):
            return False, "Invalid csv_data path for safety", 0.0

        # Clear qlib_data directory contents (not the directory itself due to Docker mount)
        if qlib_dir.exists():
            for item in qlib_dir.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()

        # Clear csv_data directory contents
        if csv_dir.exists():
            for item in csv_dir.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
        else:
            # Create csv_data directory if it doesn't exist
            csv_dir.mkdir(parents=True, exist_ok=True)

        return (
            True,
            f"Successfully cleared {total_size_mb} MB from both qlib_data and csv_data directories",
            total_size_mb,
        )

    except Exception as e:
        return False, f"Failed to clear data directories: {str(e)}", 0.0


def execute_yahoo_data_collector_impl(
    target_dir: str = "/app/csv_data/cn_data",
    stock_pool: str = "csi300",
    start_date: str = "2020-01-01",
    end_date: str = "2023-12-31",
    incremental: bool = False,
    period: str = None,
    region: str = "cn",
) -> Tuple[bool, str]:
    """
    Execute Yahoo data collector using get_data_yahoo_realtime.py script with enhanced parameters.

    Educational Notes:
    - Uses the new get_data_yahoo_realtime.py script with flexible parameters
    - Supports stock pool selection (csi300, csi500) via dynamic API
    - Supports incremental updates to avoid re-downloading existing data
    - Compatible with existing API interface while providing enhanced functionality

    Args:
        target_dir: Directory to store downloaded CSV data
        stock_pool: Stock pool selection (csi300, csi500, or all)
        start_date: Start date for data collection (YYYY-MM-DD format)
        end_date: End date for data collection (YYYY-MM-DD format)
        incremental: Whether to perform incremental update (append new data only)
        period: Time period (1y, 6m, 3m) - optional, conflicts with start_date/end_date
        region: Market region (cn supported)

    Returns:
        Tuple of (success, message)
    """
    import subprocess

    try:
        # Ensure target directory exists
        target_path = Path(target_dir)
        target_path.mkdir(parents=True, exist_ok=True)

        # Command to execute Yahoo data collector via get_data_yahoo_realtime.py
        cmd = [
            "python",
            "/app/scripts/get_data_yahoo_realtime.py",
            "download_data",
            "--stock_pool",
            stock_pool,
            "--start_date",
            start_date,
            "--end_date",
            end_date,
            "--target_dir",
            target_dir,
        ]

        # Add period parameter if specified (conflicts with start_date/end_date)
        if period:
            cmd.extend(["--period", period])

        # Add incremental flag if required
        if incremental:
            cmd.append("--incremental")

        # Execute the collector command
        result = subprocess.run(cmd, capture_output=True, text=True, cwd="/app")

        if result.returncode == 0:
            return (
                True,
                f"Yahoo data collector executed successfully: {stock_pool} stocks ({start_date} to {end_date}) → {target_dir}",
            )
        else:
            return False, f"Yahoo data collector failed: {result.stderr}"

    except Exception as e:
        return False, f"Error executing Yahoo data collector: {str(e)}"


def clear_qlib_data() -> Tuple[bool, str, float]:
    """Clear both qlib_data and csv_data directories using configuration."""
    return clear_qlib_data_impl(
        qlib_data_path=settings.QLIB_DATA_PATH, csv_data_path=settings.CSV_DATA_PATH
    )


def execute_yahoo_data_collector(
    stock_pool: str = "csi300",
    start_date: str = "2020-01-01",
    end_date: str = "2023-12-31",
    incremental: bool = False,
    period: str = None,
) -> Tuple[bool, str]:
    return execute_yahoo_data_collector_impl(
        target_dir=f"{settings.CSV_DATA_PATH}/cn_data",
        stock_pool=stock_pool,
        start_date=start_date,
        end_date=end_date,
        incremental=incremental,
        period=period,
    )


def convert_csv_to_qlib_format_impl(
    csv_dir: str = "/app/csv_data/cn_data",
    qlib_dir: str = "/app/qlib_data",
    freq: str = "day",
) -> Tuple[bool, str]:
    """
    Convert CSV data to Qlib .bin format using Qlib's dump_bin utility.

    Args:
        csv_dir: Directory containing CSV files
        qlib_dir: Target directory for Qlib .bin data
        freq: Data frequency ('day')

    Returns:
        Tuple of (success, message)
    """
    import subprocess

    try:
        # Ensure directory exist
        source_path = Path(csv_dir)
        qlib_path = Path(qlib_dir)

        if not source_path.exists():
            return False, f"Source directory does not exist: {csv_dir}"

        # Count CSV files
        csv_files = list(source_path.glob("*.csv"))
        if not csv_files:
            return False, f"No CSV file found in {csv_dir}"

        # Clear qlib directory contents (don't delete the directory itself due to Docker mount)
        if qlib_path.exists():
            import shutil
            import glob

            # Remove all contents in the directory
            for item in glob.glob(str(qlib_path / "*")):
                if os.path.isdir(item):
                    shutil.rmtree(item)
                else:
                    os.remove(item)
        else:
            qlib_path.mkdir(parents=True, exist_ok=True)

        # Use local dump_bin script to convert CSV to binary format
        cmd = [
            "python",
            "/app/scripts/dump_bin.py",
            "dump_all",
            "--data_path",
            str(source_path),
            "--qlib_dir",
            str(qlib_path),
            "--freq",
            freq,
            "--date_field_name",
            "date",
        ]

        # Execute the conversion
        result = subprocess.run(cmd, capture_output=True, text=True, cwd="/app")

        if result.returncode == 0:
            # Count converted stocks
            features_dir = qlib_path / "features"
            stock_count = 0
            if features_dir.exists():
                stock_dirs = [d for d in features_dir.iterdir() if d.is_dir()]
                stock_count = len(stock_dirs)

            return (
                True,
                f"Successfully converted {len(csv_files)} CSV files to Qlib format: {stock_count} stocks",
            )
        else:
            return False, f"Qlib conversion failed: {result.stderr}"
    except Exception as e:
        return False, f"Error converting CSV to Qlib format: {str(e)}"


def convert_csv_to_qlib_format() -> Tuple[bool, str]:
    """Convert CSV data to Qlib .bin format using configuration."""

    return convert_csv_to_qlib_format_impl(
        csv_dir=f"{settings.CSV_DATA_PATH}/cn_data",
        qlib_dir=settings.QLIB_DATA_PATH,
        freq="day",
    )


def get_data_source_status_impl() -> dict:
    """
    Get comprehensive data source status analysis.

    Educational Notes:
    - Implements main business logic for data status analysis
    - Uses helper functions for specific parsing tasks
    - Returns dict that can be converted to DataSourceStatus model
    """
    import pickle

    qlib_data_path = Path(settings.QLIB_DATA_PATH)

    # Get current data source from configuration
    current_source = data_source_manager.get_current_source()

    # Check if qlib_data directory exists
    if not qlib_data_path.exists():
        return {
            "source_name": current_source,
            "data_exists": False,
            "date_range_start": None,
            "date_range_end": None,
            "instruments": None,
            "instruments_count": None,
            "stock_pool": None,
            "features": None,
            "data_size_mb": 0,
            "last_updated": None,
        }

    # Calculate directory size
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(qlib_data_path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            if os.path.exists(filepath):
                total_size += os.path.getsize(filepath)

    data_size_mb = round(total_size / (1024 * 1024), 2) if total_size > 0 else 0

    # Check for Qlib standard directories
    calendars_dir = qlib_data_path / "calendars"
    instruments_dir = qlib_data_path / "instruments"
    features_dir = qlib_data_path / "features"

    data_exists = all(
        [calendars_dir.exists(), instruments_dir.exists(), features_dir.exists()]
    )

    # Get last modification time
    last_updated = None
    if data_exists:
        mod_times = []
        for dir_path in [calendars_dir, instruments_dir, features_dir]:
            if dir_path.exists():
                mod_times.append(dir_path.stat().st_mtime)

        if mod_times:
            from datetime import datetime

            last_updated = datetime.fromtimestamp(max(mod_times)).isoformat()

    # Parse actual data if exists
    date_start, date_end = None, None
    instruments, instruments_count = None, None
    stock_pool = None
    features = None

    if data_exists:
        # Parse calendar for date range - check for different frequency files
        try:
            # Try different calendar file types in order of preference
            calendar_files = ["1min.txt", "day.txt"]
            for calendar_filename in calendar_files:
                calendar_file = calendars_dir / calendar_filename
                if calendar_file.exists():
                    with open(calendar_file, "r", encoding="utf-8") as f:
                        dates = [line.strip() for line in f if line.strip()]
                    if dates:
                        # For minute data, extract just the date part
                        if calendar_filename == "1min.txt":
                            date_start = dates[0].split()[
                                0
                            ]  # Extract date from "2026-02-10 09:30:00"
                            date_end = dates[-1].split()[
                                0
                            ]  # Extract date from "2026-02-10 14:59:00"
                        else:
                            date_start = dates[0]
                            date_end = dates[-1]
                        break
        except Exception:
            pass

        # Parse instruments
        try:
            all_file = instruments_dir / "all.txt"
            if all_file.exists():
                with open(all_file, "r") as f:
                    lines = [line.strip() for line in f if line.strip()]

                instruments_data = []
                for line in lines:
                    parts = line.split("\t")
                    if len(parts) >= 1:
                        instruments_data.append(parts[0])  # Stock code

                if instruments_data:
                    instruments = (
                        instruments_data[:10]
                        if len(instruments_data) > 10
                        else instruments_data
                    )
                    instruments_count = len(instruments_data)

                    # Try to read stock_pool from metadata file first
                    stock_pool = None
                    try:
                        import json

                        metadata_file = qlib_data_path / "metadata.json"
                        if metadata_file.exists():
                            with open(metadata_file, "r") as f:
                                metadata = json.load(f)
                                stock_pool = metadata.get("stock_pool")
                    except Exception:
                        pass

                    # Fallback to inference if metadata not available
                    if not stock_pool:
                        if instruments_count <= 120:
                            stock_pool = "csi100"
                        elif instruments_count <= 350:
                            stock_pool = "csi300"
                        elif instruments_count <= 600:
                            stock_pool = "csi500"
                        elif instruments_count > 1000:
                            stock_pool = "yahoo_cn_full"
                        else:
                            stock_pool = "all"
        except Exception:
            pass

        # Parse features
        try:
            symbol_dirs = [d for d in features_dir.iterdir() if d.is_dir()]
            if symbol_dirs:
                first_symbol_dir = symbol_dirs[0]
                feature_files = list(first_symbol_dir.glob("*.bin"))
                features = []
                for f in feature_files:
                    # Remove .day suffix if present (for minute data compatibility)
                    feature_name = f.stem
                    if feature_name.endswith(".day"):
                        feature_name = feature_name[:-4]  # Remove '.day'
                    features.append(feature_name)
                features = list(set(features))  # Remove duplicates
                features.sort()
                features = features[:20] if len(features) > 20 else features
        except Exception:
            pass
    return {
        "source_name": current_source,
        "data_exists": data_exists,
        "data_range_start": date_start,
        "data_range_end": date_end,
        "instruments": instruments,
        "instruments_count": instruments_count,
        "stock_pool": stock_pool,
        "features": features,
        "data_size_mb": data_size_mb,
        "last_updated": last_updated,
    }


def get_data_source_status() -> dict:
    """Get data source status using configuration."""
    return get_data_source_status_impl()

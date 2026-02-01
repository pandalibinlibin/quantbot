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
    file_name: str = "csv_data_cn.zip",
    instruments: str = "csi300",
    start_date: str = "2020-01-01",
    end_date: str = "2023-12-31",
    region: str = "cn",
) -> Tuple[bool, str]:
    """
    Execute Yahoo data collector using get_data.py script with correct parameters for full dataset.

    Educational Notes:
    - Uses get_data.py script with the correct file name for full dataset
    - The key is using "qlib_data_cn_1d_latest.zip" instead of default file name
    - This downloads the complete dataset with thousands of stocks
    - Supports CSI300, CSI500, and full market data

    Args:
        target_dir: Directory to store downloaded CSV data
        file_name: Name of the data file to download (use "qlib_data_cn_1d_latest.zip" for full dataset)
        instruments: Stock pool (csi300, csi500, or all)
        start_date: Start date (for future use)
        end_date: End date (for future use)
        region: Market region (cn supported)

    Returns:
        Tuple of (success, message)
    """
    import subprocess

    try:
        # Ensure target directory exists
        target_path = Path(target_dir)
        target_path.mkdir(parents=True, exist_ok=True)

        # Use the correct file name for full dataset
        # If user requests full dataset or if file_name is default, use the full dataset file name
        if file_name == "csv_data_cn.zip" or instruments in [
            "all",
            "full",
            "yahoo_cn_full",
        ]:
            file_name = "qlib_data_cn_1d_latest.zip"

        # Command to execute Yahoo data collector via get_data.py
        cmd = [
            "python",
            "/app/scripts/get_data.py",
            "download_data",
            "--file_name",
            file_name,
            "--target_dir",
            target_dir,
        ]

        # Execute the collector command
        result = subprocess.run(cmd, capture_output=True, text=True, cwd="/app")

        if result.returncode == 0:
            return (
                True,
                f"Yahoo data collector executed successfully: {file_name} → {target_dir}",
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


def execute_yahoo_data_collector() -> Tuple[bool, str]:
    return execute_yahoo_data_collector_impl(
        target_dir=f"{settings.CSV_DATA_PATH}/cn_data",
        file_name=settings.DEFAULT_CSV_FILE_NAME,
    )


def convert_csv_to_qlib_format_impl(
    csv_dir: str = "/app/csv_data/cn_data",
    qlib_dir: str = "/app/qlib_data",
    freq: str = "day",
) -> Tuple[bool, str]:
    """
    Convert data to Qlib .bin format - now handles pre-formatted full dataset.

    Educational Notes:
    - The full dataset is already in Qlib binary format, so we copy it directly
    - No CSV conversion needed for the complete dataset
    - Maintains compatibility with the API interface
    - Copies features, instruments, and calendars directories

    Args:
        csv_dir: Directory containing the full dataset (misnamed for compatibility)
        qlib_dir: Target directory for Qlib .bin data
        freq: Data frequency ('day' or other supported frequencies)

    Returns:
        Tuple of (success, message)
    """
    import shutil

    try:
        # Ensure directories exist
        source_path = Path(csv_dir)
        qlib_path = Path(qlib_dir)

        if not source_path.exists():
            return False, f"Source directory does not exist: {csv_dir}"

        # Ensure qlib directory exists
        qlib_path.mkdir(parents=True, exist_ok=True)

        # Copy the full dataset structure to qlib_data directory
        # The source directory now contains the full dataset in Qlib format

        # Copy features directory
        features_source = source_path / "features"
        if features_source.exists():
            features_target = qlib_path / "features"
            if features_target.exists():
                shutil.rmtree(features_target)
            shutil.copytree(features_source, features_target)

        # Copy instruments directory
        instruments_source = source_path / "instruments"
        if instruments_source.exists():
            instruments_target = qlib_path / "instruments"
            if instruments_target.exists():
                shutil.rmtree(instruments_target)
            shutil.copytree(instruments_source, instruments_target)

        # Copy calendars directory
        calendars_source = source_path / "calendars"
        if calendars_source.exists():
            calendars_target = qlib_path / "calendars"
            if calendars_target.exists():
                shutil.rmtree(calendars_target)
            shutil.copytree(calendars_source, calendars_target)

        # Count stocks for verification
        stock_count = 0
        if features_target.exists():
            stock_dirs = [d for d in features_target.iterdir() if d.is_dir()]
            stock_count = len(stock_dirs)

        return (
            True,
            f"Successfully copied full dataset to Qlib format: {stock_count} stocks from {csv_dir} → {qlib_dir}",
        )

    except Exception as e:
        return False, f"Error copying full dataset to Qlib format: {str(e)}"


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

    # Check if qlib_data directory exists
    if not qlib_data_path.exists():
        return {
            "source_name": "unknown",
            "data_exists": False,
            "date_range_start": None,
            "date_range_end": None,
            "instruments": None,
            "instruments_count": None,
            "features": None,
            "data_size_mb": None,
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
        # Parse calendar for date range
        try:
            calendar_file = calendars_dir / "day.txt"
            if calendar_file.exists():
                with open(calendar_file, "r", encoding="utf-8") as f:
                    dates = [line.strip() for line in f if line.strip()]
                if dates:
                    date_start = dates[0]
                    date_end = dates[-1]
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

                    # Determine stock pool based on count and dataset characteristics
                    stock_pool = None
                    if instruments_count <= 120:
                        stock_pool = "csi100"
                    elif instruments_count <= 350:
                        stock_pool = "csi300"
                    elif instruments_count <= 600:
                        stock_pool = "csi500"
                    elif instruments_count > 1000:
                        # Full dataset with thousands of stocks
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
                features = [f.stem for f in feature_files]
                features.sort()
                features = features[:20] if len(features) > 20 else features
        except Exception:
            pass
    return {
        "source_name": "yahoo" if data_exists else "unknown",
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

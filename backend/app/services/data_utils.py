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
    qlib_data_path: str = "/app/qlib_data",
    csv_data_path: str = "/app/csv_data",
) -> Tuple[bool, str, float]:
    """
    Clear qlib_data and csv_data directories for complete data source switching.

    Note: Only day-level data is supported in this stock selection system.
    Minute-level data should be handled by a separate timing/execution system.

    Args:
        qlib_data_path: Path to day-level qlib data directory
        csv_data_path: Path to CSV data directory

    Returns:
        Tuple of (success, message, total_size_mb)
    """
    import os
    import shutil
    from pathlib import Path

    def calculate_dir_size(dir_path: Path) -> float:
        """Calculate directory size in bytes."""
        size = 0.0
        if dir_path.exists():
            for dirpath, dirnames, filenames in os.walk(dir_path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        size += os.path.getsize(filepath)
        return size

    def clear_dir_contents(dir_path: Path) -> None:
        """Clear directory contents without removing the directory itself."""
        if dir_path.exists():
            for item in dir_path.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()

    try:
        qlib_dir = Path(qlib_data_path)
        csv_dir = Path(csv_data_path)

        # Calculate total size before clearing
        total_size_bytes = 0.0
        total_size_bytes += calculate_dir_size(qlib_dir)
        total_size_bytes += calculate_dir_size(csv_dir)

        # Convert to MB
        total_size_mb = round(total_size_bytes / (1024 * 1024), 2)

        # Safety checks
        if not qlib_data_path.endswith("qlib_data"):
            return False, "Invalid qlib_data path for safety", 0.0

        if not csv_data_path.endswith("csv_data"):
            return False, "Invalid csv_data path for safety", 0.0

        # Clear qlib_data directory contents (day-level data)
        clear_dir_contents(qlib_dir)

        # Clear csv_data directory contents
        if csv_dir.exists():
            clear_dir_contents(csv_dir)
        else:
            # Create csv_data directory if it doesn't exist
            csv_dir.mkdir(parents=True, exist_ok=True)

        return (
            True,
            f"Successfully cleared {total_size_mb} MB from qlib_data and csv_data directories",
            total_size_mb,
        )

    except Exception as e:
        return False, f"Failed to clear data directories: {str(e)}", 0.0


def clear_qlib_data() -> Tuple[bool, str, float]:
    """Clear qlib_data and csv_data directories using configuration."""
    return clear_qlib_data_impl(
        qlib_data_path=settings.QLIB_DATA_PATH,
        csv_data_path=settings.CSV_DATA_PATH,
    )


def get_qlib_dir_for_freq(freq: str = "day") -> str:
    """
    Get the Qlib data directory.

    Note: Only day-level data is supported in this stock selection system.
    Minute-level data should be handled by a separate timing/execution system.

    Args:
        freq: Data frequency (only 'day' is supported)

    Returns:
        Path to the Qlib data directory
    """
    return settings.QLIB_DATA_PATH


def _remove_benchmarks_from_instruments(qlib_path: Path) -> None:
    """
    Remove benchmark indices from instruments/all.txt file.

    Benchmark indices (e.g., 000300.SH, 000905.SH, SPY, QQQ) should only be used
    for performance comparison, not for trading. This function removes them
    from the instruments list so they won't participate in training or trading.

    Args:
        qlib_path: Path to the Qlib data directory
    """
    # Benchmark symbols for both A-shares and US stocks
    BENCHMARK_SYMBOLS = {
        # A-share benchmarks (Tushare)
        "SH510300",  # CSI300 ETF
        "SH510500",  # CSI500 ETF
        "SH510800",  # CSI800 ETF
        "SH512100",  # CSI1000 ETF
        "SH510880",  # Dividend ETF
        # US stock benchmarks (EOD)
        "SPY",  # S&P 500 ETF
        "QQQ",  # NASDAQ 100 ETF
        "DIA",  # Dow Jones ETF
    }

    instruments_file = qlib_path / "instruments" / "all.txt"
    if not instruments_file.exists():
        return

    # Get all benchmark qlib symbols
    benchmark_symbols = BENCHMARK_SYMBOLS

    try:
        # Read current instruments
        with open(instruments_file, "r") as f:
            lines = f.readlines()

        # Filter out benchmark symbols
        filtered_lines = []
        removed_count = 0
        for line in lines:
            parts = line.strip().split("\t")
            if parts and parts[0] in benchmark_symbols:
                removed_count += 1
                continue
            filtered_lines.append(line)

        # Write back filtered instruments
        if removed_count > 0:
            with open(instruments_file, "w") as f:
                f.writelines(filtered_lines)
            import logging

            logger = logging.getLogger(__name__)
            logger.info(
                f"Removed {removed_count} benchmark indices from instruments/all.txt"
            )

    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to remove benchmarks from instruments: {e}")


def convert_csv_to_qlib_format_impl(
    csv_dir: str = "/app/csv_data/cn_data",
    qlib_dir: str = None,
    freq: str = "day",
    incremental: bool = False,
) -> Tuple[bool, str]:
    """
    Convert CSV data to Qlib .bin format using Qlib's dump_bin utility.

    Note: Only day-level data is supported in this stock selection system.
    Minute-level data should be handled by a separate timing/execution system.

    Args:
        csv_dir: Directory containing CSV files
        qlib_dir: Target directory for Qlib .bin data (auto-selected if None)
        freq: Data frequency (only 'day' is supported)
        incremental: If True, preserve existing data and merge with new data

    Returns:
        Tuple of (success, message)
    """
    import subprocess

    try:
        # Auto-select qlib_dir based on frequency if not specified
        if qlib_dir is None:
            qlib_dir = get_qlib_dir_for_freq(freq)

        # Ensure directory exist
        source_path = Path(csv_dir)
        qlib_path = Path(qlib_dir)

        if not source_path.exists():
            return False, f"Source directory does not exist: {csv_dir}"

        # Count CSV files
        csv_files = list(source_path.glob("*.csv"))
        if not csv_files:
            return False, f"No CSV file found in {csv_dir}"

        import logging

        logger = logging.getLogger(__name__)

        # Only clear qlib directory contents in full refresh mode (not incremental)
        if not incremental and qlib_path.exists():
            import shutil
            import glob

            # Remove all contents in the directory
            for item in glob.glob(str(qlib_path / "*")):
                if os.path.isdir(item):
                    shutil.rmtree(item)
                else:
                    os.remove(item)
            logger.info("Full refresh: cleared existing Qlib data")
        elif not qlib_path.exists():
            qlib_path.mkdir(parents=True, exist_ok=True)

        # Use local dump_bin script to convert CSV to binary format
        # Use dump_update for incremental mode, dump_all for full refresh
        dump_command = "dump_update" if incremental else "dump_all"
        cmd = [
            "python",
            "/app/scripts/dump_bin.py",
            dump_command,
            "--data_path",
            str(source_path),
            "--qlib_dir",
            str(qlib_path),
            "--freq",
            freq,
            "--date_field_name",
            "date",
        ]

        logger.info(
            f"Running dump_bin with command: {dump_command} (incremental={incremental})"
        )

        # Execute the conversion
        result = subprocess.run(cmd, capture_output=True, text=True, cwd="/app")

        if result.returncode == 0:
            # Count converted stocks
            features_dir = qlib_path / "features"
            stock_count = 0
            if features_dir.exists():
                stock_dirs = [d for d in features_dir.iterdir() if d.is_dir()]
                stock_count = len(stock_dirs)

            # Remove benchmark indices from instruments/all.txt
            # Benchmark indices should only be used for comparison, not for trading
            _remove_benchmarks_from_instruments(qlib_path)

            return (
                True,
                f"Successfully converted {len(csv_files)} CSV files to Qlib format ({freq}): {stock_count} stocks → {qlib_path}",
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
    - Checks both day-level and minute-level data directories
    """
    import pickle

    # Use day-level data directory only (minute data handled by separate timing system)
    qlib_data_path = Path(settings.QLIB_DATA_PATH)

    # Get current data source from configuration
    current_config = data_source_manager.get_current_config()
    current_source = current_config.get("source", "tushare")

    # Check if qlib_data directory has complete data structure
    def has_complete_data_structure(path: Path) -> bool:
        if not path.exists():
            return False
        calendars = path / "calendars"
        instruments = path / "instruments"
        features = path / "features"
        return calendars.exists() and instruments.exists() and features.exists()

    day_exists = has_complete_data_structure(qlib_data_path)

    if not day_exists:
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
    if qlib_data_path.exists():
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
                        # Detect market type from stock code format
                        # A-shares: start with 'sh' or 'sz' (e.g., sh600000)
                        # US stocks: pure letters (e.g., aapl)
                        sample_code = (
                            instruments_data[0].lower() if instruments_data else ""
                        )
                        is_us_market = sample_code and not (
                            sample_code.startswith("sh") or sample_code.startswith("sz")
                        )

                        if is_us_market:
                            if instruments_count <= 110:
                                stock_pool = "nasdaq100"
                            elif instruments_count <= 510:
                                stock_pool = "sp500"
                            else:
                                stock_pool = "us_all"
                        else:
                            if instruments_count <= 120:
                                stock_pool = "csi100"
                            elif instruments_count <= 350:
                                stock_pool = "csi300"
                            elif instruments_count <= 600:
                                stock_pool = "csi500"
                            elif instruments_count > 1000:
                                stock_pool = "csi1000"
                            else:
                                stock_pool = "all"
        except Exception:
            pass

        # Parse features from day-level data directory
        try:
            features = []
            features_dir_day = qlib_data_path / "features"
            if features_dir_day.exists():
                symbol_dirs = [d for d in features_dir_day.iterdir() if d.is_dir()]
                if symbol_dirs:
                    first_symbol_dir = symbol_dirs[0]
                    feature_files = list(first_symbol_dir.glob("*.bin"))
                    for f in feature_files:
                        # Extract feature name with frequency suffix
                        # e.g., "close.day.bin" -> "close.day"
                        feature_name = f.stem
                        features.append(feature_name)

            features = list(set(features))  # Remove duplicates
            features.sort()
            features = features[:20] if len(features) > 20 else features
        except Exception:
            pass

        # Get label name from database to separate from features
        label_name = None
        try:
            from sqlmodel import Session, select
            from app.core.db import engine
            from app.models import Factor, FactorStatus, FactorType

            with Session(engine) as session:
                statement = select(Factor).where(
                    Factor.factor_type == FactorType.LABEL,
                    Factor.status == FactorStatus.ACTIVE,
                )
                label = session.exec(statement).first()
                if label:
                    label_name = label.name
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
        "label": label_name,
        "data_size_mb": data_size_mb,
        "last_updated": last_updated,
    }


def get_data_source_status() -> dict:
    """Get data source status using configuration."""
    return get_data_source_status_impl()

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

    Args:
        freq: Data frequency (only 'day' is supported)

    Returns:
        Path to the Qlib data directory
    """
    return settings.QLIB_DATA_PATH


def _remove_benchmarks_from_instruments(qlib_path: Path) -> None:
    """
    Remove benchmark indices from instruments/all.txt file.

    Benchmark ETFs (e.g., SH510300) should only be used for performance comparison,
    not for model training or signal generation. This function removes them
    from the instruments list so they won't participate in training or trading.

    Args:
        qlib_path: Path to the Qlib data directory
    """
    # Benchmark symbol for ETF Enhanced Indexing strategy
    BENCHMARK_SYMBOLS = {
        "SH510300",  # CSI300 ETF (benchmark)
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
    """
    import pickle

    # Use Qlib data directory
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
        # Parse calendar for date range
        try:
            calendar_file = calendars_dir / "day.txt"
            if calendar_file.exists():
                with open(calendar_file, "r", encoding="utf-8") as f:
                    dates = [line.strip() for line in f if line.strip()]
                if dates:
                    date_start = dates[0]
                    date_end = dates[-1]
            else:
                logger.error(f"Calendar file not found: {calendar_file}")
        except Exception as e:
            logger.error(f"Failed to parse calendar: {e}")

        # Parse instruments: single source = feature directories on disk
        try:
            if features_dir.exists():
                instrument_dirs = [d for d in features_dir.iterdir() if d.is_dir()]
                instruments_count = len(instrument_dirs)
                instruments = (
                    [d.name for d in instrument_dirs[:10]]
                    if len(instrument_dirs) > 10
                    else [d.name for d in instrument_dirs]
                )
            else:
                logger.error(f"Features directory not found: {features_dir}")

            # Stock pool: single source = metadata.json
            if instruments_count is not None:
                try:
                    import json

                    metadata_file = qlib_data_path / "metadata.json"
                    if metadata_file.exists():
                        with open(metadata_file, "r") as f:
                            metadata = json.load(f)
                            stock_pool = metadata.get("stock_pool")

                    if not stock_pool:
                        # Infer from instrument code format
                        sample_code = instruments[0].lower() if instruments else ""
                        is_us_market = sample_code and not (
                            sample_code.startswith("sh") or sample_code.startswith("sz")
                        )
                        stock_pool = "us_all" if is_us_market else "etf_universe"
                except Exception as e:
                    logger.error(f"Failed to determine stock_pool: {e}")
        except Exception as e:
            logger.error(f"Failed to parse instruments: {e}")

        # Parse features: single source = bin files in first instrument directory
        try:
            features = []
            if features_dir.exists():
                symbol_dirs = [d for d in features_dir.iterdir() if d.is_dir()]
                if symbol_dirs:
                    first_symbol_dir = symbol_dirs[0]
                    feature_files = list(first_symbol_dir.glob("*.bin"))
                    for f in feature_files:
                        # e.g., "close.day.bin" -> "close.day"
                        features.append(f.stem)

            features = sorted(set(features))
            features = features[:20] if len(features) > 20 else features
        except Exception as e:
            logger.error(f"Failed to parse features: {e}")

        # Label: single source = system_config.yaml (label is defined there, not in DB)
        label_name = None
        try:
            import yaml as _yaml

            _cfg_path = Path("/app/app/config/qlib/system_config.yaml")
            if _cfg_path.exists():
                with open(_cfg_path, "r") as _f:
                    _sys_cfg = _yaml.safe_load(_f)
                _region = _sys_cfg.get("data", {}).get("region", "cn")
                _label_cfg = _sys_cfg.get("label_config", {}).get(_region, {})
                _label_expr = _label_cfg.get("expression", "")
                if _label_expr:
                    label_name = f"LABEL0: {_label_expr}"
                else:
                    logger.error(
                        f"No label expression for region '{_region}' in system config"
                    )
            else:
                logger.error(f"System config not found: {_cfg_path}")
        except Exception as e:
            logger.error(f"Failed to read label config: {e}")

    # Build raw field_names list (OHLCV + broadcast fields)
    field_names = None
    if data_exists and features:
        base_data_names = {"open", "high", "low", "close", "volume", "vwap"}
        try:
            from app.services.data_collectors.broadcast_field_collector import (
                get_broadcast_field_names,
            )

            base_data_names |= get_broadcast_field_names()
        except ImportError:
            pass
        # Keep only features that are raw fields, preserve .day/.1min suffix
        field_names = [
            f
            for f in features
            if f.replace(".day", "").replace(".1min", "").lower() in base_data_names
        ]

    return {
        "source_name": current_source,
        "data_exists": data_exists,
        "data_range_start": date_start,
        "data_range_end": date_end,
        "instruments": instruments,
        "instruments_count": instruments_count,
        "stock_pool": stock_pool,
        "features": features,
        "field_names": field_names,
        "label": label_name,
        "data_size_mb": data_size_mb,
        "last_updated": last_updated,
    }


def get_data_source_status() -> dict:
    """Get data source status using configuration."""
    return get_data_source_status_impl()

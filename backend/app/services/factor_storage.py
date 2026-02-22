"""
Factor Storage Manager for bin file operations

This module implements the storage layer for computed factor data,
writing factor bin files directly to each symbol's directory.

Educational Notes:
- FactorStorage writes bin files directly to features/{symbol}/ directories
- This avoids using dump_bin.py which would overwrite calendar/instruments
- Ensures complete compatibility with Qlib's bin format
- Supports both day and 1min frequencies with correct directory selection
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union, Any
from datetime import datetime, date
from pathlib import Path

from qlib.data import D
from qlib.utils.time import Freq
from qlib.log import get_module_logger
import qlib
from qlib.config import C

logger = get_module_logger("FactorStorage")


class FactorStorage:
    """
    Factor Storage Manager for bin file operations

    This class handles the storage and retrieval of computed factor data
    by writing bin files directly to each symbol's directory.

    Educational Notes:
    - Writes bin files directly to features/{symbol}/ directories
    - Avoids dump_bin.py to prevent overwriting calendar/instruments
    - Supports both day and 1min frequencies with correct directory selection
    - Fully compatible with Qlib's data format
    """

    def __init__(self, freq: str = "day"):
        """
        Initialize Factor Storage Manager

        Args:
            freq: Data frequency (day, 1min, etc.)
        """
        self.freq = freq

        # Determine storage directory based on frequency
        # day data -> qlib_data, 1min data -> qlib_data_1min
        self.storage_dir = self._get_storage_dir_for_freq(freq)

        # Create directory structure following Qlib convention
        # Note: factors are stored in features/{symbol}/ directories, not features/{freq}/
        self.features_dir = self.storage_dir / "features"
        self.metadata_dir = self.storage_dir / "factor_metadata"

        # Ensure directories exist
        self.features_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"FactorStorage initialized: storage_dir={self.storage_dir}, freq={freq}"
        )

    def _get_storage_dir_for_freq(self, freq: str) -> Path:
        """
        Get the correct storage directory based on frequency.

        Args:
            freq: Data frequency (day, 1min, etc.)

        Returns:
            Path to the storage directory
        """
        try:
            # Try to get data_path from Qlib config
            data_path_config = C.get("data_path", None)
            if data_path_config and isinstance(data_path_config, dict):
                # Get frequency-specific path if available
                if freq in data_path_config:
                    qlib_data_dir = str(data_path_config[freq])
                else:
                    qlib_data_dir = str(
                        data_path_config.get("__DEFAULT_FREQ", "./qlib_data")
                    )
            else:
                # Fallback to provider_uri
                provider_uri = C.get("provider_uri", "./qlib_data")
                if isinstance(provider_uri, str):
                    qlib_data_dir = provider_uri
                    if qlib_data_dir.startswith("file://"):
                        qlib_data_dir = qlib_data_dir[7:]
                else:
                    qlib_data_dir = "./qlib_data"

            # For minute data, use qlib_data_1min directory
            if freq == "1min" and "1min" not in qlib_data_dir:
                # Check if qlib_data_1min exists
                base_dir = (
                    Path(qlib_data_dir).parent
                    if "qlib_data" in qlib_data_dir
                    else Path(".")
                )
                min_dir = base_dir / "qlib_data_1min"
                if min_dir.exists() or not Path(qlib_data_dir).exists():
                    return min_dir

            return Path(qlib_data_dir)

        except Exception as e:
            logger.warning(f"Failed to get Qlib data directory, using default: {e}")
            # Default based on frequency
            if freq == "1min":
                return Path("qlib_data_1min")
            return Path("qlib_data")

    def save_factor_data(
        self,
        factor_name: str,
        factor_data: pd.DataFrame,
        instruments: Optional[List[str]] = None,
        overwrite: bool = False,
    ) -> bool:
        """
        Save computed factor data to bin files using CSV+dump_bin approach

        Args:
            factor_name: Name of the factor
            factor_data: Computed factor DataFrame
            instruments: List of instruments (for validation)
            overwrite: Whether to overwrite existing data

        Returns:
            True if save successful
        """
        try:
            logger.info(f"=== FACTOR STORAGE START for '{factor_name}' ===")
            logger.info(f"factor_data shape: {factor_data.shape}")
            logger.info(f"freq: {self.freq}")
            logger.info(f"storage_dir: {self.storage_dir}")
            logger.info(f"features_dir: {self.features_dir}")
            logger.info(f"overwrite: {overwrite}")

            # Validate input data
            if factor_data.empty:
                logger.warning(f"Factor '{factor_name}' data is empty, skipping save")
                return False

            # Write factor data directly to bin files in each symbol's directory
            # This avoids using dump_bin.py which would overwrite calendar/instruments
            logger.info(f"Writing factor data directly to bin files")
            bin_success = self._write_factor_to_bin_files(
                factor_name, factor_data, overwrite
            )
            logger.info(f"Bin write result: bin_success={bin_success}")
            if not bin_success:
                return False

            # Step 3: Save metadata
            metadata = self._create_metadata(factor_name, factor_data, instruments)
            metadata_file = self.metadata_dir / f"{factor_name}_metadata.json"

            import json

            with open(metadata_file, "w") as f:
                json.dump(metadata, f, indent=2, default=str)

            logger.info(f"✓ Factor '{factor_name}' saved successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to save factor '{factor_name}': {e}")
            return False

    def _write_factor_to_bin_files(
        self, factor_name: str, factor_data: pd.DataFrame, overwrite: bool = False
    ) -> bool:
        """
        Write factor data directly to bin files in each symbol's directory.

        This method writes bin files directly without using dump_bin.py,
        which would overwrite the calendar and instruments files.

        Args:
            factor_name: Name of the factor
            factor_data: Factor DataFrame with MultiIndex (instrument, datetime)
            overwrite: Whether to overwrite existing files

        Returns:
            True if successful
        """
        try:
            # Read existing calendar to get date indices
            calendar_file = self.storage_dir / "calendars" / f"{self.freq}.txt"
            if not calendar_file.exists():
                logger.error(f"Calendar file not found: {calendar_file}")
                return False

            with open(calendar_file, "r") as f:
                calendar_dates = [line.strip() for line in f if line.strip()]

            # Create date to index mapping
            date_to_idx = {pd.Timestamp(d): i for i, d in enumerate(calendar_dates)}

            # Prepare data - handle MultiIndex (instrument, datetime) format
            if hasattr(factor_data.index, "get_level_values"):
                df_reset = factor_data.reset_index()
                # Identify datetime and instrument columns
                index_names = list(factor_data.index.names)
                if "instrument" in index_names:
                    instrument_col = "instrument"
                    datetime_col = [n for n in index_names if n != "instrument"][0]
                elif "datetime" in index_names:
                    datetime_col = "datetime"
                    instrument_col = [n for n in index_names if n != "datetime"][0]
                else:
                    # Try to identify by column content
                    col_names = list(df_reset.columns)[:2]
                    datetime_col = col_names[0]
                    instrument_col = col_names[1]
                    for col in col_names:
                        try:
                            pd.to_datetime(df_reset[col].iloc[0])
                            datetime_col = col
                        except:
                            instrument_col = col
            else:
                logger.error("Factor data must have MultiIndex (instrument, datetime)")
                return False

            # Get the factor value column name
            value_cols = [
                c for c in df_reset.columns if c not in [datetime_col, instrument_col]
            ]
            if not value_cols:
                logger.error("No factor value column found")
                return False
            value_col = value_cols[0]

            # Group by instrument and write bin files
            symbols_written = 0
            for instrument, group in df_reset.groupby(instrument_col):
                # Get symbol directory (lowercase)
                symbol_dir = self.features_dir / str(instrument).lower()
                if not symbol_dir.exists():
                    logger.warning(
                        f"Symbol directory not found: {symbol_dir}, skipping"
                    )
                    continue

                # Target bin file
                bin_file = symbol_dir / f"{factor_name.lower()}.{self.freq}.bin"

                # Skip if file exists and not overwrite
                if bin_file.exists() and not overwrite:
                    logger.debug(f"Bin file exists, skipping: {bin_file}")
                    continue

                # Sort by datetime
                group = group.sort_values(datetime_col)

                # Get first date and validate it's in calendar
                first_date = pd.Timestamp(group[datetime_col].iloc[0])
                if first_date not in date_to_idx:
                    logger.warning(
                        f"Date {first_date} not in calendar for {instrument}"
                    )
                    continue

                start_idx = date_to_idx[first_date]

                # Get factor values as float32 array
                values = group[value_col].values.astype(np.float32)

                # Write bin file: [start_index as float32] + [values as float32]
                with open(bin_file, "wb") as f:
                    np.array([start_idx], dtype=np.float32).tofile(f)
                    values.tofile(f)

                symbols_written += 1
                logger.debug(f"Written {len(values)} values to {bin_file}")

            logger.info(
                f"✓ Factor '{factor_name}' written to {symbols_written} symbol directories"
            )
            return symbols_written > 0

        except Exception as e:
            logger.error(f"Failed to write factor bin files: {e}")
            import traceback

            logger.error(traceback.format_exc())
            return False

    def load_factor_data(
        self,
        factor_name: str,
        start_time: Optional[Union[str, datetime, date]] = None,
        end_time: Optional[Union[str, datetime, date]] = None,
    ) -> Optional[pd.DataFrame]:
        """
        Load factor data from bin files using Qlib's data loading mechanism

        Args:
            factor_name: Name of the factor
            start_time: Start time for data filtering
            end_time: End time for data filtering

        Returns:
            DataFrame with factor data or None if not found
        """
        try:
            # Get instruments list using D.instruments
            instruments = D.instruments(market="all")

            # Use the factor name as a field reference (not as an expression)
            # Qlib stores factors as lowercase field names in the binary format
            field_name = f"${factor_name.lower()}"

            # Load the factor data using D.features with the field reference
            factor_data = D.features(
                instruments=instruments,
                fields=[field_name],
                start_time=start_time,
                end_time=end_time,
                freq=self.freq,
            )

            if not factor_data.empty:
                logger.info(
                    f"✓ Factor '{factor_name}' loaded successfully: shape={factor_data.shape}"
                )
                return factor_data
            else:
                logger.warning(f"Factor '{factor_name}' data is empty or not found")
                return None

        except Exception as e:
            logger.error(f"Failed to load factor '{factor_name}': {e}")
            return None

    def get_factor_metadata(self, factor_name: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a specific factor

        Args:
            factor_name: Name of the factor

        Returns:
            Metadata dictionary or None if not found
        """
        try:
            metadata_file = self.metadata_dir / f"{factor_name}_metadata.json"

            if not metadata_file.exists():
                logger.warning(f"Metadata for factor '{factor_name}' not found")
                return None

            import json

            with open(metadata_file, "r") as f:
                metadata = json.load(f)

            return metadata

        except Exception as e:
            logger.error(f"Failed to load metadata for factor '{factor_name}': {e}")
            return None

    def list_stored_factors(self) -> List[str]:
        """
        List all stored factors by checking bin files

        Returns:
            List of factor names
        """
        try:
            factor_names = set()

            # Raw data fields that are not factors
            raw_fields = {
                "open",
                "high",
                "low",
                "close",
                "volume",
                "amount",
                "factor",
                "vwap",
            }

            if self.features_dir.exists():
                # Look in first symbol directory to find factor files
                symbol_dirs = [d for d in self.features_dir.iterdir() if d.is_dir()]
                if symbol_dirs:
                    first_symbol_dir = symbol_dirs[0]
                    pattern = f"*.{self.freq}.bin"
                    for bin_file in first_symbol_dir.glob(pattern):
                        # Extract factor name from filename
                        factor_name = bin_file.stem.replace(f".{self.freq}", "")
                        # Skip raw data fields and system files
                        if (
                            factor_name.lower() not in raw_fields
                            and not factor_name.startswith("$")
                        ):
                            factor_names.add(factor_name)

            logger.info(f"Found {len(factor_names)} stored factors")
            return list(factor_names)

        except Exception as e:
            logger.error(f"Failed to list stored factors: {e}")
            return []

    def delete_factor_data(self, factor_name: str) -> bool:
        """
        Delete stored factor data and metadata

        Args:
            factor_name: Name of the factor to delete

        Returns:
            True if deletion successful
        """
        try:
            # Delete factor bin files from all symbol directories
            deleted_count = 0
            if self.features_dir.exists():
                for symbol_dir in self.features_dir.iterdir():
                    if symbol_dir.is_dir():
                        data_file = (
                            symbol_dir / f"{factor_name.lower()}.{self.freq}.bin"
                        )
                        if data_file.exists():
                            data_file.unlink()
                            deleted_count += 1

            logger.info(
                f"✓ Deleted factor data files from {deleted_count} symbol directories"
            )

            # Delete metadata file
            metadata_file = self.metadata_dir / f"{factor_name}_metadata.json"
            if metadata_file.exists():
                metadata_file.unlink()
                logger.info(f"✓ Deleted factor metadata: {metadata_file}")

            logger.info(f"✓ Factor '{factor_name}' completely deleted")
            return True

        except Exception as e:
            logger.error(f"Failed to delete factor '{factor_name}': {e}")
            return False

    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics

        Returns:
            Dictionary with storage statistics
        """
        try:
            stats = {
                "total_factors": 0,
                "total_size_mb": 0.0,
                "storage_dir": str(self.storage_dir),
                "freq": self.freq,
                "factors": [],
            }

            stored_factors = self.list_stored_factors()
            stats["total_factors"] = len(stored_factors)

            total_size = 0
            for factor_name in stored_factors:
                # Sum up factor file sizes across all symbol directories
                factor_size = 0
                if self.features_dir.exists():
                    for symbol_dir in self.features_dir.iterdir():
                        if symbol_dir.is_dir():
                            data_file = (
                                symbol_dir / f"{factor_name.lower()}.{self.freq}.bin"
                            )
                            if data_file.exists():
                                factor_size += data_file.stat().st_size
                total_size += factor_size

                metadata = self.get_factor_metadata(factor_name)
                factor_info = {
                    "name": factor_name,
                    "size_mb": round(factor_size / (1024 * 1024), 2),
                    "created_at": metadata.get("created_at") if metadata else None,
                    "data_range": metadata.get("data_range") if metadata else None,
                }
                stats["factors"].append(factor_info)

            stats["total_size_mb"] = round(total_size / (1024 * 1024), 2)

            return stats

        except Exception as e:
            logger.error(f"Failed to get storage stats: {e}")
            return {"error": str(e)}

    def _create_metadata(
        self,
        factor_name: str,
        factor_data: pd.DataFrame,
        instruments: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Create metadata for factor data

        Args:
            factor_name: Name of the factor
            factor_data: Factor DataFrame
            instruments: List of instruments

        Returns:
            Metadata dictionary
        """
        metadata = {
            "factor_name": factor_name,
            "created_at": datetime.now().isoformat(),
            "freq": self.freq,
            "shape": list(factor_data.shape),
            "columns": list(factor_data.columns),
            "data_range": {
                "start": (
                    factor_data.index.get_level_values(0).min()
                    if hasattr(factor_data.index, "get_level_values")
                    else factor_data.index.min()
                ),
                "end": (
                    factor_data.index.get_level_values(0).max()
                    if hasattr(factor_data.index, "get_level_values")
                    else factor_data.index.max()
                ),
            },
            "instruments_count": (
                len(factor_data.index.get_level_values(1).unique())
                if hasattr(factor_data.index, "get_level_values")
                else len(factor_data)
            ),
            "non_null_ratio": float(factor_data.count().sum() / factor_data.size),
            "storage_format": "csv_to_bin",
            "qlib_compatible": True,
        }

        if instruments:
            metadata["instruments"] = instruments

        return metadata

    def delete_factor_bin_files(self, factor_name: str) -> Dict[str, Any]:
        """
        Delete all bin files for a specific factor across all symbols.

        This method removes the factor's bin file from each symbol's directory
        and also removes the factor's metadata file.

        Args:
            factor_name: Name of the factor to delete

        Returns:
            Dictionary with deletion results
        """
        try:
            logger.info(f"Deleting bin files for factor: {factor_name}")

            # Construct the bin file name based on frequency
            # Format: {factor_name}.{freq}.bin (e.g., my_factor.day.bin)
            bin_filename = f"{factor_name}.{self.freq}.bin"

            deleted_count = 0
            failed_count = 0
            deleted_symbols = []

            # Iterate through all symbol directories
            if not self.features_dir.exists():
                logger.warning(
                    f"Features directory does not exist: {self.features_dir}"
                )
                return {
                    "success": True,
                    "factor_name": factor_name,
                    "deleted_count": 0,
                    "message": "No features directory found",
                }

            for symbol_dir in self.features_dir.iterdir():
                if not symbol_dir.is_dir():
                    continue

                bin_file = symbol_dir / bin_filename
                if bin_file.exists():
                    try:
                        bin_file.unlink()
                        deleted_count += 1
                        deleted_symbols.append(symbol_dir.name)
                    except Exception as e:
                        logger.error(f"Failed to delete {bin_file}: {e}")
                        failed_count += 1

            # Delete metadata file
            metadata_file = self.metadata_dir / f"{factor_name}_metadata.json"
            if metadata_file.exists():
                try:
                    metadata_file.unlink()
                    logger.info(f"Deleted metadata file: {metadata_file}")
                except Exception as e:
                    logger.warning(f"Failed to delete metadata file: {e}")

            logger.info(
                f"Deleted {deleted_count} bin files for factor '{factor_name}' "
                f"(failed: {failed_count})"
            )

            return {
                "success": failed_count == 0,
                "factor_name": factor_name,
                "deleted_count": deleted_count,
                "failed_count": failed_count,
                "deleted_symbols": deleted_symbols[:10],  # First 10 for brevity
                "total_symbols": len(deleted_symbols),
            }

        except Exception as e:
            logger.error(f"Failed to delete factor bin files: {e}")
            return {
                "success": False,
                "factor_name": factor_name,
                "error": str(e),
            }

    def compute_factor_from_expression(
        self,
        factor_name: str,
        expression: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> Optional[pd.DataFrame]:
        """
        Compute factor values from expression using existing bin data.

        This method uses Qlib's D.features() to compute factor values
        from the given expression, using existing OHLCV bin data.

        Args:
            factor_name: Name for the computed factor
            expression: Qlib expression (e.g., "$close/$open", "Ref($close, 1)")
            start_time: Start time for computation (None for all available data)
            end_time: End time for computation (None for all available data)

        Returns:
            DataFrame with computed factor values, or None if failed
        """
        try:
            logger.info(
                f"Computing factor '{factor_name}' from expression: {expression}"
            )

            # Get list of instruments from instruments/all.txt
            instruments_file = self.storage_dir / "instruments" / "all.txt"
            if not instruments_file.exists():
                logger.error(f"Instruments file not found: {instruments_file}")
                return None

            # Read instruments
            instruments = []
            with open(instruments_file, "r") as f:
                for line in f:
                    parts = line.strip().split("\t")
                    if parts:
                        instruments.append(parts[0])

            if not instruments:
                logger.error("No instruments found")
                return None

            logger.info(f"Found {len(instruments)} instruments")

            # Use Qlib D.features() to compute the expression
            # The expression will be evaluated using existing bin data
            try:
                factor_data = D.features(
                    instruments=instruments,
                    fields=[expression],
                    start_time=start_time,
                    end_time=end_time,
                    freq=self.freq,
                )

                if factor_data is None or factor_data.empty:
                    logger.warning(f"No data computed for expression: {expression}")
                    return None

                # Rename the column to factor_name
                factor_data.columns = [factor_name]

                logger.info(
                    f"Computed factor '{factor_name}': shape={factor_data.shape}, "
                    f"non-null={factor_data[factor_name].notna().sum()}"
                )

                return factor_data

            except Exception as e:
                logger.error(f"Qlib D.features() failed: {e}")
                return None

        except Exception as e:
            logger.error(f"Failed to compute factor from expression: {e}")
            return None

    def compute_and_save_factor(
        self,
        factor_name: str,
        expression: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        overwrite: bool = True,
    ) -> Dict[str, Any]:
        """
        Compute factor from expression and save to bin files.

        This is a convenience method that combines compute_factor_from_expression
        and save_factor_data.

        Args:
            factor_name: Name for the factor
            expression: Qlib expression
            start_time: Start time for computation
            end_time: End time for computation
            overwrite: Whether to overwrite existing bin files

        Returns:
            Dictionary with computation and save results
        """
        try:
            # Step 1: If overwrite, delete existing bin files first
            if overwrite:
                delete_result = self.delete_factor_bin_files(factor_name)
                logger.info(f"Deleted existing bin files: {delete_result}")

            # Step 2: Compute factor from expression
            factor_data = self.compute_factor_from_expression(
                factor_name=factor_name,
                expression=expression,
                start_time=start_time,
                end_time=end_time,
            )

            if factor_data is None:
                return {
                    "success": False,
                    "factor_name": factor_name,
                    "error": "Failed to compute factor from expression",
                }

            # Step 3: Save to bin files
            save_success = self.save_factor_data(
                factor_name=factor_name,
                factor_data=factor_data,
                overwrite=overwrite,
            )

            if not save_success:
                return {
                    "success": False,
                    "factor_name": factor_name,
                    "error": "Failed to save factor to bin files",
                }

            return {
                "success": True,
                "factor_name": factor_name,
                "expression": expression,
                "shape": list(factor_data.shape),
                "non_null_count": int(factor_data.iloc[:, 0].notna().sum()),
                "message": f"Factor '{factor_name}' computed and saved successfully",
            }

        except Exception as e:
            logger.error(f"Failed to compute and save factor: {e}")
            return {
                "success": False,
                "factor_name": factor_name,
                "error": str(e),
            }

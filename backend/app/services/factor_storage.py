"""
Factor Storage Manager for bin file operations

This module implements the storage layer for computed factor data,
using the same CSV+dump_bin approach as our data collection pipeline.

Educational Notes:
- FactorStorage follows the same pattern as convert_csv_to_qlib_format_impl
- Saves factors as CSV first, then uses dump_bin.py script for conversion
- Ensures complete compatibility with Qlib's bin format
- Integrates with existing data pipeline infrastructure
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union, Any
from datetime import datetime, date
import os
import tempfile
import subprocess
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
    using the same CSV+dump_bin approach as our data collection pipeline.

    Educational Notes:
    - Uses CSV as intermediate format, then dump_bin.py for conversion
    - Follows the same pattern as convert_csv_to_qlib_format_impl
    - Stores factors directly in Qlib's features directory
    - Fully compatible with existing data pipeline
    """

    def __init__(self, freq: str = "day"):
        """
        Initialize Factor Storage Manager

        Args:
            freq: Data frequency (day, 1min, etc.)
        """
        self.freq = freq

        # Get Qlib data directory from configuration
        try:
            # Try to get data_path from Qlib config
            data_path_config = C.get("data_path", None)
            if data_path_config and isinstance(data_path_config, dict):
                # Get the default frequency path
                qlib_data_dir = data_path_config.get("__DEFAULT_FREQ", "./qlib_data")
            else:
                # Fallback to provider_uri if data_path is not available
                provider_uri = C.get("provider_uri", "./qlib_data")
                if isinstance(provider_uri, str):
                    qlib_data_dir = provider_uri
                    if qlib_data_dir.startswith("file://"):
                        qlib_data_dir = qlib_data_dir[7:]  # Remove file:// prefix
                else:
                    qlib_data_dir = "./qlib_data"

            self.storage_dir = Path(qlib_data_dir)
        except Exception as e:
            logger.warning(f"Failed to get Qlib data directory, using default: {e}")
            self.storage_dir = Path("qlib_data")

        # Create directory structure following Qlib convention
        self.factors_dir = self.storage_dir / "features" / freq
        self.metadata_dir = self.storage_dir / "factor_metadata"

        # CSV intermediate directory
        self.csv_temp_dir = Path("/tmp/factor_csv")

        # Ensure directories exist
        self.factors_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        self.csv_temp_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"FactorStorage initialized: storage_dir={self.storage_dir}, freq={freq}"
        )

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
            logger.info(f"factors_dir: {self.factors_dir}")
            logger.info(f"overwrite: {overwrite}")

            # Validate input data
            if factor_data.empty:
                logger.warning(f"Factor '{factor_name}' data is empty, skipping save")
                return False

            # Check if data already exists
            data_file = self.factors_dir / f"{factor_name.lower()}.{self.freq}.bin"
            logger.info(f"Target bin file: {data_file}")
            logger.info(f"Target bin file exists: {data_file.exists()}")

            if data_file.exists() and not overwrite:
                logger.warning(
                    f"Factor '{factor_name}' data already exists, use overwrite=True to replace"
                )
                return False

            # Step 1: Convert factor data to CSV format
            logger.info(f"Step 1: Saving factor as CSV")
            csv_success = self._save_factor_as_csv(factor_name, factor_data)
            logger.info(f"Step 1 result: csv_success={csv_success}")
            if not csv_success:
                return False

            # Step 2: Use dump_bin.py script to convert CSV to bin
            logger.info(f"Step 2: Converting CSV to bin")
            bin_success = self._convert_csv_to_bin(factor_name)
            logger.info(f"Step 2 result: bin_success={bin_success}")
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

    def _save_factor_as_csv(self, factor_name: str, factor_data: pd.DataFrame) -> bool:
        """
        Save factor data as CSV files in the format expected by dump_bin.py

        Args:
            factor_name: Name of the factor
            factor_data: Factor DataFrame

        Returns:
            True if save successful
        """
        try:
            # Create temporary directory for this factor
            factor_csv_dir = self.csv_temp_dir / factor_name
            factor_csv_dir.mkdir(parents=True, exist_ok=True)

            # Prepare data in dump_bin.py expected format
            csv_data = self._prepare_csv_data(factor_data, factor_name)

            if csv_data.empty:
                logger.warning(f"No data to save for factor '{factor_name}'")
                return False

            # Group by symbol and save separate CSV files (following dump_bin.py convention)
            for symbol, group_data in csv_data.groupby("symbol"):
                csv_file = factor_csv_dir / f"{symbol}.csv"
                # Sort by date to ensure proper order
                group_data = group_data.sort_values("date")
                # Remove symbol column - dump_bin.py gets symbol from filename
                columns_to_save = ["date", factor_name.lower()]
                group_data[columns_to_save].to_csv(csv_file, index=False)
                logger.debug(
                    f"Saved CSV for symbol {symbol}: {len(group_data)} records"
                )

            logger.info(
                f"✓ Factor '{factor_name}' saved as CSV: {len(csv_data.groupby('symbol'))} symbols"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to save factor '{factor_name}' as CSV: {e}")
            return False

    def _prepare_csv_data(
        self, factor_data: pd.DataFrame, factor_name: str
    ) -> pd.DataFrame:
        """
        Prepare factor data in CSV format expected by dump_bin.py

        Args:
            factor_data: Original factor DataFrame
            factor_name: Name of the factor

        Returns:
            DataFrame with 'symbol', 'date', and factor columns
        """
        try:
            # Handle MultiIndex (datetime, instrument) format
            if hasattr(factor_data.index, "get_level_values"):
                # MultiIndex case: (datetime, instrument)
                df_reset = factor_data.reset_index()

                # Check the actual index level names to determine correct order
                index_names = factor_data.index.names
                if len(df_reset.columns) >= 2:
                    # Determine which column is datetime and which is instrument
                    col_names = list(df_reset.columns)

                    # Try to identify datetime column by checking if values can be parsed as dates
                    datetime_col = None
                    instrument_col = None

                    for i, col_name in enumerate(
                        col_names[:2]
                    ):  # Check first two columns
                        try:
                            # Try to parse a sample value as datetime
                            sample_val = df_reset[col_name].iloc[0]
                            pd.to_datetime(sample_val)
                            datetime_col = col_name
                        except:
                            instrument_col = col_name

                    # If we couldn't identify by parsing, use index names as fallback
                    if datetime_col is None or instrument_col is None:
                        if (
                            "datetime" in str(index_names[0]).lower()
                            or "date" in str(index_names[0]).lower()
                        ):
                            datetime_col = col_names[0]
                            instrument_col = col_names[1]
                        else:
                            datetime_col = col_names[1]
                            instrument_col = col_names[0]

                    # Rename columns appropriately
                    rename_map = {datetime_col: "date", instrument_col: "symbol"}
                    df_reset = df_reset.rename(columns=rename_map)
                else:
                    raise ValueError(
                        "MultiIndex DataFrame should have at least 2 levels"
                    )

            else:
                # Simple index case
                df_reset = factor_data.reset_index()

                # If no symbol column, create one with default value
                if "symbol" not in df_reset.columns:
                    df_reset["symbol"] = "DEFAULT"

                # Ensure date column exists
                if "date" not in df_reset.columns and factor_data.index.name:
                    df_reset = df_reset.rename(columns={factor_data.index.name: "date"})

            # Ensure date column is properly formatted
            df_reset["date"] = pd.to_datetime(df_reset["date"]).dt.strftime("%Y-%m-%d")

            # Rename factor columns to lowercase (Qlib convention)
            factor_columns = [
                col for col in df_reset.columns if col not in ["date", "symbol"]
            ]
            for col in factor_columns:
                if col != factor_name.lower():
                    df_reset = df_reset.rename(columns={col: factor_name.lower()})

            # Ensure we have the required columns
            required_columns = ["symbol", "date", factor_name.lower()]
            if not all(col in df_reset.columns for col in required_columns):
                missing = [
                    col for col in required_columns if col not in df_reset.columns
                ]
                raise ValueError(f"Missing required columns: {missing}")

            # Select only required columns and reorder
            df_final = df_reset[required_columns].copy()

            # Remove any rows with NaN values in the factor column
            df_final = df_final.dropna(subset=[factor_name.lower()])

            logger.debug(
                f"Prepared CSV data: {len(df_final)} rows, columns: {list(df_final.columns)}"
            )
            return df_final

        except Exception as e:
            logger.error(f"Failed to prepare CSV data: {e}")
            return pd.DataFrame()

    def _convert_csv_to_bin(self, factor_name: str) -> bool:
        """
        Convert CSV files to bin format using dump_bin.py script

        Args:
            factor_name: Name of the factor

        Returns:
            True if conversion successful
        """
        try:
            logger.info(f"=== CSV TO BIN CONVERSION START for '{factor_name}' ===")
            factor_csv_dir = self.csv_temp_dir / factor_name
            logger.info(f"factor_csv_dir: {factor_csv_dir}")

            if not factor_csv_dir.exists():
                logger.error(f"CSV directory not found: {factor_csv_dir}")
                return False

            # Count CSV files
            csv_files = list(factor_csv_dir.glob("*.csv"))
            logger.info(f"Found {len(csv_files)} CSV files")
            if not csv_files:
                logger.error(f"No CSV files found in {factor_csv_dir}")
                return False

            # Use the same dump_bin.py command as convert_csv_to_qlib_format_impl
            cmd = [
                "python",
                "/app/scripts/dump_bin.py",
                "dump_all",
                "--data_path",
                str(factor_csv_dir),
                "--qlib_dir",
                str(self.storage_dir),
                "--freq",
                self.freq,
                "--date_field_name",
                "date",
            ]
            logger.info(f"dump_bin command: {' '.join(cmd)}")

            # Execute the conversion
            logger.info(f"Converting {len(csv_files)} CSV files to bin format...")
            result = subprocess.run(cmd, capture_output=True, text=True, cwd="/app")

            logger.info(f"dump_bin returncode: {result.returncode}")
            if result.stdout:
                logger.info(f"dump_bin stdout: {result.stdout[:500]}")
            if result.stderr:
                logger.info(f"dump_bin stderr: {result.stderr[:500]}")

            if result.returncode == 0:
                logger.info(
                    f"✓ Successfully converted factor '{factor_name}' to bin format"
                )

                # Clean up temporary CSV files
                import shutil

                shutil.rmtree(factor_csv_dir)
                logger.debug(f"Cleaned up temporary CSV directory: {factor_csv_dir}")

                return True
            else:
                logger.error(f"dump_bin.py conversion failed: {result.stderr}")
                return False

        except Exception as e:
            logger.error(
                f"Failed to convert CSV to bin for factor '{factor_name}': {e}"
            )
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
            factor_names = []

            if self.factors_dir.exists():
                # Look for .bin files that match our frequency
                pattern = f"*.{self.freq}.bin"
                for bin_file in self.factors_dir.glob(pattern):
                    # Extract factor name from filename
                    factor_name = bin_file.stem.replace(f".{self.freq}", "")
                    # Skip system files that start with $
                    if not factor_name.startswith("$"):
                        factor_names.append(factor_name)

            logger.info(f"Found {len(factor_names)} stored factors")
            return factor_names

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
            # Delete data file
            data_file = self.factors_dir / f"{factor_name.lower()}.{self.freq}.bin"
            if data_file.exists():
                data_file.unlink()
                logger.info(f"✓ Deleted factor data file: {data_file}")

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
                data_file = self.factors_dir / f"{factor_name.lower()}.{self.freq}.bin"
                factor_size = data_file.stat().st_size if data_file.exists() else 0
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

"""
Base Collector for Data Sources.
This module defines the abstract base class for all data collectors.
Each data source (Yahoo Finance, Tushare, etc.) must implement this interface.

Educational Notes:
- Use Python APIs directly (yfinance, tushare) not subprocess for fetching
- Convert data to CSV format
- Use Qlib's dump_bin.py script to convert CSV to .bin format
- .bin format enables Qlib's caching and compressing mechanism

Design Philosophy:
- Use Python APIs for data fetching (type-safe, easy to debug)
- Use Qlib's official dump_bin.py for format conversion (proven, optimized)
- Ensure all collectors provide the same 10 standard fields
- Fill missing fields with NaN for consistency

Data Flow:
 yfinance/tushare API -> DataFrame -> CSV -> dump_bin.py -> .bin -> D.features()
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime, date
import logging
import pandas as pd
import subprocess
from .field_config import QuantBotFieldConfig, STANDARD_FIELDS, DUMP_BIN_FIELDS_ARG

logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    """
    Abstract base class for all data collectors.

    Each data source must implement this interface to ensure consistency
    and interchangeability.

    Workflow for implementing a new collector:
    1. Inherit from BaseCollector
    2. Implement all @abstractmethod methods
    3. Use data source library (yfinance, tushare) to fetch data
    4. Convert to pandas DataFrame with standard fields
    5. Save as CSV
    6. Call _convert_to_bin() to convert to .bin format

    Example:
    ```python
    class YahooCollector(BaseCollector):
        def get_collector_name(self) -> str:
            return "yahoo"

        def collect_data(self, instruments, start_date, end_date, output_dir):
            import yfinance as yf

            csv_dir = output_dir / "csv"
            csv_dir.mkdir(parents=True, exist_ok=True)

            for instrument in instruments:
                # 1. Fetch data using yfinance
                ticker = yf.Ticker(instrument)
                df = ticker.history(start=start_date, end=end_date)

                # 2. Convert to standard format
                df = self._convert_to_standard_format(df)

                # 3. Ensure all fields exist
                df = self._ensure_all_fields(df)

                # 4. Save as CSV
                csv_file = csv_dir / f"{instrument}.csv"
                df.to_csv(csv_file, index=True)

            # 5. Convert CSV to .bin using dump_bin.py
            result = self._convert_csv_to_bin(
                csv_dir=csv_dir,
                qlib_dir=output_dir / "qlib_data"
            )

            return result
    ```

    Educational Notes:
    - @abstractmethod means subclasses MUST implement this method
    - This enforces the contract across all data sources
    - Python will raise TypeError if you try to instantiate without implementing
    """

    # Path to dump_bin.py script in container
    DUMP_BIN_SCRIPT = Path("/app/scripts/qlib/dump_bin.py")

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the collector.

        Args:
            config: Configuration dictionary (API keys, settings, etc.)

        Educational Notes:
        - config might contain API tokens, rate limits, etc.
        - Each collector can have different requirements
        """
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{self.get_collector_name()}")

    @abstractmethod
    def get_collector_name(self) -> str:
        """
        Get the unique name of this collector.

        Returns:
            Collector name (e.g., 'yahoo', 'tushare', 'akshare')

        Educational Notes:
        - Used for logging and identification
        - Should be lowercase, no spaces
        """
        pass

    @abstractmethod
    def collect_data(
        self,
        instruments: List[str],
        start_date: str,
        end_date: str,
        output_dir: Path,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Collect data from the source and convert to Qlib format

        This method should:
        1. Fetch data from the data source using its Python library
        2. Convert to pandas DataFrame with standard fields
        3. Ensure all 10 standard fields exist (fill with NaN if missing)
        4. Save as CSV files
        5. Call _convert_csv_to_bin() to convert to .bin format
        6. Return result status

        Args:
            instruments: List of instrument codes (e.g., ['SH600000', 'SZ000001'])
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            output_dir: Directory to store CSV and .bin files
            **kwargs: Additional collector-specific parameters

        Returns:
            Result dictionary with keys:
            - success: bool
            - message: str
            - instruments_count: int
            - date_range: [start_date, end_date]
            - fields: List[str] (fields that were collected)
            - csv_dir: str (path to CSV files)
            - qlib_dir: str (path to .bin files)
            - errors: List[str] (any errors encountered)

        Educational Notes:
        - This is where the actual data fetching happens
        - Each collector implements this differently:
            * YahooCollector: uses yfinance library
            * TushareCollector: uses tushare library
        - All must ensure the same 10 fields are available
        - CSV files are temporary, .bin files are the final format

        CSV Format Requirements:
        - File name: {instrument}.csv (e.g., SH600000.csv)
        - Index: date (YYYY-MM-DD format)
        - Columns: open, high, low, close, volume, factor, adj_close, vwap, amount, turnover
        """
        pass

    @abstractmethod
    def get_supported_fields(self) -> List[str]:
        """
        Get the list of fields this collector can provide.

        Returns:
            List of field names (without $ prefix)

        Educational Notes:
        - Should return all fields from STANDARD_FIELDS if possible
        - If some fields are unavailable, return what you can provide
        - Missing fields will be filled with NaN automatically

        Example:
        ```python
        def get_supported_fields(self) -> List[str]:
            # Yahoo Finance provides most standard fields
            return ['open', 'high', 'low', 'close', 'volume', 'adj_close']
            # 'factor', 'vwap', 'amount', 'turnover' will be calculated or filled with NaN
        ```
        """
        pass

    def validate_field_coverage(self) -> Dict[str, Any]:
        """
        Validate if this collector supports all required fields.

        Returns:
            Validation result from QuantBotFieldConfig.validate_collector_compatibility()

        Educational Notes:
        - Check if collector provides all fields from field_config.py
        - Warns if any fields are missing
        - Called during collector registration
        """
        supported = self.get_supported_fields()
        return QuantBotFieldConfig.validate_collector_compatibility(
            collector_name=self.get_collector_name(), supported_fields=supported
        )

    def _ensure_all_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Ensure DataFrame contains all required fields.

        If a field is missing, add it with NaN values.

        Args:
            df: pandas DataFrame with data

        Returns:
            DataFrame with all required fields

        Educational Notes:
        - This ensures field consistency across all collectors
        - Missing fields are filled with NaN (Not a number)
        - Qlib can handle NaN values in calculations
        """
        for field in STANDARD_FIELDS:
            if field not in df.columns:
                self.logger.warning(
                    f"Field '{field}' not available from {self.get_collector_name()}, "
                    f"filling with NaN"
                )
                df[field] = float("nan")

        # Ensure only standard fields are present (in correct order)
        df = df[STANDARD_FIELDS]

        return df

    def _convert_csv_to_bin(
        self, csv_dir: Path, qlib_dir: Path, freq: str = "day"
    ) -> Dict[str, Any]:
        """
        Convert CSV files to Qlib .bin format using dump_bin.py script.

        This method calls Qlib's official dump_bin.py script to convert
        CSV files to optimized .bin format with compression and caching support.

        Args:
            csv_dir: Directory containing CSV files
            qlib_dir: Directory to store .bin files
            freq: Data frequency ('day' or '1min')

        Returns:
            Result dictionary with keys:
            - success: bool
            - message: str
            - csv_dir: str
            - qlib_dir: str
            - stdout: str (command output)
            - stderr: str (error output if any)

        Educational Notes:
        - dump_bin.py is Qlib's official conversion tool
        - .bin format provides:
            * Compression (smaller file size)
            * Fast memory-mapped access
            * Qlib's caching mechanism
        - This is why we use .bin instead of CSV directly

        Command example:
        ```bash
        python /app/scripts/qlib/dump_bin.py dump_all \
            --data_path /path/to/csv \
            --qlib_dir /path/to/qlib_data \
            --include_fields open,high,low,close,volume,factor,adj_close,vwap,amount,turnover \
            --freq day
        ```
        """
        self.logger.info(f"Converting CSV to .bin format: {csv_dir} -> {qlib_dir}")

        try:
            # Ensure output directory exists
            qlib_dir.mkdir(parents=True, exist_ok=True)

            # Construct dump_bin.py command
            cmd = [
                "python",
                str(self.DUMP_BIN_SCRIPT),
                "dump_all",
                "--data_path",
                str(csv_dir),
                "--qlib_dir",
                str(qlib_dir),
                "--include_fields",
                DUMP_BIN_FIELDS_ARG,
                "--freq",
                freq,
                "--date_field_name",
                "date",
                "--file_suffix",
                ".csv",
            ]

            self.logger.info(f"Executing: {' '.join(cmd)}")

            # Execute the command
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=3600  # 1 hour timeout
            )

            success = result.returncode == 0

            if success:
                self.logger.info("Successfully converted CSV to .bin format")
            else:
                self.logger.error(f"Failed to convert CSV to .bin: {result.stderr}")

            return {
                "success": success,
                "message": (
                    "CSV to .bin conversion completed"
                    if success
                    else "Conversion failed"
                ),
                "csv_dir": str(csv_dir),
                "qlib_dir": str(qlib_dir),
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

        except subprocess.TimeoutExpired:
            self.logger.error("CSV to .bin conversion timed out after 1 hour")
            return {
                "success": False,
                "message": "Conversion timed out",
                "csv_dir": str(csv_dir),
                "qlib_dir": str(qlib_dir),
            }

        except Exception as e:
            self.logger.error(f"Error converting CSV to .bin: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "csv_dir": str(csv_dir),
                "qlib_dir": str(qlib_dir),
            }

    def get_collector_info(self) -> Dict[str, Any]:
        """
        Get information about this collector.

        Returns:
            Info dictionary with keys:
            - name: str
            - supported_fields: List[str]
            - field_coverage: Dict (from validate_field_coverage)
            - config_keys: List[str] (config parameters needed)
        """
        coverage = self.validate_field_coverage()

        return {
            "name": self.get_collector_name(),
            "supported_fields": self.get_supported_fields(),
            "field_coverage": coverage,
            "config_keys": list(self.config.keys()),
        }



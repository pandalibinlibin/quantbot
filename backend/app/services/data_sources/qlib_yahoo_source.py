"""
Qlib Yahoo Finance data source implementation.
This module wraps Qlib's official Yahoo Finance data collector scripts.
It provides a Python interface to download and manage market data using
Qlib's built-in tools.
Reference: https://github.com/microsoft/qlib/tree/main/scripts/data_collector/yahoo
"""

import subprocess
import sys
from pathlib import Path
import pandas as pd
from .base import BaseDataSource
from qlib.tests.data import GetData


class QlibYahooDataSource(BaseDataSource):
    """
    Qlib Yahoo Finance data source.

    This class wraps Qlib's official Yahoo Finance data collector.
    It uses Qlib's built-in scripts to download, normalize, and convert
    market data to Qlib's binary format.

    Advantages:
    - Official Qlib support, best compatibility
    - No API token required (free)
    - Supports multiple regions (CN, US, IN, BR)
    - Automatic data normalization and adjustment

    Data Flow:
    1. Download raw CSV data from Yahoo Finance
    2. Normalize data (adjust prices, handle splits)
    3. Convert to Qlib binary format
    4. Save to ~/.qlib/qlib_data/
    """

    def __init__(self, config: dict):
        """
        Initialize Qlib Yahoo data source.

        Args:
            config: Configuration dictionary with keys:
                - region: Market region ('cn', 'us', 'in', 'br')
                - qlib_data_dir: Path to Qlib data directory (optional)
                - delay: Delay between requests in seconds (default: 0.5)

        Example:
            >>> config = {
            ...     "region": "cn",
            ...     "qlib_data_dir": "~/.qlib/qlib_data/cn_data",
            ...     "delay": 0.5
            ... }
            >>> source = QlibYahooDataSource(config)
        """
        super().__init__(config)

        # Get configuration
        self.region = config.get("region", "cn").upper()
        self.delay = config.get("delay", 0.5)

        # Setup directories
        home = Path.home()
        qlib_data_dir = config.get("qlib_data_dir")
        if qlib_data_dir:
            self.qlib_data_dir = Path(qlib_data_dir).expanduser()
        else:
            self.qlib_data_dir = (
                home / ".qlib" / "qlib_data" / f"{self.region.lower()}_data"
            )

        # Source and normalize directories for Yahoo collector
        self.source_dir = (
            home / ".qlib" / "stock_data" / "source" / f"{self.region.lower()}_data"
        )
        self.normalize_dir = (
            home / ".qlib" / "stock_data" / "normalize" / f"{self.region.lower()}_data"
        )

    def get_stock_list(self, market: str = "stock") -> pd.DataFrame:
        """
        Get stock list from Qlib data.

        Note: This method reads from already downloaded Qlib data.
        You need to download data first using download_prebuilt_data() or collect_full_data().

        Args:
            market: Market type (not used for Qlib Yahoo source)

        Returns:
            DataFrame with stock symbols

        Raises:
            FileNotFoundError: If Qlib data not found
        """

        # TODO: Implement in next step
        raise NotImplementedError("Will implement in next step")

    def get_daily_data(
        self,
        symbols: list[str],
        start_date: str,
        end_date: str,
        fields: list[str] | None = None,
    ) -> pd.DataFrame:
        """
        Get daily data from Qlib storage.

        Note: This method reads from already downloaded Qlib data.
        For reading data, it's recommended to use Qlib's DataLoader directly.

        Args:
            symbols: List of stock symbols in Qlib format
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            fields: List of fields to read

        Returns:
            DataFrame with MultiIndex(date, symbol)

        Raises:
            NotImplementedError: Use Qlib's DataLoader instead
        """

        raise NotImplementedError(
            "Please use Qlib's DataLoader to read data: \n"
            "from qlib.data import D\n"
            "data = D.features(symbols, fields, start_time, end_time)"
        )

    def get_trading_calendar(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Get trading calendar from Qlib data.

        Note: This method reads from already downloaded Qlib data.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format

        Returns:
            DataFrame with trading dates

        Raises:
            FileNotFoundError: If Qlib data not found
        """
        # TODO: Implement in next step
        raise NotImplementedError("Will implement in next step")

    def download_prebuilt_data(self) -> dict:
        """
        Download pre-built Qlib data (quick start method).

        This method downloads ready-made Qlib data that has been pre-processed.
        It's the fastest way to get started, but data may not be the latest.

        Returns:
            dict with status and message

        Example:
            >>> source = QlibYahooDataSource({"region": "cn"})
            >>> result = source.download_prebuilt_data()
            >>> print(result["status"])
            'success'
        """

        # Use Qlib's GetData class to download pre-built data
        try:
            import subprocess
            import sys

            # Ensure target directory exists
            self.qlib_data_dir.parent.mkdir(parents=True, exist_ok=True)

            # Use subprocess to call get_data.py script with auto-confirm
            cmd = [
                sys.executable,
                "/app/scripts/get_data.py",
                "qlib_data",
                "--target_dir",
                str(self.qlib_data_dir),
                "--region",
                self.region.lower(),
            ]

            # Run with 'yes' piped to stdin to auto-confirm deletion
            result = subprocess.run(
                cmd,
                input="yes\n",
                capture_output=True,
                text=True,
                timeout=600,  # 10 minutes timeout
            )

            if result.returncode != 0:
                return {
                    "status": "error",
                    "message": f"Failed to download data: {result.stderr}",
                }

            return {
                "status": "success",
                "message": f"Pre-built data downloaded to {self.qlib_data_dir}",
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to download data: {str(e)}",
            }

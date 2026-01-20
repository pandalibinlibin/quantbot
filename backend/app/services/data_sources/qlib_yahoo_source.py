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

        try:
            # Import qlib first
            import qlib
            from ..qlib_utils import init_qlib

            # Initialize Qlib to access data
            init_qlib(provider_uri=str(self.qlib_data_dir), region=self.region)
            # Use Qlib's D module to get instrument list
            from qlib.data import D

            # Get instruments config for 'all' market
            instruments_config = D.instruments(market="all")

            # Use D.list_instruments() with a wide time range to get all stocks
            # We use a very wide time range to ensure we get all available stocks
            stock_list = D.list_instruments(
                instruments=instruments_config,
                start_time="2000-01-01",
                end_time="2099-12-31",
                freq="day",
                as_list=True,
            )

            return {
                "status": "success",
                "count": len(stock_list),
                "instruments": stock_list,
                "message": f"Found {len(stock_list)} instruments in {self.region} market",
            }
        except Exception as e:
            return {
                "status": "error",
                "count": 0,
                "instruments": [],
                "message": f"Failed to get stock list: {str(e)}",
            }

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

        try:
            # Initialize Qlib to access data
            from ..qlib_utils import init_qlib

            init_qlib(provider_uri=str(self.qlib_data_dir), region=self.region)

            # Use Qlib's D module to get daily data
            from qlib.data import D

            # Default fields if not specified
            if fields is None:
                fields = ["$open", "$high", "$low", "$close", "$volume"]
            else:
                # Convert field names to Qlib format (add $ prefix if not present)
                qlib_fields = []
                for field in fields:
                    if not field.startswith("$"):
                        qlib_fields.append(f"${field}")
                    else:
                        qlib_fields.append(field)
                fields = qlib_fields

            # Get data using Qlib's DataLoader
            data = D.features(
                instruments=symbols,
                fields=fields,
                start_time=start_date,
                end_time=end_date,
            )
            return {
                "status": "success",
                "data": data.to_dict() if data is not None else {},
                "symbols": symbols,
                "fields": fields,
                "start_date": start_date,
                "end_date": end_date,
                "message": f"Retrieved data for {len(symbols)} symbols from {start_date} to {end_date}",
            }

        except Exception as e:
            return {
                "status": "error",
                "data": {},
                "symbols": symbols,
                "fields": fields or [],
                "start_date": start_date,
                "end_date": end_date,
                "message": f"Failed to get daily data: {str(e)}",
            }

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
        try:
            # Initialize Qlib to access data
            from ..qlib_utils import init_qlib

            init_qlib(provider_uri=str(self.qlib_data_dir), region=self.region)

            # Use Qlib's D module to get trading calendar
            from qlib.data import D

            # Get trading calendar (list of trading dates)
            calendar = D.calendar(start_time=start_date, end_time=end_date)

            # Convert to list format
            trading_dates = [str(date) for date in calendar]

            return {
                "status": "success",
                "count": len(trading_dates),
                "trading_dates": trading_dates,
                "start_date": start_date,
                "end_date": end_date,
                "message": f"Found {len(trading_dates)} trading days from {start_date} to {end_date}",
            }

        except Exception as e:
            return {
                "status": "error",
                "count": 0,
                "trading_dates": [],
                "start_date": start_date,
                "end_date": end_date,
                "message": f"Failed to get trading calendar: {str(e)}",
            }

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

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

    def _convert_qlib_to_yfinance_symbol(self, qlib_symbol: str) -> str:
        """
        Convert Qlib symbol format to Yahoo Finance format.

        Args:
            qlib_symbol: Qlib format symbol (e.g., 'SH600000', 'SZ000001')

        Returns:
            Yahoo Finance format symbol (e.g., '600000.SS', '000001.SZ')
        """
        if qlib_symbol.startswith("SH"):
            # Shanghai Stock Exchange: SH600000 -> 600000.SS
            return qlib_symbol[2:] + ".SS"
        elif qlib_symbol.startswith("SZ"):
            # Shenzhen Stock Exchange: SZ000001 -> 000001.SZ
            return qlib_symbol[2:] + ".SZ"
        else:
            # For other formats, return as-is (might be already in Yahoo format)
            return qlib_symbol

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
            # Use Qlib to get comprehensive stock list, but yfinance for data
            from ..qlib_utils import init_qlib
            from qlib.data import D

            # Initialize Qlib only for getting stock list
            init_qlib(provider_uri=str(self.qlib_data_dir), region=self.region)

            # Get comprehensive stock list from Qlib
            instruments_config = D.instruments(market="all")
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
                "message": f"Found {len(stock_list)} instruments in {self.region} market (Qlib list + YFinance data)",
                "data_source": "yfinance",
                "list_source": "qlib",
                "note": "Stock list from Qlib, real-time data from YFinance",
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
            import yfinance as yf

            # Default fields if not specified
            if fields is None:
                fields = ["open", "high", "low", "close", "volume"]

            # Remove $ prefix if present (for yfinance compatibility)
            clean_fields = []
            for field in fields:
                clean_field = field.lstrip("$").lower()
                clean_fields.append(clean_field)

            all_data = {}

            for symbol in symbols:
                try:
                    # Convert Qlib format to Yahoo Finance format
                    yf_symbol = self._convert_qlib_to_yfinance_symbol(symbol)
                    ticker = yf.Ticker(yf_symbol)
                    hist = ticker.history(start=start_date, end=end_date)

                    if not hist.empty:
                        # Convert to the expected format (same as current Qlib format)
                        for clean_field in clean_fields:
                            # Map field names to yfinance columns
                            yf_field_map = {
                                "open": "Open",
                                "high": "High",
                                "low": "Low",
                                "close": "Close",
                                "volume": "Volume",
                            }

                            yf_column = yf_field_map.get(clean_field)
                            if yf_column and yf_column in hist.columns:
                                field_key = f"${clean_field}"  # Keep $ prefix for API compatibility
                                if field_key not in all_data:
                                    all_data[field_key] = {}

                                # Format: "SYMBOL,YYYY-MM-DD HH:MM:SS"
                                for date, value in hist[yf_column].items():
                                    date_str = date.strftime("%Y-%m-%d %H:%M:%S")
                                    key = f"{symbol},{date_str}"
                                    all_data[field_key][key] = float(value)

                except Exception as symbol_error:
                    print(f"Error fetching data for {symbol}: {symbol_error}")
                    continue

            return {
                "status": "success",
                "data": all_data,
                "symbols": symbols,
                "fields": [f"${field}" for field in clean_fields],
                "start_date": start_date,
                "end_date": end_date,
                "message": f"Retrieved YFinance data for {len(symbols)} symbols from {start_date} to {end_date}",
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
            import yfinance as yf

            # Use a representative stock to determine trading days
            reference_symbol = "000001.SZ" if self.region == "cn" else "AAPL"

            ticker = yf.Ticker(reference_symbol)
            hist = ticker.history(start=start_date, end=end_date)

            if hist.empty:
                return {
                    "status": "success",
                    "count": 0,
                    "trading_dates": [],
                    "start_date": start_date,
                    "end_date": end_date,
                    "message": f"No trading days found from {start_date} to {end_date}",
                }

            # Extract trading dates
            trading_dates = [date.strftime("%Y-%m-%d %H:%M:%S") for date in hist.index]

            return {
                "status": "success",
                "count": len(trading_dates),
                "trading_dates": trading_dates,
                "start_date": start_date,
                "end_date": end_date,
                "message": f"Found {len(trading_dates)} trading days from {start_date} to {end_date}",
                "reference_symbol": reference_symbol,
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

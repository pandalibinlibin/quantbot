"""
EOD Historical Data Collector for US Stock Market.

This collector uses EOD Historical Data API to fetch:
- Daily OHLCV data for US stocks
- Index constituent stocks (S&P 500, NASDAQ 100, etc.)
- Trading calendar

Educational Notes:
- EOD Historical Data is a reliable data source for US stocks
- Requires API key from https://eodhistoricaldata.com/
- Supports various indices: S&P 500, NASDAQ 100, Dow Jones, etc.
- Data format follows standard OHLCV structure
"""

import logging
import pandas as pd
import numpy as np
import requests
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path

from app.core.config import settings
from .base import BaseDataCollector
from .exceptions import DataSourceError, DataCollectionError, DataValidationError

logger = logging.getLogger(__name__)


# Market configuration for US stocks
MARKET_CONFIG = {
    "US": {
        "timezone": "America/New_York",
        "exchange": "US",
        "supported_indices": ["SP500", "NASDAQ100", "DJIA"],
    }
}

# Index code mapping for EOD Historical Data
INDEX_CODE_MAP = {
    "SP500": "GSPC.INDX",
    "NASDAQ100": "NDX.INDX",
    "DJIA": "DJI.INDX",
}

# Benchmark ETF mapping
BENCHMARK_CONFIG = {
    "SP500": {"eod_symbol": "SPY.US", "qlib_symbol": "SPY"},
    "NASDAQ100": {"eod_symbol": "QQQ.US", "qlib_symbol": "QQQ"},
    "DJIA": {"eod_symbol": "DIA.US", "qlib_symbol": "DIA"},
}

# EOD API base URL
EOD_API_BASE = "https://eodhistoricaldata.com/api"


class EODDataCollector(BaseDataCollector):
    """
    EOD Historical Data Collector for US Stock Market.

    This collector fetches daily OHLCV data from EOD Historical Data API.
    Supports S&P 500, NASDAQ 100, and other US indices.

    Educational Notes:
    - Inherits from BaseDataCollector for standard workflow integration
    - Uses EOD Historical Data API for reliable US stock data
    - Automatically handles stock symbols and data normalization
    - Supports various US market indices
    """

    def __init__(
        self,
        save_dir: str = "./qlib_data/us_data",
        start: str = "2020-01-01",
        end: str = None,
        interval: str = "1d",
        max_workers: int = 4,
        max_collector_count: int = 2,
        delay: float = 0.2,
        check_data_length: int = None,
        limit_nums: int = None,
        index_name: str = "SP500",
    ):
        """
        Initialize EOD Historical Data collector.

        Parameters
        ----------
        save_dir : str or Path
            Directory to save collected CSV files
        start : str
            Start date in YYYY-MM-DD format
        end : str, optional
            End date in YYYY-MM-DD format (defaults to today)
        interval : str, default "1d"
            Data interval (only "1d" supported)
        max_workers : int, default 4
            Number of concurrent workers
        max_collector_count : int, default 2
            Maximum retry attempts for failed collections
        delay : float, default 0.2
            Delay between requests to avoid rate limiting
        check_data_length : int, optional
            Minimum required data length for validation
        limit_nums : int, optional
            Limit number of instruments for debugging
        index_name : str, default "SP500"
            Index selection: "SP500", "NASDAQ100", "DJIA"
        """
        # Validate index parameter
        index = index_name.upper()
        if index not in MARKET_CONFIG["US"]["supported_indices"]:
            raise ValueError(
                f"Unsupported index {index}. "
                f"Supported: {MARKET_CONFIG['US']['supported_indices']}"
            )

        # Set end date to today if not provided
        if end is None:
            end = datetime.now().strftime("%Y-%m-%d")

        # Call parent constructor
        super().__init__(
            save_dir=save_dir,
            start=start,
            end=end,
            interval=interval,
            max_workers=max_workers,
            max_collector_count=max_collector_count,
            delay=delay,
            check_data_length=check_data_length,
            limit_nums=limit_nums,
        )

        self.index = index
        self._timezone = MARKET_CONFIG["US"]["timezone"]
        self._api_key = settings.EOD_API_KEY

        # Define field metadata for Qlib compatibility
        self._field_metadata = {
            "open": "float64",
            "high": "float64",
            "low": "float64",
            "close": "float64",
            "volume": "int64",
        }

        logger.info(f"EODDataCollector initialized for {index} index")
        logger.info(f"Date range: {start} to {end}")

    def _check_api_key(self):
        """Check if EOD API key is configured."""
        if not self._api_key or self._api_key == "YOUR_EOD_API_KEY_HERE":
            raise DataSourceError(
                source="eod",
                operation="initialize",
                original_error=ValueError(
                    "EOD_API_KEY not configured. Please register at https://eodhistoricaldata.com/ "
                    "and set your API key in .env file."
                ),
            )

    def get_instrument_list(self) -> List[str]:
        """
        Get list of constituent stocks for the specified index.

        Returns
        -------
        List[str]
            List of stock symbols (e.g., ['AAPL', 'MSFT', 'GOOGL'])

        Educational Notes:
        - Uses EOD fundamentals API to get index constituents
        - Returns symbols in EOD format for data collection
        - Will be normalized to Qlib format later
        """
        self._check_api_key()

        try:
            index_code = INDEX_CODE_MAP.get(self.index)
            if not index_code:
                raise ValueError(f"Unknown index: {self.index}")

            logger.info(f"Fetching {self.index} constituent stocks from EOD...")

            # Get index constituents using fundamentals API
            url = f"{EOD_API_BASE}/fundamentals/{index_code}"
            params = {
                "api_token": self._api_key,
                "fmt": "json",
            }

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Extract constituent symbols
            symbols = []
            if "Components" in data:
                for component in data["Components"].values():
                    if "Code" in component:
                        symbol = component["Code"]
                        # Add .US suffix for EOD API
                        if not symbol.endswith(".US"):
                            symbol = f"{symbol}.US"
                        symbols.append(symbol)

            if not symbols:
                # Fallback: use predefined list for common indices
                symbols = self._get_fallback_constituents()

            logger.info(f"Retrieved {len(symbols)} constituent stocks for {self.index}")
            logger.info(f"Sample: {symbols[:5]}")

            return symbols

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error fetching {self.index} constituents: {e}")
            raise DataSourceError(
                source=f"eod/{self.index}",
                operation="get_instrument_list",
                original_error=e,
            )
        except Exception as e:
            logger.error(f"Error fetching {self.index} constituents: {e}")
            raise DataSourceError(
                source=f"eod/{self.index}",
                operation="get_instrument_list",
                original_error=e,
            )

    def _get_fallback_constituents(self) -> List[str]:
        """
        Get fallback constituent list for common indices.

        Returns
        -------
        List[str]
            List of stock symbols with .US suffix
        """
        # Top holdings for common indices (fallback)
        fallback_lists = {
            "SP500": [
                "AAPL.US",
                "MSFT.US",
                "AMZN.US",
                "NVDA.US",
                "GOOGL.US",
                "META.US",
                "TSLA.US",
                "BRK-B.US",
                "UNH.US",
                "XOM.US",
                "JNJ.US",
                "JPM.US",
                "V.US",
                "PG.US",
                "MA.US",
                "HD.US",
                "CVX.US",
                "MRK.US",
                "ABBV.US",
                "LLY.US",
            ],
            "NASDAQ100": [
                "AAPL.US",
                "MSFT.US",
                "AMZN.US",
                "NVDA.US",
                "GOOGL.US",
                "META.US",
                "TSLA.US",
                "AVGO.US",
                "COST.US",
                "ASML.US",
                "PEP.US",
                "CSCO.US",
                "ADBE.US",
                "NFLX.US",
                "AMD.US",
                "INTC.US",
                "CMCSA.US",
                "TMUS.US",
                "TXN.US",
                "QCOM.US",
            ],
            "DJIA": [
                "AAPL.US",
                "MSFT.US",
                "UNH.US",
                "GS.US",
                "HD.US",
                "CAT.US",
                "MCD.US",
                "V.US",
                "AMGN.US",
                "CRM.US",
                "TRV.US",
                "AXP.US",
                "BA.US",
                "HON.US",
                "JPM.US",
            ],
        }
        return fallback_lists.get(self.index, fallback_lists["SP500"])

    def normalize_symbol(self, symbol: str) -> str:
        """
        Normalize EOD symbol to Qlib format.

        Parameters
        ----------
        symbol : str
            EOD format symbol (e.g., 'AAPL.US')

        Returns
        -------
        str
            Qlib format symbol (e.g., 'AAPL')

        Educational Notes:
        - EOD format: {symbol}.{exchange} (e.g., AAPL.US)
        - Qlib format for US: just the symbol (e.g., AAPL)
        - Remove exchange suffix for Qlib compatibility
        """
        if symbol.endswith(".US"):
            return symbol[:-3]
        return symbol

    def get_data(
        self,
        symbol: str,
        interval: str = "1d",
        start_datetime: str = None,
        end_datetime: str = None,
    ) -> pd.DataFrame:
        """
        Fetch daily OHLCV data for a single stock.

        Parameters
        ----------
        symbol : str
            EOD format symbol (e.g., 'AAPL.US')
        interval : str
            Data interval (only "1d" supported)
        start_datetime : str
            Start date in YYYY-MM-DD format
        end_datetime : str
            End date in YYYY-MM-DD format

        Returns
        -------
        pd.DataFrame
            OHLCV data with datetime index

        Educational Notes:
        - Uses EOD eod API for historical data
        - Returns data in standard OHLCV format for Qlib
        - Handles adjusted prices automatically
        """
        self._check_api_key()

        try:
            start_date = start_datetime or self.start
            end_date = end_datetime or self.end

            logger.debug(f"Fetching data for {symbol}: {start_date} to {end_date}")

            # Fetch historical data
            url = f"{EOD_API_BASE}/eod/{symbol}"
            params = {
                "api_token": self._api_key,
                "from": start_date,
                "to": end_date,
                "fmt": "json",
            }

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            if not data:
                logger.warning(f"No data returned for {symbol}")
                return pd.DataFrame()

            # Convert to DataFrame
            df = pd.DataFrame(data)

            # Rename columns to standard format
            df = df.rename(
                columns={
                    "date": "date",
                    "open": "open",
                    "high": "high",
                    "low": "low",
                    "close": "close",
                    "adjusted_close": "adj_close",
                    "volume": "volume",
                }
            )

            # Use adjusted close as close price
            if "adj_close" in df.columns:
                # Calculate adjustment ratio
                adj_ratio = df["adj_close"] / df["close"]
                # Apply to OHLC
                for col in ["open", "high", "low"]:
                    if col in df.columns:
                        df[col] = df[col] * adj_ratio
                df["close"] = df["adj_close"]

            # Select and order columns
            columns = ["date", "open", "high", "low", "close", "volume"]
            df = df[[col for col in columns if col in df.columns]]

            # Convert date to datetime and set as index
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date")
            df = df.sort_index()

            # Convert volume to int64
            if "volume" in df.columns:
                df["volume"] = df["volume"].astype(np.int64)

            logger.debug(f"Retrieved {len(df)} records for {symbol}")
            return df

        except requests.exceptions.RequestException as e:
            logger.warning(f"Network error fetching data for {symbol}: {e}")
            return pd.DataFrame()
        except Exception as e:
            logger.warning(f"Error fetching data for {symbol}: {e}")
            return pd.DataFrame()

    @staticmethod
    def get_trading_calendar(start_date: str = None, end_date: str = None) -> List[str]:
        """
        Get US trading calendar from EOD Historical Data.

        Parameters
        ----------
        start_date : str
            Start date in YYYY-MM-DD format
        end_date : str
            End date in YYYY-MM-DD format

        Returns
        -------
        List[str]
            List of trading dates in YYYY-MM-DD format

        Educational Notes:
        - Uses EOD exchange API for trading calendar
        - Filters for NYSE trading days
        - Essential for data alignment and validation
        """
        api_key = settings.EOD_API_KEY
        if not api_key or api_key == "YOUR_EOD_API_KEY_HERE":
            logger.warning("EOD_API_KEY not configured, using pandas business days")
            # Fallback to pandas business days
            if start_date is None:
                start_date = "2020-01-01"
            if end_date is None:
                end_date = datetime.now().strftime("%Y-%m-%d")

            dates = pd.bdate_range(start=start_date, end=end_date)
            return [d.strftime("%Y-%m-%d") for d in dates]

        try:
            # Use SPY data to get trading calendar
            url = f"{EOD_API_BASE}/eod/SPY.US"
            params = {
                "api_token": api_key,
                "from": start_date or "2020-01-01",
                "to": end_date or datetime.now().strftime("%Y-%m-%d"),
                "fmt": "json",
            }

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            dates = [item["date"] for item in data if "date" in item]

            return sorted(dates)

        except Exception as e:
            logger.error(f"Error fetching trading calendar: {e}")
            # Fallback to pandas business days
            if start_date is None:
                start_date = "2020-01-01"
            if end_date is None:
                end_date = datetime.now().strftime("%Y-%m-%d")

            dates = pd.bdate_range(start=start_date, end=end_date)
            return [d.strftime("%Y-%m-%d") for d in dates]

    @staticmethod
    def get_index_components(index_code: str) -> List[str]:
        """
        Get index constituent stocks from EOD Historical Data.

        Parameters
        ----------
        index_code : str
            EOD index code (e.g., 'GSPC.INDX')

        Returns
        -------
        List[str]
            List of stock symbols in Qlib format (e.g., ['AAPL', 'MSFT'])

        Educational Notes:
        - Static method for use by index_components_service
        - Returns codes in Qlib format for consistency
        """
        api_key = settings.EOD_API_KEY
        if not api_key or api_key == "YOUR_EOD_API_KEY_HERE":
            raise DataSourceError(
                source="eod",
                operation="get_index_components",
                original_error=ValueError(
                    "EOD_API_KEY not configured. Please register at https://eodhistoricaldata.com/"
                ),
            )

        try:
            url = f"{EOD_API_BASE}/fundamentals/{index_code}"
            params = {
                "api_token": api_key,
                "fmt": "json",
            }

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Extract constituent symbols
            symbols = []
            if "Components" in data:
                for component in data["Components"].values():
                    if "Code" in component:
                        symbol = component["Code"]
                        # Remove .US suffix for Qlib format
                        if symbol.endswith(".US"):
                            symbol = symbol[:-3]
                        symbols.append(symbol)

            logger.info(f"Retrieved {len(symbols)} components for {index_code}")
            return symbols

        except Exception as e:
            logger.error(f"Error fetching index components: {e}")
            raise

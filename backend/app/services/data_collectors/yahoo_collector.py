"""
Multi-Market Yahoo Finance Data Collector - Qlib Standard Implementation
This module implements a Yahoo Finance data collector supporting CN and US markets
with specific focus on major indices. Uses JSON API for constituent stock fetching.

Supported Markets and Indices:
- CN Market: CSI300 (沪深300), CSI500 (中证500)
- US Market: SP500 (标普500), NASDAQ100 (纳斯达克100)

Key Features:
- Market and index selection via constructor parameters (market, index)
- JSON API for real-time constituent stock fetching via yfiua.github.io
- Automatic stock code format conversion for Yahoo Finance compatibility
- Qlib BaseCollector inheritance for standard workflow integration
- Market-specific timezone handling (Asia/Shanghai, America/New_York)

Educational Notes:
- CN stocks: 6-digit codes converted to Yahoo format (000001 -> 000001.SZ/SS)
- US stocks: Direct symbol usage (AAPL, MSFT, GOOGL)
- Uses proven yfiua.github.io API that returns clean JSON responses
- Inherits all Qlib BaseCollector features: concurrency, retry, validation
"""

import pandas as pd
from pandas._libs import interval
import requests
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from pathlib import Path
import sys
import json
import logging

logger = logging.getLogger(__name__)

from backend.app.services.data_collectors.exceptions import DataCollectionError

# Add qlib-source to Python path for BaseCollector import
qlib_source_path = (
    Path(__file__).parent.parent.parent.parent
    / "qlib-source"
    / "scripts"
    / "data_collector"
)
sys.path.append(str(qlib_source_path))

try:
    from base import BaseCollector
except ImportError:
    raise ImportError(
        "Cannot import Qlib BaseCollector. Please ensure qlib is properly configured."
    )
try:
    from .exceptions import DataCollectionError, DataSourceError, DataValidationError
except ImportError:
    # Define basic exceptions if not available
    class DataCollectionError(Exception):
        """General data collection error"""

        pass

    class DataSourceError(DataCollectionError):
        """Data source specific error"""

        pass

    class DataValidationError(DataCollectionError):
        """Data validation error"""

        pass


# Required third-party libraries
try:
    from yahooquery import Ticker
except ImportError:
    raise ImportError(
        "yahooquery is required for Yahoo Finance data. Install with: pip install yahooquery"
    )
try:
    import requests
except ImportError:
    raise ImportError(
        "requests is required for API calls. Install with: pip install requests"
    )

# Index Constituents API Configuration
INDEX_API_CONFIG = {
    "base_url": "https://yfiua.github.io/index-constituents",
    "endpoints": {
        # Chinese Indices
        "CSI300": "/constituents-csi300.json",
        "CSI500": "/constituents-csi500.json",
        # US Indices
        "SP500": "/constituents-sp500.json",
        "NASDAQ100": "/constituents-nasdaq100.json",
    },
}

# Market Configuration
MARKET_CONFIG = {
    "CN": {
        "timezone": "Asia/Shanghai",
        "supported_indices": ["CSI300", "CSI500"],
        "exchange_mapping": {
            "60": ".SS",  # 上海主板 (600xxx, 601xxx, 605xxx)
            "68": ".SS",  # 上海科创板 (688xxx)
            "00": ".SZ",  # 深圳主板 (000xxx, 002xxx)
            "30": ".SZ",  # 深圳创业板 (300xxx)
            "12": ".SZ",  # 深圳中小板 (12xxx)
        },
    },
    "US": {
        "timezone": "America/New_York",
        "supported_indices": ["SP500", "NASDAQ100"],
        "exchange_mapping": {},  # US stocks use direct symbols
    },
}

# Request headers for API calls
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.101 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
    "Connection": "keep-alive",
}


class YahooDataCollector(BaseCollector):
    """
    Multi-Market Yahoo Finance Data Collector for Qlib.

    This collector supports both CN and US market with specific indices:
    - CN Market: CSI300, CSI500
    - US Market: SP500, NASDAQ100

    Educational Notes:
    - Inherits from Qlib's BaseCollector for standard workflow integration
    - Uses JSON API to fetch real-time index constituent stocks
    - Automatically converts stock codes to Yahoo Finance compatible format
    - Supports all BaseCollector features: concurrency, retry, validation
    """

    def __init__(
        self,
        save_dir,
        market="CN",
        index="CSI300",
        start=None,
        end=None,
        interval="1d",
        max_workers=1,
        max_collector_count=2,
        delay=0.5,
        check_data_length=None,
        limit_nums=None,
    ):
        """
        Initialize Yahoo Finance data collector for specified market and index.

        Parameters
        ----------
        save_dir : str or Path
            Directory to save collected CSV files
        market : str, default "CN"
            Market selection: "CN" or "US"
        index : str, default "CSI300"
            Index selection: "CSI300", "CSI500", "SP500", "NASDAQ100"
        start : str, optional
            Start date in YYYY-MM-DD format
        end : str, optional
            End date in YYYY-MM-DD format
        interval : str, default "1d"
            Data interval, either "1d" or "1min"
        max_workers : int, default 1
            Number of concurrent workers (recommended: 1 for Yahoo Finance)
        max_collector_count : int, default 2
            Maximum retry attempts for failed collections
        delay : float, default 0.5
            Delay between requests to avoid rate limiting
        check_data_length : int, optional
            Minimum required data length for validation
        limit_nums : int, optional
            Limit number of instruments for debugging

        Educational Notes:
        - market and index parameters determine which stocks to collect
        - All other parameters follow Qlib BaseCollector standard
        - save_dir will contain CSV files with symbol and date columns
        - Qlib will automatically handle concurrent processing and retry logic
        """
        # Validate market and index parameters
        market = market.upper()
        index = index.upper()

        if market not in MARKET_CONFIG:
            raise ValueError(
                f"Unsupported market: {market}. Supported: {list(MARKET_CONFIG.keys())}"
            )

        if index not in MARKET_CONFIG[market]["supported_indices"]:
            raise ValueError(
                f"Unsupported index {index} for market {market}. "
                f"Supported: {MARKET_CONFIG[market]['supported_indices']}"
            )

        # Call parent constructor with all Qlib standard parameters
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

        # Store market and index configuration
        self.market = market
        self.index = index
        self.market_config = MARKET_CONFIG[market]

        # Set timezone for the market
        self._timezone = self.market_config["timezone"]

        logger.info(
            f"YahooDataCollector initialized for {market} market, {index} index"
        )
        logger.info(f"Timezone: {self._timezone}")
        logger.info(
            f"Supported indices for {market}: {self.market_config['supported_indices']}"
        )

    def get_instrument_list(self) -> List[str]:
        """
        Get list of constituent stocks for the specified market and index.

        Returns
        -------
        List[str]
            List of Yahoo Finance compatible ticker symbols

        Educational Notes:
        - This is one of three required abstract methods from BaseCollector
        - Fetches real-time constituent stocks from yfiua.github.io JSON API
        - API returns JSON array with objects containing 'Symbol' and 'Name' fields
        - Symbols are already in Yahoo Finance format (CN: "000001.SZ", US: "AAPL")
        - No format conversion needed, just extract 'Symbol' from each object
        """
        try:
            logger.info(
                f"Fetching {self.index} constituent stocks for {self.market} market..."
            )

            # Build API URL
            api_endpoint = INDEX_API_CONFIG["endpoints"][self.index]
            api_url = INDEX_API_CONFIG["base_url"] + api_endpoint
            logger.info(f"API URL: {api_url}")

            # Make API request
            response = requests.get(api_url, headers=REQUEST_HEADERS, timeout=30)
            response.raise_for_status()

            # Parse JSON response
            data = response.json()
            logger.info(f"API response received, found {len(data)} items")

            # Extract symbols from JSON array
            # Expected format: [{"Symbol": "NVDA", "Name": "Nvidia"}, ...]
            symbols = []
            for item in data:
                if isinstance(item, dict) and "Symbol" in item:
                    symbol = item["Symbol"].strip()
                    if symbol:  # Only add non-empty symbols
                        symbols.append(symbol)
                else:
                    logger.warning(f"Unexpected item format: {item}")

            logger.info(f"Successfully extracted {len(symbols)} symbols")
            logger.info(f"Sample symbols: {symbols[:5] if symbols else 'None'}")

            return symbols
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error fetching {self.index} constituents: {e}")
            raise DataSourceError(f"Failed to fetch {self.index} constituents: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error for {self.index} data: {e}")
            raise DataValidationError(f"Invalid JSON response for {self.index}: {e}")
        except KeyError as e:
            logger.error(f"Missing expected field in API response: {e}")
            raise DataValidationError(f"API response missing required field: {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching {self.index} constituents: {e}")
            raise DataCollectionError(
                f"Failed to get {self.index} instrument list: {e}"
            )

    def normalize_symbol(self, symbol: str) -> str:
        """
        Normalize stock symbol to standard format for data storage.

        Parameters
        ----------
        symbol : str
            Raw stock symbol (e.g., "000001.SZ", "AAPL")

        Returns
        -------
        str
            Normalized symbol for Qlib data storage

        Educational Notes:
        - This is the second required abstract method from BaseCollector
        - Converts Yahoo Finance symbols to Qlib standard format
        - CN stocks: "000001.SZ" -> "SZ000001" (exchange prefix format)
        - US stocks: "AAPL" -> "AAPL" (keep original format)
        - Used by Qlib for consistent data file naming and indexing
        """
        try:
            symbol = symbol.strip().upper()

            if self.market == "CN":
                # Convert CN symbols from Yahoo format to Qlib format
                # "000001.SZ" -> "SZ000001", "600519.SS" -> "SH600519"
                if "." in symbol:
                    code, exchange = symbol.split(".")
                    if exchange == "SZ":
                        return f"SZ{code}"
                    elif exchange == "SS":
                        return f"SH{code}"
                    else:
                        logger.warning(
                            f"Unknown exchange suffix: {exchange} for symbol {symbol}"
                        )
                        return symbol
                else:
                    # If no exchange suffix, assume it's already normalized
                    return symbol

            elif self.market == "US":
                # US symbols remain unchanged
                return symbol
            else:
                # Fallback for unsupported markets
                return symbol

        except Exception as e:
            logger.warning(f"Failed to normalize symbol {symbol}: {e}")
            return symbol  # Return original symbol if normalization fails

    def get_data(self, symbol: str, start_time=None, end_time=None) -> pd.DataFrame:
        """
        Fetch OHLCV data for a specific stock symbol.

        Parameters
        -----------
        symbol: str
            Stock symbol in Yahoo Finance format (e.g., "000001.SZ", "AAPL")
        start_time: str, optional
            Start date in YYYY-MM-DD format
        end_time: str, optional
            End date in YYYY-MM-DD format

        Returns
        --------
        pd.DataFrame
            DataFrame with columns: ['open', 'high', 'low', 'close', 'volume']
            Index: DatetimeIndex with 'date' name

        Educational Notes:
        - This is the third required abstract method from BaseCollector
        - Uses yahooquery library to fetch historical stock data
        - Returns data in Qlib standard format with required columns
        - Handle both CN and US market data with proper timezone
        - Qlib expects 'date' index and specific column names (lowercase)
        """
        try:
            logger.info(f"Fetching data for {symbol} from {start_time} to {end_time}")

            # Use class start/end times if not provided
            if start_time is None:
                start_time = self.start
            if end_time is None:
                end_time = self.end

            # Create Ticker object
            ticker = Ticker(symbol)

            # Fetch historical data
            if self.interval == "1d":
                data = ticker.history(start=start_time, end=end_time, interval="1d")
            elif self.interval == "1min":
                data = ticker.history(start=start_time, end=end_time, interval="1m")
            else:
                raise ValueError(f"Unsupported interval: {self.interval}")

            if data is None or data.empty:
                logger.warning(f"No data returned for {symbol}")
                return pd.DataFrame()

            # Reset index to get date as column, then set it back as index
            if isinstance(data.index, pd.MultiIndex):
                data = data.reset_index()
                data = data.set_index("date")

            # Get required columns from BaseCollector's field metadata
            required_columns = list(self._field_metadata.keys())
            logger.info(f"Using field metadata columns: {required_columns}")
            data.columns = data.columns.lower()

            # Select only required columns
            data = data[required_columns]

            # Ensure index is named 'date'
            data.index.name = "date"
            logger.info(f"Successfully fetched {len(data)} records for {symbol}")
            return data

        except Exception as e:
            logger.error(f"Failed to fetch data for {symbol}: {e}")
            # Return empty DataFrame with correct structure
            return pd.DataFrame(columns=list(self._field_metadata.keys()))

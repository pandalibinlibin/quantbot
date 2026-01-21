"""
YFinance data provider implementation.
This module provides real-time and historical stock data from Yahoo Finance
through the yfinance library, implementing the BaseDataProvider interface.

Key Features:
- Real-time stock data from Yahoo Finance
- Automatic symbol format conversion (Qlib <-> Yahoo Finance)
- Qlib-compatible MultiIndex DataFrame output
- Multi-API strategy for comprehensive field coverage
- Support for extended fields beyond basic OHLCV

Educational Notes:
- Qlib uses MultiIndex DataFrames with (datetime, instrument) as index
- Yahoo Finance uses different symbol formats than Qlib
- Forward-adjusted prices (adj_close) are preferred for quantitative analysis
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Union
import logging
from .base_data_provider import BaseDataProvider

# Configure logging
logger = logging.getLogger(__name__)


class YFinanceProvider(BaseDataProvider):
    """
    YFinance data provider for real-time stock market data.

    This class implements the BaseDataProvider interface to fetch real-time
    and historical stock data from Yahoo Finance. It provides Qlib-compatible
    data loading for use with factor calculation engines like Alpha158.

    Default Fields (when fields=None):
    - open, high, low, close, volume: Basic OHLCV data
    - adj_close: Forward-adjusted closing price

    Available Field Categories:
    - Basic OHLCV: open, high, low, close, volume, adj_close
    - Company Info: market_cap, pe_ratio, pb_ratio, dividend_yield
    - Calculated: returns, volatility (future extension)

    Symbol Format Conversion:
    - Qlib format: SH600000 (Shanghai), SZ000001 (Shenzhen)
    - Yahoo Finance format: 600000.SS (Shanghai), 000001.SZ (Shenzhen)
    - US stocks: AAPL remains AAPL (no conversion needed)

    Educational Background:
    - Qlib DataLoader interface ensures compatibility with factor engines
    - MultiIndex DataFrame format is required for Qlib's time-series operations
    - Forward-adjusted prices account for dividends and stock splits
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize YFinance data provider.

        Args:
            config: Configuration dictionary with keys:
            - region: Market region (default: 'cn' for China)
            - timeout: Request timeout in seconds (default: 30)
            - cache_enabled: Enable data caching (default: True)
            - max_retries: Maximum retry attempts (default: 3)

        Educational Notes:
        - config allows flexible configuration for different markets
        - caching improves performance for repeated requests
        - timeout prevents hanging requests
        """

        super().__init__(config)
        self.timeout = config.get("timeout", 30)
        self.cache_enabled = config.get("cache_enabled", True)
        self.max_retries = config.get("max_retries", 3)

        # Initialize cache if enabled
        self._cache = {} if self.cache_enabled else None

        logger.info(f"YFinanceDataProvider initialized for region: {self.region}")

    def get_data_source_name(self) -> str:
        """
        Get the name of this data source.

        Returns:
            String identifier for this data source
        """

        return "yfinance"

    def _convert_qlib_to_yfinance_symbol(self, qlib_symbol: str) -> str:
        """
        Convert Qlib symbol format to Yahoo Finance format.

        This method handles the symbol format conversion between Qlib's internal
        representation and Yahoo Finance's API requirements.

        Args:
            qlib_symbol: Qlib format symbol (e.g., 'SH600000', 'SZ000001', 'AAPL')

        Returns:
            Yahoo Finance format symbol (e.g., '600000.SS', '000001.SZ', 'AAPL')

        Educational Notes:
        - Shanghai Stock Exchange: SH prefix becomes .SS suffix
        - Shenzhen Stock Exchange: SZ prefix becomes .SZ suffix
        - US and other markets: no conversion needed
        - This conversion is essential for Yahoo Finance API calls

        Examples:
            SH600000 -> 600000.SS
            SZ000001 -> 000001.SZ
            AAPL -> AAPL
        """
        if qlib_symbol.startswith("SH"):
            # Shanghai Stock Exchange: remove SH prefix, add .SS suffix
            return qlib_symbol[2:] + ".SS"
        elif qlib_symbol.startswith("SZ"):
            # Shenzhen Stock Exchange: remove SZ prefix, add .SZ suffix
            return qlib_symbol[2:] + ".SZ"
        else:
            # For other markets (US, etc.), return as-is
            return qlib_symbol

    def _convert_yfinance_to_qlib_symbol(self, yf_symbol: str) -> str:
        """
        Convert Yahoo Finance symbol format to Qlib format.

        This method performs the reverse conversion, useful for data processing
        and ensuring consistency in our system.

        Args:
            yf_symbol: Yahoo Finance format symbol (e.g. , '600000.SS', '000001.SZ', 'AAPL')

        Returns:
            Qlib format symbol (e.g., 'SH600000', 'SZ000001', 'AAPL')

        Educational Notes:
        - This is the reverse of _convert_qlib_to_yfinance_symbol
        - Useful when processing Yahoo Finance response
        - Maintains consistency with Qlib's symbol conventions

        Examples:
            600000.SS -> SH600000
            000001.SZ -> SZ000001
            AAPL -> AAPL
        """
        if yf_symbol.endswith(".SS"):
            # Shanghai Stock Exchange: remove .SS suffix, add SH prefix
            return "SH" + yf_symbol[:-3]
        elif yf_symbol.endswith(".SZ"):
            # Shenzhen Stock Exchange: remove .SZ suffix, add SZ prefix
            return "SZ" + yf_symbol[:-3]
        else:
            # For other markets, return as-is
            return yf_symbol

    def _categorize_fields(self, fields: List[str]) -> Dict[str, List[str]]:
        """
        Categorize requested fields by their data source.

        This method analyzes the requested fields and groups them by the
        Yahoo Finance API endpoint that provides the data.

        Args:
            fields: List of field names (without $ prefix)

        Returns:
            Dictionary with categories as keys and field lists as values

        Educational Notes:
        - Different fields come from different Yahoo Finance APIs
        - Categorization enables targeted API calls
        - Reduces unnecessary API requests and improves performance

        Field Categories:
        - history: Basic OHLCV data from ticker.history()
        - info: Company information from ticker.info()
        - calculated: Derived fields computed from basic data
        """
        # Define field categories and their sources
        field_categories = {
            "history": ["open", "high", "low", "close", "volume", "adj_close"],
            "info": [
                "market_cap",
                "pe_ratio",
                "pb_ratio",
                "dividend_yield",
                "shares_outstanding",
            ],
            "calculated": ["returns", "volatility", "rsi", "macd", "moving_average"],
        }

        # Initialize result dictionary
        categorized = {"history": [], "info": [], "calculated": [], "unsupported": []}

        # Categorize each requested field
        for field in fields:
            field_found = False
            for category, category_fields in field_categories.items():
                if field in category_fields:
                    categorized[category].append(field)
                    field_found = True
                    break

            if not field_found:
                categorized["unsupported"].append(field)

        # Log categorization results
        logger.debug(f"Field categorization: {categorized}")

        return categorized

    def _fetch_history_data(
        self, ticker, start_date: str, end_date: str, fields: List[str]
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV data from ticker.history().

        Args:
            ticker: yfinance Ticker object
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format
            fields: List of history fields to fetch

        Returns:
            DataFrame with requested history fields in Qlib format

        Raises:
            ValueError: If requested fields are not available
            RuntimeError: If data fetching fails

        Educational Notes:
        - ticker.history() is the primary API for price data
         - Returns DataFrame with Date index and OHLCV columns
        - We rename columns to Qlib format (with $ prefix)
        """
        try:
            # Fetch historical data
            hist = ticker.history(start=start_date, end=end_date)
            if hist.empty:
                logger.warning("No historical data returned")
                return pd.DataFrame()

            # Define column mapping from Yahoo Finance to Qlib format
            column_mapping = {
                "Open": "$open",
                "High": "$high",
                "Low": "$low",
                "Close": "$close",
                "Volume": "$volume",
                "Adj Close": "$adj_close",
            }

            # Build result DataFrame with requested fields
            result_data = pd.DataFrame(index=hist.index)
            missing_fields = []

            for field in fields:
                # Find corresponding Yahoo Finance column
                yf_column = None
                for yf_col, qlib_col in column_mapping.items():
                    if qlib_col == f"${field}":
                        yf_column = yf_col
                        break

                if yf_column and yf_column in hist.columns:
                    result_data[f"${field}"] = hist[yf_column]
                else:
                    missing_fields.append(field)

            if missing_fields:
                raise ValueError(f"Historical fields not available: {missing_fields}")

            logger.debug(
                f"Successfully fetched {len(result_data)} rows of historical data"
            )

            return result_data
        except ValueError:
            raise
        except Exception as e:
            raise RuntimeError(f"Failed to fetch historical data: {str(e)}")

    def _fetch_info_data(
        self, ticker, start_date: str, end_date: str, fields: List[str]
    ) -> pd.DataFrame:
        """
        Fetch company info and create time series data.

        Args:
            ticker: yfinance Ticker object
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format
            fields: List of info fields to fetch

        Returns:
            DataFrame with requested info fields in Qlib format

        Educational Notes:
        - ticker.info provides company fundamentals
        - Info data is static, so we repeat values across date range
        - Useful for fundamental analysis and factor calculation
        """
        try:
            # Fetch company info
            info = ticker.info
            if not info:
                raise ValueError("No company info available")

            # Create date range for time series
            date_range = pd.date_range(start=start_date, end=end_date, freq="D")
            result_data = pd.DataFrame(index=date_range)

            # Define info field mapping
            info_mapping = {
                "market_cap": "marketCap",
                "pe_ratio": "trailingPE",
                "pb_ratio": "priceToBook",
                "dividend_yield": "dividendYield",
                "shares_outstanding": "sharesOutstanding",
            }

            missing_fields = []

            for field in fields:
                info_key = info_mapping.get(field)
                if info_key and info_key in info and info[info_key] is not None:
                    # Repeat static value across all dates
                    result_data[f"${field}"] = info[info_key]
                else:
                    missing_fields.append(field)

            if missing_fields:
                raise ValueError(f"Info fields not available: {missing_fields}")

            logger.debug(f"Successfully fetched info data for {len(fields)} fields")

            return result_data

        except ValueError:
            raise
        except Exception as e:
            raise RuntimeError(f"Failed to fetch company info: {str(e)}")

    def load(
        self, instruments=None, start_time=None, end_time=None, fields=None
    ) -> pd.DataFrame:
        """
        Load data in Qlib-compatible format.

        This is the core method that implements Qlib's DataLoader interface.
        It orchestrates multiple Yahoo Finance APIs to fetch comprehensive
        data and returns it in the MultiIndex DataFrame format required by Qlib.

        Args:
            instruments: List of stock symbols in Qlib format (e.g., ['SH600000', 'SZ000001'])
            start_time: Start date (str, datetime, or date)
            end_time: End date (str, datetime, or date)
            fields: List of field names to load. If None, defaults to OHLCV + adj_close

        Returns:
            pandas.DataFrame with MultiIndex (datetime, instrument) and requested columns

        Raises:
            ValueError: If required parameters are missing or invalid
            RuntimeError: If data fetching fails

        Educational Notes:
        - This method is called by Qlib's factor calculation engines
        - MultiIndex format enables efficient time-series operations
        - Default fields include adj_close for quantitative analysis
        - Multiple API strategy ensures comprehensive data coverage

        Data Flow:
        1. Validate inputs and normalize parameters
        2. Set default fields if not specified
        3. Categorize fields by data source
        4. Fetch data from multiple Yahoo Finance APIs
        5. Combine and format as MultiIndex DataFrame
        """
        try:
            # Step 1: Validate inputs
            if not instruments:
                raise ValueError("Instruments list cannot be empty")

            if not start_time or not end_time:
                raise ValueError("Start time and end time are required")

            # Normalize dates using inherited method
            start_date = self._normalize_date(start_time)
            end_date = self._normalize_date(end_time)

            # Validate and normalize symbols using inherited method
            validated_symbols = self._validate_symbols(instruments)

            # Step 2: Set default fields if not specified
            if fields is None:
                # Default: OHLCV + adj_close for quantitative analysis
                requested_fields = [
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                    "adj_close",
                ]
            else:
                # Clean field names (remove $ prefix if present)
                requested_fields = [field.lstrip("$") for field in fields]

            logger.info(
                f"Loading data for {len(validated_symbols)} instruments from {start_date} to {end_date}"
            )
            logger.info(f"Requested fields: {requested_fields}")

            # Step 3: Categorize fields by data source
            categorized_fields = self._categorize_fields(requested_fields)

            # Check for unsupported fields
            if categorized_fields["unsupported"]:
                raise ValueError(
                    f"Unsupported fields: {categorized_fields['unsupported']}"
                )

            # Step 4: Fetch data for each symbol
            all_symbol_data = []

            for qlib_symbol in validated_symbols:
                try:
                    logger.debug(f"Processing symbol: {qlib_symbol}")

                    # Convert to Yahoo Finance format
                    yf_symbol = self._convert_qlib_to_yfinance_symbol(qlib_symbol)

                    # Initialize ticker
                    ticker = yf.Ticker(yf_symbol)

                    # Collect data from different sources
                    symbol_data_parts = []

                    # Fetch historical data if needed
                    if categorized_fields["history"]:
                        logger.debug(
                            f"Fetching history data for {qlib_symbol}: {categorized_fields['history']}"
                        )
                        hist_data = self._fetch_history_data(
                            ticker, start_date, end_date, categorized_fields["history"]
                        )
                        if not hist_data.empty:
                            symbol_data_parts.append(hist_data)

                    # Fetch company info if needed
                    if categorized_fields["info"]:
                        logger.debug(
                            f"Fetching info data for {qlib_symbol}: {categorized_fields['info']}"
                        )
                        info_data = self._fetch_info_data(
                            ticker, start_date, end_date, categorized_fields["info"]
                        )
                        if not info_data.empty:
                            symbol_data_parts.append(info_data)

                    # TODO: Add calculated fields support in future
                    if categorized_fields["calculated"]:
                        logger.warning(
                            f"Calculated fields not yet implemented: {categorized_fields['calculated']}"
                        )

                    # Combine data parts for this symbol
                    if symbol_data_parts:
                        # Merge all data parts on date index
                        symbol_data = symbol_data_parts[0]
                        for part in symbol_data_parts[1:]:
                            symbol_data = pd.concat([symbol_data, part], axis=1)

                        # Add instrument column for MultiIndex
                        symbol_data["instrument"] = qlib_symbol
                        symbol_data.reset_index(inplace=True)
                        all_symbol_data.append(symbol_data)

                        logger.debug(
                            f"Successfully processed {qlib_symbol}: {symbol_data.shape}"
                        )

                    else:
                        logger.warning(f"No data retrieved for symbol: {qlib_symbol}")

                except Exception as e:
                    logger.warning(f"Failed to process symbol {qlib_symbol}: {str(e)}")
                    continue

            # Step 5: Combine all symbols into final MultiIndex DataFrame
            if not all_symbol_data:
                logger.warning("No data loaded for any instruments")
                return pd.DataFrame()

            # Concatenate all symbol data
            combined_data = pd.concat(all_symbol_data, ignore_index=True)

            # Create MultiIndex (datetime, instrument) - Qlib standard format
            combined_data.set_index(["Date", "instrument"], inplace=True)
            combined_data.index.names = ["datetime", "instrument"]

            # Sort by datetime and instrument for optimal performance
            combined_data.sort_index(inplace=True)

            # Validate final result
            if combined_data.empty:
                logger.warning("Final combined data is empty")
                return pd.DataFrame()

            logger.info(
                f"Successfully loaded data: {combined_data.shape[0]} rows, {combined_data.shape[1]} columns"
            )
            logger.info(
                f"Date range: {combined_data.index.get_level_values('datetime').min()} to {combined_data.index.get_level_values('datetime').max()}"
            )
            logger.info(
                f"Instruments: {combined_data.index.get_level_values('instrument').unique().tolist()}"
            )
            logger.info(f"Fields: {combined_data.columns.tolist()}")

            return combined_data

        except ValueError:
            # Re-raise validation errors as-is
            raise
        except Exception as e:
            logger.error(f"Failed to load data: {str(e)}")
            raise RuntimeError(f"Data loading failed: {str(e)}")

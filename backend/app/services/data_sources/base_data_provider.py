"""
Base data provider interface for quantitative data sources.
This module defines the standard interface that all data providers must implement
to ensure consistency and interoperability across different data sources.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, date
import pandas as pd
from qlib.data.dataset.loader import DataLoader


class BaseDataProvider(DataLoader, ABC):
    """
    Abstract base class for all data providers.

    This class defines the standard interface that all data providers must implement.
    It inherits from Qlib's DataLoader to ensure compatibility with Qlib's factor
    calculation engines.

    Design Philosophy:
    - Dual Interface: Both Qlib DataLoader and Web API compatibility
    - Separation of Concerns: Data acquisition separate from factor calculation
    - Standardized Responses: Consistent error handling and response formats
    - High Performance: Native Qlib integration for optimal performance

    All data providers should:
    1. Implement the load() method for Qlib compatibility
    2. Handle data format conversion between source and Qlib formats
    3. Provide metadata about available instruments and date ranges
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize data provider with configuration.

        Args:
            config: Configuration dictionary containing provider-specific settings
                    Common keys: region, cache_enabled, timeout, etc.
        """
        super().__init__()
        self.config = config
        self.region = config.get("region", "cn").lower()

    # Qlib Dataloader Interface (Required for Factor Calculation)
    @abstractmethod
    def load(
        self, instruments=None, start_time=None, end_time=None, fields=None
    ) -> pd.DataFrame:
        """
        Load data in Qlib-compatible format.

        This method implements Qlib's DataLoader interface and must return
        a DataFrame with MultiIndex (datetime, instrument) and requested columns.
        This is the core method that enables Qlib's factor calculation engines
        like Alpha158 to work with real-time data sources.

        Args:
            instruments: List of stock symbols (e.g., ['SH600000', 'SZ000001'])
            start_time: Start date (str, datetime, or date)
            end_time: End date (str, datetime, or date)
            fields: List of field names to load (e.g., ['open', 'high', 'low', 'close', 'volume'])
                    If None, defaults to OHLCV fields. Supports extended fields like:
                    - Basic: ['open', 'high', 'low', 'close', 'volume']
                    - Extended: ['adj_close', 'turnover', 'market_cap', 'pe_ratio']

        Returns:
            pandas.DataFrame with MultiIndex (datetime, instrument) and columns:
            - $open, $high, $low, $close, $volume: Basic OHLCV data
            - Additional fields as requested (with $ prefix)

        Raises:
            ValueError: If required parameters are missing or invalid
            RuntimeError: If data fetching fails
        """
        pass

    @abstractmethod
    def get_data_source_name(self) -> str:
        """
        Get the name of the data source.

        Returns:
            String name of the data source (e.g., 'yfinance', 'tushare', 'akshare')
        """
        pass

    # Utility Methods (Shared Implementation)
    def get_provider_info(self) -> Dict[str, Any]:
        """
        Get information about this data provider.

        Returns:
            Dictionary containing provider metadata
        """
        return {
            "provider_name": self.__class__.__name__,
            "region": self.region,
            "data_source": self.get_data_source_name(),
            "qlib_compatible": True,
            "config": {k: v for k, v in self.config.items() if not k.startswith("_")},
        }

    def _normalize_date(self, date_input: Union[str, datetime, date]) -> str:
        """
        Normalize date input to string format.

        Args:
            date_input: Date in various formats

        Returns:
            Date string in 'YYYY-MM-DD' format

        Raises:
            ValueError: If date format is not supported
        """
        if isinstance(date_input, str):
            return date_input
        elif isinstance(date_input, (datetime, date)):
            return date_input.strftime("%Y-%m-%d")
        else:
            raise ValueError(f"Unsupported date format: {type(date_input)}")

    def _validate_symbols(self, symbols: List[str]) -> List[str]:
        """
        Validate and normalize stock symbols.

        Args:
            symbols: List of stock symbols

        Returns:
            List of validated and normalized symbols

        Raises:
            ValueError: If symbols list is empty or invalid
        """
        if not symbols:
            raise ValueError("Symbols list cannot be empty")

        validated_symbols = []
        for symbol in symbols:
            if not isinstance(symbol, str) or not symbol.strip():
                raise ValueError(f"Invalid symbol: {symbol}")

            validated_symbols.append(symbol.upper().strip())

        return validated_symbols

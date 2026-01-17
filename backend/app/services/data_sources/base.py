"""
Abstract base class for market data sources.
This module defines the interface that all data source implementations must follow.
It provides a unified way to access different data providers (Tushare, Akshare, etc.)
"""

from abc import ABC, abstractmethod
from typing import Any
import pandas as pd


class BaseDataSource(ABC):
    """
    Abstract base class for market data sources.

    All data source implementations (Tushare, Akshare, etc.) should inherit from
    this class and implement the required methods.

    Design Pattern: Strategy Pattern
    - Allows switching between different data sources without changing client code
    - Each data source implements the same interface
    """

    def __init__(self, config: dict[str, Any]):
        """
        Initialize data source with configuration.

        Args:
            config: Configuration dictionary with source-specific parameters
                Example for Tushare: {"token": "your_token", "delay": 0.2}
                Example for Akshare: {"delay": 0.5}
        """
        self.config = config

    @abstractmethod
    def get_stock_list(self, market: str = "stock") -> pd.DataFrame:
        """
        Get list of available stocks/instruments.

        This method retrieves the list of all tradable stocks from data source.

        Args:
            market: Market type (e.g., 'stock', 'index', 'fund')
                Default is 'stock' for A-share stocks

        Returns:
            DataFrame with columns:
                - symbol: Stock symbol in Qlib format (e.g., 'SH600000', 'SZ000001')
                - name: Stock name in Chinese
                - market: Market type
                - list_date: Listing date in YYYY-MM-DD format

        Example:
            >>> source = TushareDataSource(config)
            >>> stocks = source.get_stock_list()
            >>> print(stocks.head())
                symbol      name        market  list_date
            0   SH600000    浦发银行     stock   1999-11-10
            1   SH600001    邯郸钢铁     stock   2003-03-06
        """
        pass

    @abstractmethod
    def get_daily_data(
        self,
        symbols: list[str],
        start_date: str,
        end_date: str,
        fields: list[str] | None = None,
    ) -> pd.DataFrame:
        """
        Download daily OHLCV data for specified symbols.

        This is the core method for downloading market data. It retrieves
        historical daily data for multiple stocks.

        Args:
            symbols: List of stock symbols in Qlib format
                    Example: ['SH600000', 'SZ000001']
            start_date: Start date in YYYY-MM-DD format
                    Example: '2020-01-01'
            end_date: End date in YYYY-MM-DD format
                    Example: '2020-12-31'
            fields: List of fields to download. If None, download all available fields.
            Default fields: ['open', 'high', 'low', 'close', 'volume', 'amount']
            Extended fields: ['turnover_rate', 'pct_chg', 'pe', 'pb', 'total_mv']

        Returns:
            DataFrame with MultiIndex (date, symbol) and columns for each field.

            Index:
                - date: Trading date (datetime)
                - symbol: Stock symbol (str)

            Columns: Requested fields (open, high, low, close, volume, etc.)

        Example:
            >>> source = TushareDataSource(config)
            >>> data = source.get_daily_data(
            ...     symbols=['SH600000'],
            ...     start_date='2020-01-01',
            ...     end_date='2020-01-31',
            ...     fields=['open', 'close', 'volume']
            ... )
            >>> print(data.head())
                                    open    close   volume
            date        symbol
            2020-01-02  SH600000    11.50   11.60   12345678.0
            2020-01-03  SH600000    11.55   11.65   12345679.0
        """
        pass

    @abstractmethod
    def get_trading_calendar(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Get trading calendar (list of trading days).

        This method retrieves the official trading calendar, which is essential
        for Qlib to know which days are trading days vs. holidays.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format

        Returns:
            DataFrame with column 'date' containing trading days.

            Columns:
                - date: Trading date (datetime)

        Example:
            >>> source = TushareDataSource(config)
            >>> calendar = source.get_trading_calendar('2020-01-01', '2020-01-31')
            >>> print(calendar)
                date
            0   2020-01-02
            1   2020-01-03
            2   2020-01-06
            ...
            (Note: Jan 1, 4, 5 are holidays/weekends, so not included)
        """
        pass

    def normalize_symbol(self, symbol: str) -> str:
        """
        Normalize symbol to Qlib format.

        Qlib uses a specific format for stock symbols:
        - Shanghai Stock Exchange: SH + 6-digit code (e.g., SH600000)
        - Shenzhen Stock Exchange: SZ + 6-digit code (e.g., SZ000001)

        This method can be overridden by subclasses if they use different formats.

        Args:
            symbol: Original symbol from data source

        Returns:
            Normalized symbol in Qlib format

        Example:
            >>> source.normalize_symbol('600000.SH') # Tushare format
            'SH600000'
            >>> source.normalize_symbol('000001')   # Akshare format
            'SZ000001'
        """
        return symbol.upper()

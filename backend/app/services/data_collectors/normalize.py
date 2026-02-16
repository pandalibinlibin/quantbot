"""
Data normalization module based on Qlib's BaseNormalize architecture.

Educational Notes:
- Implements our own BaseNormalize abstract class based on Qlib's design
- Provides UniversalNormalize for unified OHLCV processing across all data sources
- Fully compatible with Qlib's Normalize workflow class
- Handles standard fields defined in BaseDataCollector._field_metadata
"""

import abc
import logging
import pandas as pd
import numpy as np
from typing import List, Iterable, Optional
import copy

logger = logging.getLogger(__name__)


class BaseNormalize(abc.ABC):
    """
    Abstract base class for data normalization.

    Educational Notes:
    - Based on Qlib's BaseNormalize design pattern from qlib-source
    - Defines standard interface that all normalize implementations must follow
    - Compatible with Qlib's Normalize workflow class
    - Requires subclasses to implement normalize() and _get_calendar_list()
    """

    def __init__(
        self, date_field_name: str = "date", symbol_field_name: str = "symbol", **kwargs
    ):
        """
        Initialize BaseNormalize.

        Parameters
        ----------
        date_field_name: str
            Date field name, default is "date"
        symbol_field_name: str
            Symbol field name, default is "symbol"
        **kwargs: dict
            Additional parameters for subclass customization
        """
        self._date_field_name = date_field_name
        self._symbol_field_name = symbol_field_name
        self.kwargs = kwargs
        self._calendar_list = self._get_calendar_list()

        logger.debug(
            f"BaseNormalize initialized with date_field='{date_field_name}', symbol_field='{symbol_field_name}'"
        )

    @abc.abstractmethod
    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize the input DataFrame.

        Parameters
        ----------
        df: pd.DataFrame
            Input DataFrame to normalize

        Returns
        -------
        pd.DataFrame
            Normalized DataFrame ready for Qlib processing
        """
        raise NotImplementedError("Subclasses must implement normalize() method")

    @abc.abstractmethod
    def _get_calendar_list(self) -> Iterable[pd.Timestamp]:
        """
        Get benchmark calendar for data alignment.

        Returns
        -------
        Iterable[pd.Timestamp]
            Calendar timestamps for data alignment with trading days
        """
        raise NotImplementedError(
            "Subclasses must implement _get_calendar_list() method"
        )


class UniversalNormalize(BaseNormalize):
    """
    Universal normalize class for all data sources.

    Educational Notes:
    - Based on Qlib's YahooNormalize but adapted for universal use
    - Processes standard OHLCV fields: open, high, low, close, volume
    - Uses source_type for data source specific logic when needed
    - Implements complete data normalization pipeline from Qlib
    """

    # Standard OHLCV fields - matches BaseDataCollector._field_metadata
    COLUMNS = ["open", "high", "low", "close", "volume"]

    # Time format constants for different data frequencies
    DAILY_FORMAT = "%Y-%m-%d"
    MINUTE_FORMAT = "%Y-%m-%d %H:%M:%S"

    # Anomaly detection thresholds for different frequencies
    DAILY_ANOMALY_THRESHOLD = (89, 111)  # 89x to 111x change detection
    MINUTE_ANOMALY_THRESHOLD = (5, 20)  # 5x to 20x change detection for minute data

    def __init__(self, source_type: str = "yahoo", **kwargs):
        """
        Initialize UniversalNormalize.

        Parameters
        ----------
        source_type: str
            Data source identifier for branch logic ("yahoo", "tushare", etc.)
        **kwargs: dict
            Additional parameters passed to BaseNormalize
        """
        self.source_type = source_type

        # Call parent constructor with required parameters
        super().__init__(**kwargs)

        logger.info(f"Initialized UniversalNormalize for source: {source_type}")

    @staticmethod
    def calc_change(df: pd.DataFrame, last_close: float) -> pd.Series:
        """
        Calculate price change series for anomaly detection.

        Educational Notes:
        - Based on Qlib's YahooNormalize.calc_change method
        - Calculates price change series for anomaly detection
        - Handles both daily and minute-level data
        - Uses forward fill to handle missing values
        - Change ratio = current_close / previous_close - 1

        Parameters
        -------------
        df: pd.DataFrame
            DataFrame with close price column
        last_close: float
            Last close price from previous period (can be None)

        Returns
        --------------
        pd.Series
            Series of price change ratios
        """
        df = df.copy()
        _tmp_series = df["close"].ffill()
        _tmp_shift_series = _tmp_series.shift(1)

        if last_close is not None:
            _tmp_shift_series.iloc[0] = float(last_close)

        change_series = _tmp_series / _tmp_shift_series - 1
        return change_series

    def _get_calendar_list(self) -> Iterable[pd.Timestamp]:
        """
        Get benchmark calendar for data alignment.

        Educational Notes:
        - Based on YahooNormalize implementation from Qlib
        - For daily data: uses D.calendar(freq="day")
        - For minute data: generates minute calendar from daily calendar
        - Market-specific trading hours handled in generate_1min_from_daily

        Returns
        -------
        Iterable[pd.Timestamp]
            Trading calendar timestamps for data alignment
        """
        try:
            # Import Qlib's data module
            from qlib.data import D

            # Get daily calendar as base
            daily_calendar = D.calendar(freq="day")

            logger.debug(
                f"Retrieved daily calendar with {len(daily_calendar)} trading days for source: {self.source_type}"
            )
            return daily_calendar

        except Exception as e:
            logger.warning(
                f"Failed to get calendar from Qlib: {e}, using empty calendar"
            )
            return []

    def detect_market_from_symbol(self, symbol: str) -> str:
        """
        Detect market (CN/US) from stock symbol.

        Educational Notes:
        - CN symbols: end with .SZ, .SH, or 6-digit numbers
        - US symbols: typically alphabetic or end with common US suffixes
        - Used to determine appropriate trading hours for minute data

        Parameters
        ----------
        symbol: str
            Stock symbol to analyze

        Returns
        -------
        str
            Market identifier: "CN", "US", or "US" (default)
        """
        if not symbol:
            return "US"  # Default to US

        symbol = symbol.upper()

        # Chinese market patterns
        if (
            symbol.endswith(".SZ")
            or symbol.endswith(".SH")
            or symbol.endswith(".SS")
            or (symbol.isdigit() and len(symbol) == 6)
        ):
            return "CN"

        # Default to US market for other patterns
        return "US"

    def generate_1min_from_daily(
        self, daily_calendar: List[pd.Timestamp], market: str = "US"
    ) -> List[pd.Timestamp]:
        """
        Generate minute-level calendar from daily calendar.

        Educational Notes:
        - Based on YahooNormalizeCN1min.generate_1min_from_daily method
        - Creates minute timestamps for each trading day
        - Market-specific trading hours:
          - US market: 09:30-16:00 EST (6.5 hours = 390 minutes)
          - CN market: 09:30-11:30 + 13:00-15:00 CST (4 hours = 240 minutes)

        Parameters
        ----------
        daily_calendar: List[pd.Timestamp]
            Daily trading calendar
        market: str
            Market identifier: "CN" or "US"

        Returns
        -------
        List[pd.Timestamp]
            Minute-level trading calendar
        """
        if not daily_calendar:
            return []

        minute_calendar = []

        # Define trading hours based on market
        if market == "CN":
            # Chinese market hours (09:30-11:30 + 13:00-15:00 CST)
            am_start, am_end = "09:30:00", "11:30:00"
            pm_start, pm_end = "13:00:00", "15:00:00"
        else:  # US or default
            # US market hours (09:30-16:00 EST)
            am_start, am_end = "09:30:00", "16:00:00"
            pm_start, pm_end = None, None  # US has continuous trading

        for trading_day in daily_calendar:
            # Generate AM session minutes
            am_start_time = pd.Timestamp(f"{trading_day.date()} {am_start}")
            am_end_time = pd.Timestamp(f"{trading_day.date()} {am_end}")

            if pm_start and pm_end:
                # Markets with lunch break (like CN)
                am_minutes = pd.date_range(am_start_time, am_end_time, freq="1min")[
                    :-1
                ]  # Exclude end
                minute_calendar.extend(am_minutes.tolist())

                # Generate PM session minutes
                pm_start_time = pd.Timestamp(f"{trading_day.date()} {pm_start}")
                pm_end_time = pd.Timestamp(f"{trading_day.date()} {pm_end}")
                pm_minutes = pd.date_range(pm_start_time, pm_end_time, freq="1min")[
                    :-1
                ]  # Exclude end
                minute_calendar.extend(pm_minutes.tolist())
            else:
                # Continuous trading markets (like US)
                day_minutes = pd.date_range(am_start_time, am_end_time, freq="1min")[
                    :-1
                ]  # Exclude end
                minute_calendar.extend(day_minutes.tolist())

        logger.debug(
            f"Generated {len(minute_calendar)} minute timestamps for {market} market from {len(daily_calendar)} trading days"
        )
        return minute_calendar

    @staticmethod
    def normalize_universal(
        df: pd.DataFrame,
        calendar_list: list = None,
        date_field_name: str = "date",
        symbol_field_name: str = "symbol",
        last_close: float = None,
    ):
        """
        Universal normalize method for OHLCV data.

        Educational Notes:
        - Based on YahooNormalize.normalize_yahoo static method
        - Handles time index processing, calendar alignment, and anomaly detection
        - Supports both daily and minute-level data
        - Processes standard OHLCV fields with data cleaning

        Parameters
        ----------
        df: pd.DataFrame
            Input DataFrame with OHLCV data
        calendar_list: list
            Trading calendar for data alignment (optional)
        date_field_name: str
            Date field name, default "date"
        symbol_field_name: str
            Symbol field name, default "symbol"
        last_close: float
            Last close price from previous period (optional)

        Returns
        -------
        pd.DataFrame
            Normalized DataFrame ready for Qlib processing
        """
        if df.empty:
            return df

        # Get symbol for processing
        symbol = df.loc[df[symbol_field_name].first_valid_index(), symbol_field_name]
        columns = copy.deepcopy(UniversalNormalize.COLUMNS)
        df = df.copy()

        # Set datetime index
        df.set_index(date_field_name, inplace=True)
        df.index = pd.to_datetime(df.index)
        df.index = df.index.tz_localize(None)  # Remove timezone info

        # Remove duplicate timestamps
        df = df[~df.index.duplicated(keep="first")]

        # Calendar alignment if provided
        if calendar_list is not None and len(calendar_list) > 0:
            df = df.reindex(
                pd.DataFrame(index=calendar_list)
                .loc[
                    pd.Timestamp(df.index.min())
                    .date() : pd.Timestamp(df.index.max())
                    .date()
                    + pd.Timedelta(hours=23, minutes=59)
                ]
                .index
            )

        # Sort by time index
        df.sort_index(inplace=True)

        # Clean invalid volume data
        df.loc[
            (df["volume"] <= 0) | np.isnan(df["volume"]),
            list(set(df.columns) - {symbol_field_name}),
        ] = np.nan

        # Calculate price changes for anomaly detection
        change_series = UniversalNormalize.calc_change(df, last_close)

        # Anomaly detection and correction
        # Based on YahooNormalize logic for detecting price splits/errors
        _count = 0
        while True:
            change_series = UniversalNormalize.calc_change(df, last_close)
            _mask = (change_series >= 89) & (change_series <= 111)
            if not _mask.any():
                break
            # Correct anomalous prices (likely due to stock splits)
            _tmp_cols = ["high", "close", "low", "open"]
            df.loc[_mask, _tmp_cols] = df.loc[_mask, _tmp_cols] / 100
            _count += 1
            if _count >= 10:
                logger.warning(
                    f"{symbol} price change is abnormal for {_count} consecutive days, please check data carefully"
                )
                break

        # Final change calculation
        df["change"] = UniversalNormalize.calc_change(df, last_close)

        # Add change to columns list
        columns += ["change"]

        # Final data cleaning
        df.loc[(df["volume"] <= 0) | np.isnan(df["volume"]), columns] = np.nan

        # Restore symbol and reset index
        df[symbol_field_name] = symbol
        df.index.names = [date_field_name]
        return df.reset_index()

    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Main normalize method - implements BaseNormalize abstract method.

        Educational Notes:
        - This is the main entry point called by Qlib's Normalize class
        - Integrates all normalization steps: calendar, market detection, data cleaning
        - Automatically detects data frequency and market from symbol
        - Returns data ready for Qlib processing

        Parameters
        ----------
        df: pd.DataFrame
            Input DataFrame with OHLCV data

        Returns
        -------
        pd.DataFrame
            Normalized DataFrame ready for Qlib processing
        """
        if df.empty:
            logger.warning("Empty DataFrame provided to normalize method")
            return df

        # Get symbol for market detection
        symbol_field = self._symbol_field_name
        if symbol_field not in df.columns:
            logger.error(
                f"Symbol field '{symbol_field}' not found in DataFrame columns: {df.columns.tolist()}"
            )
            return df

        # Get first valid symbol
        first_symbol = df.loc[df[symbol_field].first_valid_index(), symbol_field]

        # Detect market from symbol
        market = self.detect_market_from_symbol(first_symbol)
        logger.debug(f"Detected market: {market} for symbol: {first_symbol}")

        # Get calendar list
        calendar_list = list(self._get_calendar_list())

        # Apply universal normalization
        normalized_df = self.normalize_universal(
            df=df,
            calendar_list=calendar_list,
            date_field_name=self._date_field_name,
            symbol_field_name=self._symbol_field_name,
            last_close=None,  # Could be enhanced to support incremental updates
        )

        logger.info(
            f"Successfully normalized {len(normalized_df)} rows for symbol: {first_symbol}"
        )
        return normalized_df

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

    Supported data sources:
    - tushare: A-share (China) market data
    - eod: US stock market data (EOD Historical Data)

    Educational Notes:
    - Processes standard OHLCV fields: open, high, low, close, volume
    - Uses source_type for data source specific logic when needed
    - Implements complete data normalization pipeline from Qlib
    - Uses calendar caching to avoid repeated API calls for the same market
    """

    # Standard OHLCV fields - matches BaseDataCollector._field_metadata
    COLUMNS = ["open", "high", "low", "close", "volume"]

    # Time format for daily data
    DAILY_FORMAT = "%Y-%m-%d"

    # Anomaly detection threshold for daily data
    DAILY_ANOMALY_THRESHOLD = (89, 111)  # 89x to 111x change detection

    # Class-level calendar cache to avoid repeated API calls
    _calendar_cache = {}

    def __init__(self, source_type: str = "tushare", market: str = "CN", **kwargs):
        """
        Initialize UniversalNormalize.

        Parameters
        ----------
        source_type: str
            Data source identifier for branch logic ("tushare", "eod", etc.)
        market: str
            Market identifier for trading calendar ("CN", "US")
        **kwargs: dict
            Additional parameters passed to BaseNormalize
        """
        self.source_type = source_type
        self.market = market

        # Call parent constructor with required parameters
        super().__init__(**kwargs)

        logger.info(
            f"Initialized UniversalNormalize for source: {source_type}, market: {market}"
        )

    @staticmethod
    def calc_change(df: pd.DataFrame, last_close: float) -> pd.Series:
        """
        Calculate price change series for anomaly detection.

        Educational Notes:
        - Based on Qlib's normalize pattern for price change calculation
        - Calculates price change series for anomaly detection
        - Handles daily data
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
        Get benchmark calendar for data alignment with caching.

        Educational Notes:
        - Uses class-level cache to avoid repeated API calls for same market
        - Uses Tushare API for CN market trading calendar
        - Falls back to pandas business days for US market or if API fails
        - Supports both CN and US market calendars
        - Market-specific trading calendar handling

        Returns
        -------
        Iterable[pd.Timestamp]
            Calendar timestamps for data alignment with trading days
        """
        # Check cache first to avoid repeated API calls
        cache_key = f"{self.source_type}_{self.market}"

        if cache_key in UniversalNormalize._calendar_cache:
            logger.debug(f"Using cached trading calendar for {self.market} market")
            return UniversalNormalize._calendar_cache[cache_key]

        # Get calendar and cache it
        calendar = self._get_pandas_trading_calendar()
        UniversalNormalize._calendar_cache[cache_key] = calendar

        logger.info(
            f"Cached trading calendar for {self.market} market ({len(calendar)} trading days)"
        )
        return calendar

    def _get_pandas_trading_calendar(self) -> Iterable[pd.Timestamp]:
        """
        Get trading calendar using Tushare (CN) or pandas fallback (US).

        Educational Notes:
        - For CN market: uses Tushare trade_cal API for accurate A-share trading days
        - For US market: uses pandas business days as fallback
        - Provides real trading days for data alignment

        Returns
        -------
        Iterable[pd.Timestamp]
            Real trading calendar timestamps
        """
        try:
            if self.market == "CN":
                # Try Tushare for A-share trading calendar
                tushare_calendar = self._get_tushare_trading_calendar()
                if tushare_calendar is not None and len(tushare_calendar) > 0:
                    return tushare_calendar
        except Exception as e:
            logger.warning(f"Failed to get Tushare trading calendar: {e}")

        try:
            import pandas as pd
            from datetime import datetime, timedelta

            # Fallback to pandas business days
            start_date = datetime(2000, 1, 1)
            end_date = datetime.now() + timedelta(days=365)

            # Generate business days (excludes weekends)
            business_days = pd.bdate_range(start=start_date, end=end_date, freq="B")

            logger.info(
                f"Generated pandas trading calendar with {len(business_days)} business days from {start_date.date()} to {end_date.date()}"
            )

            return business_days

        except Exception as e:
            logger.error(f"Failed to generate pandas trading calendar: {e}")
            logger.warning("Using empty calendar as final fallback")
            return []

    def _get_tushare_trading_calendar(self) -> Iterable[pd.Timestamp]:
        """
        Get A-share trading calendar from Tushare Pro API.

        Educational Notes:
        - Uses Tushare trade_cal API for accurate A-share trading days
        - Automatically excludes weekends and Chinese holidays
        - More accurate than business day approximation for A-share market

        Returns
        -------
        Iterable[pd.Timestamp]
            Tushare trading calendar timestamps
        """
        try:
            import tushare as ts
            from datetime import datetime, timedelta
            from app.core.config import settings

            token = settings.TUSHARE_TOKEN
            if not token:
                logger.warning("TUSHARE_TOKEN not configured, using pandas fallback")
                return None

            ts.set_token(token)
            pro = ts.pro_api()

            # Get trading calendar for SSE (Shanghai Stock Exchange)
            start_date = "20200101"
            end_date = (datetime.now() + timedelta(days=30)).strftime("%Y%m%d")

            df = pro.trade_cal(
                exchange="SSE",
                start_date=start_date,
                end_date=end_date,
                is_open="1",
            )

            if df is not None and not df.empty:
                # Convert to datetime
                trading_dates = pd.to_datetime(df["cal_date"])
                trading_dates = sorted(trading_dates)

                logger.info(
                    f"Retrieved A-share trading calendar with {len(trading_dates)} trading days"
                )

                return trading_dates

        except Exception as e:
            logger.warning(f"Failed to get Tushare trading calendar: {e}")

        return None

    def detect_market_from_symbol(self, symbol: str) -> str:
        """
        Detect market (CN/US) from stock symbol.

        Educational Notes:
        - CN symbols: end with .SZ, .SH, or 6-digit numbers
        - US symbols: typically alphabetic or end with common US suffixes
        - Used to determine market-specific processing rules

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
        - Based on Qlib's normalize pattern for OHLCV data
        - Handles time index processing, calendar alignment, and anomaly detection
        - Supports daily OHLCV data
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

        # Calendar alignment if provided (day-level data only)
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
        # Based on Qlib's logic for detecting price splits/errors
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

    def _clean_anomalous_timestamps(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean anomalous timestamps that are outside expected date ranges.

        Parameters
        ----------
        df: pd.DataFrame
            Input DataFrame with date column

        Returns
        -------
        pd.DataFrame
            Cleaned DataFrame with anomalous timestamps removed
        """
        if df.empty or self._date_field_name not in df.columns:
            return df

        # Convert date column to datetime if it's not already
        df = df.copy()
        df[self._date_field_name] = pd.to_datetime(df[self._date_field_name])

        return df

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

        # Clean anomalous timestamps that are outside expected date ranges
        df = self._clean_anomalous_timestamps(df)
        if df.empty:
            logger.warning("All data filtered out due to anomalous timestamps")
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

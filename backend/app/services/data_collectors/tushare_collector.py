"""
Tushare Data Collector for A-Share (China) Market.

This collector uses Tushare Pro API to fetch:
- Daily OHLCV data for A-shares
- Index constituent stocks (CSI300, CSI500, etc.)
- Trading calendar

Educational Notes:
- Tushare is the primary data source for China A-shares
- Requires API token from https://tushare.pro/
- Data format follows Tushare standard, needs normalization to Qlib format
- Supports various indices: CSI300, CSI500, CSI800, CSI1000, etc.
"""

import logging
import pandas as pd
import numpy as np
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path

from app.core.config import settings
from .base import BaseDataCollector
from .exceptions import DataSourceError, DataCollectionError, DataValidationError

logger = logging.getLogger(__name__)


# Market configuration for A-shares
MARKET_CONFIG = {
    "CN": {
        "timezone": "Asia/Shanghai",
        "exchange": "SSE",  # Shanghai Stock Exchange
        "supported_indices": ["CSI300", "CSI500", "CSI800", "CSI1000", "DIVIDEND"],
    }
}

# Index code mapping for Tushare
INDEX_CODE_MAP = {
    "CSI300": "000300.SH",
    "CSI500": "000905.SH",
    "CSI800": "000906.SH",
    "CSI1000": "000852.SH",
    "DIVIDEND": "000015.SH",
}

# Benchmark ETF mapping
BENCHMARK_CONFIG = {
    "CSI300": {"tushare_code": "510300.SH", "qlib_symbol": "SH510300"},
    "CSI500": {"tushare_code": "510500.SH", "qlib_symbol": "SH510500"},
    "CSI800": {"tushare_code": "510800.SH", "qlib_symbol": "SH510800"},
    "CSI1000": {"tushare_code": "512100.SH", "qlib_symbol": "SH512100"},
    "DIVIDEND": {"tushare_code": "510880.SH", "qlib_symbol": "SH510880"},
}


class TushareDataCollector(BaseDataCollector):
    """
    Tushare Data Collector for China A-Share Market.

    This collector fetches daily OHLCV data from Tushare Pro API.
    Supports CSI300, CSI500, CSI800, CSI1000, and other A-share indices.

    Educational Notes:
    - Inherits from BaseDataCollector for standard workflow integration
    - Uses Tushare Pro API for reliable A-share data
    - Automatically converts stock codes to Qlib format (e.g., 000001.SZ -> SZ000001)
    - Handles trading calendar and market holidays automatically
    """

    def __init__(
        self,
        save_dir: str = "./qlib_data/cn_data",
        start: str = "2020-01-01",
        end: str = None,
        interval: str = "1d",
        max_workers: int = 4,
        max_collector_count: int = 2,
        delay: float = 0.1,
        check_data_length: int = None,
        limit_nums: int = None,
        index_name: str = "CSI300",
    ):
        """
        Initialize Tushare data collector.

        Parameters
        ----------
        save_dir : str or Path
            Directory to save collected CSV files
        start : str
            Start date in YYYY-MM-DD format
        end : str, optional
            End date in YYYY-MM-DD format (defaults to today)
        interval : str, default "1d"
            Data interval (only "1d" supported for Tushare)
        max_workers : int, default 4
            Number of concurrent workers
        max_collector_count : int, default 2
            Maximum retry attempts for failed collections
        delay : float, default 0.1
            Delay between requests to avoid rate limiting
        check_data_length : int, optional
            Minimum required data length for validation
        limit_nums : int, optional
            Limit number of instruments for debugging
        index_name : str, default "CSI300"
            Index selection: "CSI300", "CSI500", "CSI800", "CSI1000", "DIVIDEND"
        """
        # Validate index parameter
        index = index_name.upper()
        if index not in MARKET_CONFIG["CN"]["supported_indices"]:
            raise ValueError(
                f"Unsupported index {index}. "
                f"Supported: {MARKET_CONFIG['CN']['supported_indices']}"
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
        self._timezone = MARKET_CONFIG["CN"]["timezone"]
        self._pro = None  # Lazy initialization of Tushare Pro API

        # Define field metadata for Qlib compatibility
        self._field_metadata = {
            "open": "float64",
            "high": "float64",
            "low": "float64",
            "close": "float64",
            "volume": "int64",
        }

        logger.info(f"TushareDataCollector initialized for {index} index")
        logger.info(f"Date range: {start} to {end}")

    def _get_pro_api(self):
        """
        Get Tushare Pro API instance with lazy initialization.

        Returns
        -------
        tushare.pro_api
            Tushare Pro API instance
        """
        if self._pro is None:
            import tushare as ts

            token = settings.TUSHARE_TOKEN
            if not token:
                raise DataSourceError(
                    source="tushare",
                    operation="initialize",
                    original_error=ValueError("TUSHARE_TOKEN not configured"),
                )

            ts.set_token(token)
            self._pro = ts.pro_api()
            logger.info("Tushare Pro API initialized successfully")

        return self._pro

    def get_instrument_list(self) -> List[str]:
        """
        Get list of constituent stocks for the specified index.
        Also automatically includes the index itself for benchmark comparison.

        Returns
        -------
        List[str]
            List of Tushare stock codes including index (e.g., ['000001.SZ', '600519.SH', '000300.SH'])

        Educational Notes:
        - Uses Tushare index_weight API to get current index constituents
        - Automatically adds the index code for benchmark data
        - Returns codes in Tushare format for data collection
        - Will be normalized to Qlib format later
        """
        try:
            pro = self._get_pro_api()
            index_code = INDEX_CODE_MAP.get(self.index)

            if not index_code:
                raise ValueError(f"Unknown index: {self.index}")

            logger.info(f"Fetching {self.index} constituent stocks from Tushare...")

            # Get index constituents using index_weight API
            # Use the most recent trading date
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")

            df = pro.index_weight(
                index_code=index_code,
                start_date=start_date,
                end_date=end_date,
            )

            if df is None or df.empty:
                # Fallback: try index_member API
                logger.warning(
                    f"index_weight returned empty, trying index_member for {index_code}"
                )
                df = pro.index_member(index_code=index_code)

            if df is None or df.empty:
                raise DataCollectionError(
                    f"Failed to get constituents for {self.index}"
                )

            # Extract unique stock codes
            if "con_code" in df.columns:
                symbols = df["con_code"].unique().tolist()
            elif "ts_code" in df.columns:
                symbols = df["ts_code"].unique().tolist()
            else:
                raise DataValidationError(
                    f"Unexpected column format: {df.columns.tolist()}"
                )

            # Add the index itself for benchmark comparison
            symbols.append(index_code)

            logger.info(
                f"Retrieved {len(symbols)-1} constituent stocks for {self.index}"
            )
            logger.info(f"Added index {index_code} for benchmark data")
            logger.info(f"Sample stocks: {symbols[:5]}")

            return symbols

        except Exception as e:
            logger.error(f"Error fetching {self.index} constituents: {e}")
            raise DataSourceError(
                source=f"tushare/{self.index}",
                operation="get_instrument_list",
                original_error=e,
            )

    def normalize_symbol(self, symbol: str) -> str:
        """
        Normalize Tushare symbol to Qlib format.

        Parameters
        ----------
        symbol : str
            Tushare format symbol (e.g., '000001.SZ', '600519.SH')

        Returns
        -------
        str
            Qlib format symbol (e.g., 'SZ000001', 'SH600519')

        Educational Notes:
        - Tushare format: {code}.{exchange} (e.g., 000001.SZ)
        - Qlib format: {exchange}{code} (e.g., SZ000001)
        - This conversion is critical for Qlib data compatibility
        """
        if "." in symbol:
            code, exchange = symbol.split(".")
            return f"{exchange}{code}"
        return symbol

    def get_data(
        self,
        symbol: str,
        interval: str = "1d",
        start_datetime: str = None,
        end_datetime: str = None,
    ) -> pd.DataFrame:
        """
        Fetch daily OHLCV data for a single stock or index.

        Parameters
        ----------
        symbol : str
            Tushare format symbol (e.g., '000001.SZ' for stock, '000300.SH' for index)
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
        - Uses Tushare daily API for stock data
        - Uses Tushare index_daily API for index data
        - Automatically handles forward adjustment for stocks (qfq)
        - Returns data in standard OHLCV format for Qlib
        """
        try:
            pro = self._get_pro_api()

            # Convert date format
            start_date = (
                start_datetime.replace("-", "")
                if start_datetime
                else self.start.replace("-", "")
            )
            end_date = (
                end_datetime.replace("-", "")
                if end_datetime
                else self.end.replace("-", "")
            )

            logger.debug(f"Fetching data for {symbol}: {start_date} to {end_date}")

            # Check if this is an index (based on known index codes)
            is_index = symbol in INDEX_CODE_MAP.values()

            if is_index:
                # Fetch index data using index_daily API
                logger.debug(f"Fetching index data for {symbol}")
                df = pro.index_daily(
                    ts_code=symbol,
                    start_date=start_date,
                    end_date=end_date,
                )

                if df is None or df.empty:
                    logger.warning(f"No index data returned for {symbol}")
                    return pd.DataFrame()

                # Index data doesn't need adjustment factors
                # Rename columns to standard format
                df = df.rename(
                    columns={
                        "trade_date": "date",
                        "vol": "volume",
                    }
                )

            else:
                # Fetch stock data using daily API
                logger.debug(f"Fetching stock data for {symbol}")
                df = pro.daily(
                    ts_code=symbol,
                    start_date=start_date,
                    end_date=end_date,
                )

                if df is None or df.empty:
                    logger.warning(f"No stock data returned for {symbol}")
                    return pd.DataFrame()

                # Get adjustment factors for forward adjustment (stocks only)
                adj_df = pro.adj_factor(
                    ts_code=symbol,
                    start_date=start_date,
                    end_date=end_date,
                )

                if adj_df is not None and not adj_df.empty:
                    # Merge adjustment factors
                    df = df.merge(
                        adj_df[["trade_date", "adj_factor"]],
                        on="trade_date",
                        how="left",
                    )

                    # Apply forward adjustment to OHLC prices
                    if "adj_factor" in df.columns:
                        latest_factor = df["adj_factor"].iloc[0]  # Most recent factor
                        df["adj_ratio"] = df["adj_factor"] / latest_factor

                        for col in ["open", "high", "low", "close"]:
                            df[col] = df[col] * df["adj_ratio"]

                # Rename columns to standard format
                df = df.rename(
                    columns={
                        "trade_date": "date",
                        "vol": "volume",
                    }
                )

            # Select and order columns
            columns = ["date", "open", "high", "low", "close", "volume"]
            df = df[[col for col in columns if col in df.columns]]

            # Convert date to datetime and set as index
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date")
            df = df.sort_index()

            # Convert volume to int64
            if "volume" in df.columns:
                if is_index:
                    # Index volume is already in correct units
                    df["volume"] = df["volume"].astype(np.int64)
                else:
                    # Stock volume is in lots (手), convert to shares
                    df["volume"] = (df["volume"] * 100).astype(np.int64)

            data_type = "index" if is_index else "stock"
            logger.debug(f"Retrieved {len(df)} records for {symbol} ({data_type})")
            return df

        except Exception as e:
            logger.warning(f"Error fetching data for {symbol}: {e}")
            return pd.DataFrame()

    @staticmethod
    def get_trading_calendar(start_date: str = None, end_date: str = None) -> List[str]:
        """
        Get A-share trading calendar from Tushare.

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
        - Uses Tushare trade_cal API
        - Filters for open trading days only
        - Essential for data alignment and validation
        """
        import tushare as ts

        token = settings.TUSHARE_TOKEN
        if not token:
            logger.warning("TUSHARE_TOKEN not configured, returning empty calendar")
            return []

        ts.set_token(token)
        pro = ts.pro_api()

        if start_date is None:
            start_date = "20200101"
        else:
            start_date = start_date.replace("-", "")

        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")
        else:
            end_date = end_date.replace("-", "")

        try:
            df = pro.trade_cal(
                exchange="SSE",
                start_date=start_date,
                end_date=end_date,
                is_open="1",
            )

            if df is None or df.empty:
                return []

            # Convert to YYYY-MM-DD format
            dates = df["cal_date"].tolist()
            formatted_dates = [f"{d[:4]}-{d[4:6]}-{d[6:8]}" for d in dates]

            return sorted(formatted_dates)

        except Exception as e:
            logger.error(f"Error fetching trading calendar: {e}")
            return []

    @staticmethod
    def get_index_components(index_code: str) -> List[str]:
        """
        Get index constituent stocks from Tushare.

        Parameters
        ----------
        index_code : str
            Tushare index code (e.g., '000300.SH')

        Returns
        -------
        List[str]
            List of stock codes in Qlib format (e.g., ['SH600519', 'SZ000858'])

        Educational Notes:
        - Static method for use by index_components_service
        - Returns codes in Qlib format for consistency
        """
        import tushare as ts

        token = settings.TUSHARE_TOKEN
        if not token:
            raise DataSourceError(
                source="tushare",
                operation="get_index_components",
                original_error=ValueError("TUSHARE_TOKEN not configured"),
            )

        ts.set_token(token)
        pro = ts.pro_api()

        try:
            # Get index constituents
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")

            df = pro.index_weight(
                index_code=index_code,
                start_date=start_date,
                end_date=end_date,
            )

            if df is None or df.empty:
                # Fallback to index_member
                df = pro.index_member(index_code=index_code)

            if df is None or df.empty:
                raise DataCollectionError(
                    f"Failed to get constituents for {index_code}"
                )

            # Extract stock codes
            if "con_code" in df.columns:
                tushare_codes = df["con_code"].unique().tolist()
            elif "ts_code" in df.columns:
                tushare_codes = df["ts_code"].unique().tolist()
            else:
                raise DataValidationError(
                    f"Unexpected column format: {df.columns.tolist()}"
                )

            # Convert to Qlib format
            qlib_codes = []
            for code in tushare_codes:
                if "." in code:
                    stock_code, exchange = code.split(".")
                    qlib_codes.append(f"{exchange}{stock_code}")
                else:
                    qlib_codes.append(code)

            logger.info(f"Retrieved {len(qlib_codes)} components for {index_code}")
            return qlib_codes

        except Exception as e:
            logger.error(f"Error fetching index components: {e}")
            raise

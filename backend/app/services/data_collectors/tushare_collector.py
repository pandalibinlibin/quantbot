"""
Tushare Data Collector for A-Share (China) Market.

This collector uses Tushare Pro API to fetch:
- Daily OHLCV data for ETFs (via fund_daily API)
- Daily OHLCV data for A-shares (via daily API)
- Index data (via index_daily API)

Educational Notes:
- Tushare is the primary data source for China A-shares and ETFs
- Requires API token from https://tushare.pro/
- Data format follows Tushare standard, needs normalization to Qlib format
- Only supports ETF_UNIVERSE (reads from index_config.yaml)
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
        "supported_indices": [
            "ETF_UNIVERSE",
        ],
    }
}


def _is_etf_code(symbol: str) -> bool:
    """
    Detect if a Tushare symbol is an ETF based on code pattern.

    Shanghai ETFs: codes starting with '5' (51xxxx, 56xxxx, 58xxxx)
    Shenzhen ETFs: codes starting with '159'
    """
    if "." not in symbol:
        return False
    code, exchange = symbol.split(".")
    if exchange == "SH":
        return code.startswith("5")
    elif exchange == "SZ":
        return code.startswith("159")
    return False


class TushareDataCollector(BaseDataCollector):
    """
    Tushare Data Collector for China A-Share Market.

    This collector fetches daily OHLCV data from Tushare Pro API.
    Collects ETF universe daily data via fund_daily API.

    Educational Notes:
    - Inherits from BaseDataCollector for standard workflow integration
    - Uses Tushare Pro API for reliable A-share and ETF data
    - Automatically converts stock codes to Qlib format (e.g., 510300.SH -> SH510300)
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
        index_name: str = "ETF_UNIVERSE",
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
        index_name : str, default "ETF_UNIVERSE"
            Index selection: only "ETF_UNIVERSE" is supported
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
        # VWAP (Volume Weighted Average Price) is required by Alpha158 factor library
        self._field_metadata = {
            "open": "float64",
            "high": "float64",
            "low": "float64",
            "close": "float64",
            "volume": "int64",
            "vwap": "float64",
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
        Get list of instruments for ETF Universe.

        Reads the static ETF list from index_config.yaml.

        Returns
        -------
        List[str]
            List of Tushare ETF codes (e.g., ['510300.SH', '159919.SZ'])
        """
        if self.index != "ETF_UNIVERSE":
            raise ValueError(
                f"Unsupported index: {self.index}. Only ETF_UNIVERSE is supported."
            )
        return self._get_etf_universe_instruments()

    def _get_etf_universe_instruments(self) -> List[str]:
        """
        Get ETF instrument list from index_config.yaml (static_list source).

        Reads the etf_universe entry and converts Qlib-format codes (SH510300)
        to Tushare format (510300.SH) for data collection.

        Also adds the benchmark index (000300.SH) for reference.

        Returns
        -------
        List[str]
            List of Tushare-format ETF codes
        """
        try:
            from app.services.index_components_service import (
                get_index_components_service,
            )

            service = get_index_components_service()
            # Returns Qlib-format codes like ['SH510300', 'SZ159919', ...]
            qlib_codes = service.get_components("etf_universe")

            # Convert Qlib format → Tushare format: SH510300 → 510300.SH
            tushare_codes = []
            for code in qlib_codes:
                if len(code) > 2 and code[:2] in ("SH", "SZ"):
                    stock_num = code[2:]
                    exchange = code[:2]
                    tushare_codes.append(f"{stock_num}.{exchange}")
                else:
                    logger.warning(f"Unexpected ETF code format: {code}, skipping")

            # Add benchmark index for reference
            tushare_codes.append("000300.SH")

            logger.info(
                f"ETF Universe: {len(tushare_codes) - 1} ETFs + 1 benchmark index"
            )
            logger.info(f"Sample ETFs: {tushare_codes[:5]}")

            return tushare_codes

        except Exception as e:
            logger.error(f"Error loading ETF universe from index_config.yaml: {e}")
            raise DataSourceError(
                source="tushare/ETF_UNIVERSE",
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

            # Check if this is an index (000xxx.SH pattern, e.g., 000300.SH)
            code_part = symbol.split(".")[0] if "." in symbol else ""
            is_index = code_part.startswith("000") and symbol.endswith(".SH")
            # Check if this is an ETF (pattern-based detection)
            is_etf = _is_etf_code(symbol)

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

                # Calculate VWAP for index
                # Index data has 'amount' (turnover in CNY) and 'vol' (volume)
                # VWAP = amount / volume (both already in compatible units for index)
                if "amount" in df.columns and "volume" in df.columns:
                    df["vwap"] = df["amount"] / (df["volume"] + 1e-12)
                else:
                    # Fallback: use average of OHLC
                    df["vwap"] = (df["open"] + df["high"] + df["low"] + df["close"]) / 4

            elif is_etf:
                # Fetch ETF data using fund_daily API
                logger.debug(f"Fetching ETF data for {symbol}")
                df = pro.fund_daily(
                    ts_code=symbol,
                    start_date=start_date,
                    end_date=end_date,
                )

                if df is None or df.empty:
                    logger.warning(f"No ETF data returned for {symbol}")
                    return pd.DataFrame()

                # ETF data - rename columns to standard format
                df = df.rename(
                    columns={
                        "trade_date": "date",
                        "vol": "volume",
                    }
                )

                # Calculate VWAP for ETF
                # ETF data has 'amount' (turnover in CNY) and 'vol' (volume)
                if "amount" in df.columns and "volume" in df.columns:
                    df["vwap"] = df["amount"] / (df["volume"] + 1e-12)
                else:
                    # Fallback: use average of OHLC
                    df["vwap"] = (df["open"] + df["high"] + df["low"] + df["close"]) / 4

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

                # Calculate VWAP for stocks
                # Tushare daily API returns:
                # - amount: turnover in thousand CNY (千元)
                # - vol: volume in lots (手, 1 lot = 100 shares)
                # VWAP = (amount * 1000) / (vol * 100) = amount * 10 / vol
                if "amount" in df.columns and "volume" in df.columns:
                    # After rename, 'vol' becomes 'volume'
                    # But 'amount' is still 'amount'
                    df["vwap"] = (df["amount"] * 10) / (df["volume"] + 1e-12)
                    # Apply forward adjustment to VWAP if adjustment was applied
                    if "adj_ratio" in df.columns:
                        df["vwap"] = df["vwap"] * df["adj_ratio"]
                else:
                    # Fallback: use average of OHLC
                    df["vwap"] = (df["open"] + df["high"] + df["low"] + df["close"]) / 4

            # Select and order columns (including VWAP for Alpha158)
            columns = ["date", "open", "high", "low", "close", "volume", "vwap"]
            df = df[[col for col in columns if col in df.columns]]

            # Convert date to datetime and set as index
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date")
            df = df.sort_index()

            # Convert volume to int64
            if "volume" in df.columns:
                if is_index or is_etf:
                    # Index and ETF volume is already in correct units
                    df["volume"] = df["volume"].astype(np.int64)
                else:
                    # Stock volume is in lots (手), convert to shares
                    df["volume"] = (df["volume"] * 100).astype(np.int64)

            data_type = "index" if is_index else ("etf" if is_etf else "stock")
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

    def collector_data(self, **kwargs) -> None:
        """
        Main data collection workflow for batch downloading.

        This method implements the standard Qlib BaseCollector interface
        for batch data collection. It downloads OHLCV data for all instruments
        including stocks, indices, and ETFs.

        Educational Notes:
        - Called by data collection pipeline to execute batch downloads
        - Saves data as CSV files in save_dir for Qlib processing
        - Qlib will automatically convert CSV to binary format
        - Includes error handling and progress tracking
        """
        import os
        from pathlib import Path

        logger.info(f"Starting TushareDataCollector batch data collection...")
        logger.info(f"Target directory: {self.save_dir}")
        logger.info(f"Date range: {self.start} to {self.end}")

        # Ensure save directory exists
        Path(self.save_dir).mkdir(parents=True, exist_ok=True)

        # Get instrument list (stocks + index + ETF)
        try:
            instruments = self.get_instrument_list()
            logger.info(f"Retrieved {len(instruments)} instruments for collection")

            # Log instrument breakdown
            etf_count = sum(1 for code in instruments if _is_etf_code(code))
            index_count = sum(
                1
                for code in instruments
                if "." in code
                and code.split(".")[0].startswith("000")
                and code.endswith(".SH")
            )
            logger.info(f"Breakdown: {etf_count} ETFs, {index_count} benchmark indices")

        except Exception as e:
            logger.error(f"Failed to get instrument list: {e}")
            raise

        # Download data for each instrument
        successful_downloads = 0
        failed_downloads = 0

        for i, instrument in enumerate(instruments, 1):
            try:
                logger.info(f"[{i}/{len(instruments)}] Downloading {instrument}...")

                # Get data for this instrument
                df = self.get_data(
                    symbol=instrument,
                    interval="1d",
                    start_datetime=self.start,
                    end_datetime=self.end,
                )

                if df.empty:
                    logger.warning(f"No data returned for {instrument}")
                    failed_downloads += 1
                    continue

                # Convert to Qlib symbol format for filename
                qlib_symbol = self.normalize_symbol(instrument)
                csv_filename = f"{qlib_symbol}.csv"
                csv_path = os.path.join(self.save_dir, csv_filename)

                # Save to CSV
                df.to_csv(csv_path)
                logger.debug(f"Saved {len(df)} records to {csv_filename}")
                successful_downloads += 1

                # Add small delay to avoid API rate limits
                import time

                time.sleep(self.delay)

            except Exception as e:
                logger.error(f"Failed to download {instrument}: {e}")
                failed_downloads += 1
                continue

        # Summary
        logger.info(f"Data collection completed:")
        logger.info(f"  Successful: {successful_downloads}")
        logger.info(f"  Failed: {failed_downloads}")
        logger.info(f"  Total: {len(instruments)}")

        if successful_downloads == 0:
            raise DataCollectionError("No data was successfully downloaded")

        logger.info(f"CSV files saved to: {self.save_dir}")
        logger.info("Qlib will automatically convert CSV files to binary format")

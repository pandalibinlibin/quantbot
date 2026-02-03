#!/usr/bin/env python3
"""
Yahoo Finance Real-time Data Collector for Qlib
This script collects real-time stock data using yfinance SDK and outputs
CSV format compatible with Qlib's dump_bin.py converter.
Compatible with get_data.py interface while adding extended functionality.

Usage:
    # Basic usage (compatible with get_data.py)
    python get_data_yahoo_realtime.py download_data --target_dir /app/csv_data/cn_data
    # Same to python get_data_yahoo_realtime.py download_data --stock_pool csi300 --period 1y --target_dir /app/csv_data/cn_data

    # Extended usage (new functionality)
    python get_data_yahoo_realtime.py download_data --stock_pool csi300 --period 1y --target_dir /app/csv_data/cn_data
    python get_data_yahoo_realtime.py download_data --stock_pool csi500 --start_date 2023-01-01 --target_dir /app/csv_data/cn_data
    python get_data_yahoo_realtime.py download_data --stock_pool csi300 --incremental --target_dir /app/csv_data/cn_data
    python get_data_yahoo_realtime.py download_data --stock_pool csi300 --start_date 2023-01-01 --end_date 2023-12-31 --target_dir /app/csv_data/cn_data

    # Configuration-driven field collection (fields defined in config file)
    # Fields are automatically loaded from backend/app/core/data_fields.yaml

"""
import argparse
from functools import total_ordering
import logging
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Union
import pandas as pd
import yfinance as yf

# Import configuration utilities
import sys

sys.path.append("/app")
from app.core.data_config import get_required_fields

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class StockPool:
    """
    Stock pool for CSI300/cSI500 constituents.
    Gets constituent stocks dynamically from third-party API for Qlib factor calculation.
    """

    def __init__(self, pool_name: str):
        self.pool_name = pool_name.lower()
        self.api_urls = {
            "csi300": "https://yfiua.github.io/index-constituents/constituents-csi300.json",
            "csi500": "https://yfiua.github.io/index-constituents/constituents-csi500.json",
        }

    def get_name(self) -> str:
        """Get human-readable name of the stock pool."""
        return "CSI300" if self.pool_name == "csi300" else "CSI500"

    def get_symbols(self) -> List[str]:
        """
        Get constituent stock symbols for Qlib factor calculation.

        Returns:
            List of stock symbols in Yahoo Finance format (e.g., '000001.SZ')

        Raises:
            ValueError: If pool_name is not supported
            Exception: If API request fails
        """
        if self.pool_name not in self.api_urls:
            raise ValueError(
                f"Unsupported pool: {self.pool_name}. Supported pools: {list(self.api_urls.keys())}"
            )

        url = self.api_urls[self.pool_name]
        logger.info(f"Fetching {self.pool_name.upper()} constituents from API")

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            symbols = [item["Symbol"] for item in data if "Symbol" in item]

            if not symbols:
                raise Exception(
                    f"No symbols found in API response for {self.pool_name}"
                )

            logger.info(
                f"Successfully retrieved {len(symbols)} stocks for {self.get_name()}"
            )

            return symbols
        except requests.RequestException as e:
            raise Exception(
                f"Failed to fetch {self.pool_name} constituents from API: {e}"
            )
        except (KeyError, ValueError) as e:
            raise Exception(f"Invalid API response format for {self.pool_name}: {e}")


class YahooDataCollector:
    """
    Yahoo Finance data collector with get_data.py compatible interface.
    Supports incremental updates and extensible field configuration.
    """

    def __init__(self):
        # Load complete configuration for yahoo_finance
        from app.core.data_config import load_data_fields_config

        full_config = load_data_fields_config()
        self.config = full_config["data_sources"]["yahoo_finance"]

        # Load required fields from configuration
        self.required_fields = self.config.get("fields", [])
        logger.info(
            f"Loaded required fields from configuration: {self.required_fields}"
        )

    def download_data(
        self,
        target_dir: str = "./csv_data",
        stock_pool: str = "csi300",
        period: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        incremental: bool = False,
    ):
        """
        Download stock data with get_data.py compatible interface.

        Args:
            target_dir: Target directory for CSV files
            stock_pool: Stock pool name (csi300, csi500)
            period: Time period (1y, 6m, 3m, etc.)
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            incremental: Whether to perform incremental update

        Returns:
            bool: True if successful, False otherwise
        """
        logger.info(f"Starting Yahoo Finance data collection")
        logger.info(f"Stock pool: {stock_pool}")
        logger.info(f"Target directory: {target_dir}")

        try:
            # Create target directory
            target_path = Path(target_dir)
            target_path.mkdir(parents=True, exist_ok=True)

            # Get stock symbol
            pool = StockPool(stock_pool)
            symbols = pool.get_symbols()

            # Use configured fields
            field_list = self.required_fields
            logger.info(f"Using configured fields: {field_list}")

            # Determine date range
            start_dt, end_dt = self._parse_date_range(period, start_date, end_date)

            # Download data for each symbol
            success_count = 0
            total_count = len(symbols)

            for i, symbol in enumerate(symbols, 1):
                try:
                    logger.info(f"Processing {symbol} ({i} / {total_count})")

                    # Check for incremental update
                    actual_start_dt = start_dt
                    if incremental:
                        actual_start_dt = self._get_incremental_start_date(
                            target_path / f"{symbol}.csv", start_dt
                        )

                    # Downlaod data
                    data = self._download_symbol_data(
                        symbol, actual_start_dt, end_dt, field_list
                    )

                    if data is not None and not data.empty:
                        # Save to CSV
                        csv_file = target_path / f"{symbol}.csv"
                        self._save_csv_data(data, csv_file, incremental)
                        success_count += 1
                    else:
                        logger.warning(f"No data retrieved for {symbol}")
                except Exception as e:
                    logger.error(f"Failed to process {symbol}: {e}")
                    continue

            logger.info(
                f"Data collection completed: {success_count} / {total_count} symbols successful"
            )
            return success_count > 0
        except Exception as e:
            logger.error(f"Data collection failed: {e}")
            return False

    def _parse_date_range(
        self, period: Optional[str], start_date: Optional[str], end_date: Optional[str]
    ):
        """Parse date range from parameters."""

        end_dt = datetime.now()

        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")

        if start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        elif period:
            # Parse period (1y, 6m, 3m, etc.)
            if period.endswith("y"):
                years = int(period[:-1])
                start_dt = end_dt - timedelta(days=365 * years)
            elif period.endswith("m"):
                months = int(period[:-1])
                start_dt = end_dt - timedelta(days=30 * months)
            elif period.endswith("d"):
                days = int(period[:-1])
                start_dt = end_dt - timedelta(days=days)
            else:
                raise ValueError(
                    f"Invalid period format: {period}. Use format like '1y', '6m', '30d'"
                )
        else:
            # Default to 1 year
            start_dt = end_dt - timedelta(days=365)

        return start_dt, end_dt

    def _get_incremental_start_date(
        self, csv_file: Path, default_start: datetime
    ) -> datetime:
        """Get start date for incremental update."""
        if not csv_file.exists():
            return default_start

        try:
            df = pd.read_csv(csv_file)
            if not df.empty and "date" in df.columns:
                last_date = pd.to_datetime(df["date"]).max()
                # Start from the day after the last day
                return last_date + timedelta(days=1)
        except Exception as e:
            logger.warning(f"Failed to read existing CSV {csv_file}: {e}")

        return default_start

    def _download_symbol_data(
        self, symbol: str, start_dt: datetime, end_dt: datetime, fields: List[str]
    ) -> Optional[pd.DataFrame]:
        """Download data for a single symbol."""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(
                start=start_dt.strftime("%Y-%m-%d"), end=end_dt.strftime("%Y-%m-%d")
            )

            if hist.empty:
                return None

            # Reset index to get date as column
            hist = hist.reset_index()

            # Use configuration-driven field mapping
            yahoo_to_qlib_mapping = {
                "Date": "date",
                "Open": self.config.get("qlib_mapping", {}).get("open", "open"),
                "High": self.config.get("qlib_mapping", {}).get("high", "high"),
                "Low": self.config.get("qlib_mapping", {}).get("low", "low"),
                "Close": self.config.get("qlib_mapping", {}).get("close", "close"),
                "Volume": self.config.get("qlib_mapping", {}).get("volume", "volume"),
            }

            hist = hist.rename(columns=yahoo_to_qlib_mapping)

            # Calculate VWAP (Volume Weighted Average Price)
            if (
                "volume" in hist.columns
                and "high" in hist.columns
                and "low" in hist.columns
                and "close" in hist.columns
            ):
                # VWAP = (High + Low + Close) / 3 for daily data
                # This is a simplified VWAP calculation suitable for daily OHLCV data
                hist["vwap"] = (hist["high"] + hist["low"] + hist["close"]) / 3
            else:
                # Fallback: use close price if other fields are missing
                hist["vwap"] = hist.get("close", 0)

            # Select only requested fields
            # Debug: Print available columns and requested fields

            available_fields = ["date"] + [f for f in fields if f in hist.columns]

            hist = hist[available_fields]

            # Format date
            hist["date"] = pd.to_datetime(hist["date"]).dt.strftime("%Y-%m-%d")

            return hist
        except Exception as e:
            logger.error(f"Failed to download data for {symbol}: {e}")
            return None

    def _save_csv_data(self, data: pd.DataFrame, csv_file: Path, incremental: bool):
        """Save data to CSV file."""
        if incremental and csv_file.exists():
            # Append to existing file
            data.to_csv(csv_file, mode="a", header=False, index=False)
        else:
            # Create new file
            data.to_csv(csv_file, index=False)


def main():
    """Main function with get_data.py compatible command line interface."""
    parser = argparse.ArgumentParser(
        description="Yahoo Finance Data Collector for Qlib"
    )

    # Add subcommands to match get_data.py interface
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # download_data subcommand (compatible with get_data.py)
    download_parser = subparsers.add_parser("download_data", help="Download stock data")

    # Compatible parameters (must support)
    download_parser.add_argument(
        "--file_name", type=str, help="Output file name (for compatibility)"
    )
    download_parser.add_argument(
        "--target_dir", type=str, required=True, help="Target directory for CSV file"
    )

    # Extended parameters (new functionality)
    download_parser.add_argument(
        "--stock_pool",
        type=str,
        default="csi300",
        choices=["csi300", "csi500"],
        help="Stock pool selection",
    )
    download_parser.add_argument("--period", type=str, help="Time period (1y, 6m, 3m)")
    download_parser.add_argument(
        "--start_date", type=str, help="Start date (YYYY-MM-DD)"
    )
    download_parser.add_argument("--end_date", type=str, help="End date (YYYY-MM-DD)")
    download_parser.add_argument(
        "--incremental", action="store_true", help="Incremental update mode"
    )

    args = parser.parse_args()

    if args.command == "download_data":
        collector = YahooDataCollector()
        success = collector.download_data(
            target_dir=args.target_dir,
            stock_pool=args.stock_pool,
            period=args.period,
            start_date=args.start_date,
            end_date=args.end_date,
            incremental=args.incremental,
        )

        if success:
            logger.info("Data collection completed successfully")
        else:
            logger.error("Data collection failed")
            exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
